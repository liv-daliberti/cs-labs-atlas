"""The passage detector (detector_v2, final model 'all') on the cited works' full texts in ft.sqlite.

Same model, splitter (v2common.passages = diversity/common.passages), normalizer (v2common.norm), fp32-head
predict() and usable-text rule as detector_v2/detector.py score; the only change is where the output goes, so that
nothing under detector_v2/results/ is touched:
  -> /n/fs/resemble/cs-atlas-cache/citations/v2scores/shard-<i>.jsonl.gz {key, pidx, words, p}
     and papers-<i>.jsonl.gz {key, kind, usable, body_words, n_passages}
Each task reads a contiguous rowid range of a node-local copy of ft.sqlite.
usage: v2score.py SHARD NSHARDS
"""
import gzip, importlib.util, json, os, shutil, sqlite3, sys, time, zlib
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
D2 = HERE.parent / 'detector_v2'
sys.path.insert(0, str(D2))
import v2common as V  # noqa: E402

spec = importlib.util.spec_from_file_location('detector_v2_detector', D2 / 'detector.py')
DET = importlib.util.module_from_spec(spec); spec.loader.exec_module(DET)
CACHE = Path('/n/fs/resemble/cs-atlas-cache/citations')
OUT = CACHE / 'v2scores'


def main(shard, nshards):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    t0 = time.time()
    local = Path(os.environ.get('TMPDIR', '/tmp')) / f'cit_ft_{os.getpid()}.sqlite'
    shutil.copy(CACHE / 'ft.sqlite', local)
    tag = V.MODELS / 'all' / 'model'
    tok = AutoTokenizer.from_pretrained(tag)
    model = AutoModelForSequenceClassification.from_pretrained(tag).cuda().eval()
    db = sqlite3.connect(f'file:{local}?mode=ro&immutable=1', uri=True)
    hi = db.execute('select max(rowid) from texts').fetchone()[0]
    step = hi // nshards + 1; lo = shard * step
    keys, pidx, words, texts, papers = [], [], [], [], []
    for key, kind, body, flags in db.execute('select key, kind, body, flags from texts where rowid >= ? and rowid < ?', (lo, lo + step)):
        body = zlib.decompress(body).decode('utf-8', 'ignore') if body else ''
        ps = V.passages(body) if body else []
        papers.append(dict(key=key, kind=kind, usable=bool(body) and V.usable_text(kind, body, json.loads(flags or '{}')),
                           body_words=len(body.split()), n_passages=len(ps)))
        for i, t in enumerate(ps):
            keys.append(key); pidx.append(i); words.append(len(t.split())); texts.append(V.norm(t))
    db.close(); local.unlink()
    DET.log(shard=shard, passages=len(texts), papers=len(papers), minutes=round((time.time() - t0) / 60, 1))
    p = DET.predict(model, tok, texts, bs=DET.SCORE_BS)
    OUT.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(os.environ.get('TMPDIR', '/tmp'))
    for name, rows in ((f'shard-{shard}.jsonl.gz', [dict(key=k, pidx=i, words=w, p=DET.r6(s)) for k, i, w, s in zip(keys, pidx, words, p)]),
                       (f'papers-{shard}.jsonl.gz', papers)):
        t = tmpdir / f'cit_{os.getpid()}_{name}'
        with gzip.open(t, 'wt') as f:
            for r in rows:
                f.write(json.dumps(r) + '\n')
        shutil.copy(t, OUT / (name + '.part')); os.replace(OUT / (name + '.part'), OUT / name); t.unlink()
    DET.log(shard=shard, done=len(texts), minutes=round((time.time() - t0) / 60, 1))


if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
