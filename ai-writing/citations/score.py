"""Question 2 scoring: the v1 abstract detector (ai-writing/detector.py, ModernBERT-large on 'title | abstract') applied
to cited works.

prep   (CPU) -> /n/fs/resemble/cs-atlas-cache/citations/score_input.sqlite  texts(id, kind, text)
         cited   every cited OpenAlex work published 2022 or later with a title and an abstract of >= 50 words (the
                 threshold v1 used for lab papers)
         calib   cited works published 2016-2021 with the same filter: every preprint-only one up to CALIB_PRE, and a
                 uniform sample of CALIB_PUB published / other ones (the pre-ChatGPT false-positive floor)
         labchk  LABCHK lab papers already scored by v1 (scores.jsonl.gz): checks that this pipeline reproduces v1's flags
       Text = detector.text(title, abstract) with the abstract rebuilt from OpenAlex's inverted index, exactly as
       build_corpus.py builds the lab papers' abstracts.
score  (GPU, one Slurm array task per shard) -> score_out_<shard>.sqlite  scores(id, p) with p unrounded; uses
       detector.predict (bf16 autocast, the pipeline the v1 threshold was set with) on rows with rowid % nshards == shard.
Phases: prep TAG writes score_input_TAG.sqlite holding only texts that no earlier score_input_*.sqlite holds, so a first
phase can be queued while the OpenAlex fetch is still running and a second phase picks up the rest (calib and labchk
go only into a phase run with --calib, which must come after the fetch has finished, since the fetch runs most-cited
first and an early calibration sample would be the popular works only; labchk goes into the first phase).
usage: score.py prep TAG [--calib] | score TAG SHARD NSHARDS
"""
import gzip, json, random, sqlite3, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
AIW = HERE.parent
CACHE = Path('/n/fs/resemble/cs-atlas-cache/citations')
CALIB_PRE, CALIB_PUB, LABCHK = 15000, 15000, 3000
SEED = 20261022
sys.path.insert(0, str(AIW))


def inv_text(inv):
    if not inv:
        return None
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return ' '.join(w for _, w in pos)


def prep(tag, calib):
    INP = CACHE / f'score_input_{tag}.sqlite'
    done = set()
    for f in sorted(CACHE.glob('score_input_*.sqlite')):
        if f != INP:
            done |= {i for i, in sqlite3.connect(f).execute('select id from texts')}
    first = not done
    from build import pubclass
    import detector as V1
    c = sqlite3.connect(f'file:{CACHE / "openalex.sqlite"}?mode=ro', uri=True, timeout=600)
    cited, pre, pub = [], [], []
    for wid, b in c.execute('select wid, data from works where status > 0'):
        w = json.loads(zlib.decompress(b))
        y, t, ab = w.get('publication_year'), w.get('display_name'), inv_text(w.get('abstract_inverted_index'))
        if not y or not t or not ab or len(ab.split()) < 50:
            continue
        row = (wid, V1.text(t, ab))
        if wid in done:
            continue
        if y >= 2022:
            cited.append(row)
        elif 2016 <= y <= 2021:
            (pre if pubclass(w) == 'preprint' else pub).append(row)
    r = random.Random(SEED)
    r.shuffle(pre); r.shuffle(pub)
    lab = [json.loads(l) for l in gzip.open(AIW / 'scores.jsonl.gz', 'rt')]
    keys = set(x['key'] for x in r.sample(lab, LABCHK))
    labrows = []
    for line in gzip.open(AIW / 'papers.jsonl.gz', 'rt'):
        p = json.loads(line)
        if p['key'] in keys and p.get('abstract') and p.get('title'):
            labrows.append((p['key'], V1.text(p['title'], p['abstract'])))
    if INP.exists():
        INP.unlink()
    o = sqlite3.connect(INP)
    o.execute('create table texts (id text primary key, kind text, text text)')
    o.executemany('insert into texts values (?,?,?)', [(i, 'cited', t) for i, t in cited])
    if calib:
        o.executemany('insert or ignore into texts values (?,?,?)', [(i, 'calib', t) for i, t in pre[:CALIB_PRE] + pub[:CALIB_PUB]])
    if first:
        o.executemany('insert or ignore into texts values (?,?,?)', [(i, 'labchk', t) for i, t in labrows])
    o.commit()
    print(json.dumps(dict(tag=tag, first=first, cited=len(cited), calib_pre=min(len(pre), CALIB_PRE), calib_pub=min(len(pub), CALIB_PUB), labchk=len(labrows),
                          pool_pre=len(pre), pool_pub=len(pub))))


def score(tag, shard, nshards):
    INP = CACHE / f'score_input_{tag}.sqlite'
    import shutil, os, time
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import detector as V1
    local = Path(os.environ.get('TMPDIR', '/tmp')) / f'cit_score_{os.getpid()}.sqlite'
    shutil.copy(INP, local)  # one sequential read of the share, then node-local
    c = sqlite3.connect(local)
    rows = c.execute('select id, text from texts where rowid % ? = ? order by length(text)', (nshards, shard)).fetchall()
    c.close(); local.unlink()
    mdir = AIW / 'detector' / 'all'
    tok = AutoTokenizer.from_pretrained(mdir / 'model')
    model = AutoModelForSequenceClassification.from_pretrained(mdir / 'model').cuda().eval()
    t0 = time.time(); out = []
    B = 4096
    for i in range(0, len(rows), B):
        chunk = rows[i:i + B]
        p = V1.predict(model, tok, [t for _, t in chunk])
        out += [(k, float(v)) for (k, _), v in zip(chunk, p)]
        print(json.dumps(dict(shard=shard, done=len(out), of=len(rows), sec=round(time.time() - t0))), flush=True)
    dst = CACHE / f'score_out_{tag}_{shard}.sqlite'
    tmp = local.with_name(f'cit_out_{os.getpid()}.sqlite')  # written node-local, then copied in one piece
    o = sqlite3.connect(tmp)
    o.execute('create table scores (id text primary key, p real)')
    o.executemany('insert or replace into scores values (?,?)', out); o.commit(); o.close()
    shutil.copy(tmp, dst.with_name(dst.name + '.part')); os.replace(dst.with_name(dst.name + '.part'), dst); tmp.unlink()
    print(json.dumps(dict(shard=shard, scored=len(out), sec=round(time.time() - t0))))


if __name__ == '__main__':
    if sys.argv[1] == 'prep':
        prep(sys.argv[2], '--calib' in sys.argv)
    else:
        score(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
