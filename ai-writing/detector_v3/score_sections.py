"""Score every main and appendix passage of the section-tagged extraction with a v3 model.

input   one or more sections containers (ai-writing/data/sections/sections.sqlite, extra containers from extract_missing.py):
        sections(paper_id, key, school, main zlib, appendix zlib, ...). Passages are cut exactly as run_split.py cut them for the
        `passages` table: common.passages(main) then common.passages(appendix), i = running index, section main | appendix.
model   detector_v3 models/<tag>/model (default 'all'); operating point from results/operating_point.json (cal-only threshold and
        abstain rule, eval3.operating_point): flagged = z >= thr_z and not abstained; abstained = words < 100 or mid-sentence-capital
        share > the cal 95th percentile (both computed on the raw passage, as in the validation).
output  results/sections-<tag>/scores-<shard>.sqlite: scores(paper_id, i, section, words, midcap, z, abstain, flagged), index (paper_id, i);
        joins to sections.sqlite passages(paper_id, i). Resumable per container+shard (an existing file is skipped).
usage: score_sections.py --shard I --nshards N [--tag all] [--containers a.sqlite b.sqlite]
"""
import argparse, json, sqlite3, time, zlib
from pathlib import Path
import numpy as np
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import v3common as C
import detector as D2  # v2 predict (fp32 head)

V = C.V
DEFAULT = [str(C.AIW / 'data' / 'sections' / 'sections.sqlite')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shard', type=int, required=True); ap.add_argument('--nshards', type=int, required=True)
    ap.add_argument('--tag', default='all'); ap.add_argument('--containers', nargs='*', default=DEFAULT)
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    t0 = time.time()
    op = json.load(open(C.RESULTS / 'operating_point.json'))
    thr, cut = op['thr_z'], op['midcap_cut']
    out = C.RESULTS / f'sections-{a.tag}'; out.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(C.MODELS / a.tag / 'model')
    model = AutoModelForSequenceClassification.from_pretrained(C.MODELS / a.tag / 'model').cuda().eval()
    for ci, path in enumerate(a.containers):
        dst = out / f'scores-{Path(path).stem}-{a.shard}.sqlite'
        if dst.exists():
            continue
        db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        rows = []
        q = 'select paper_id, main, appendix from sections where rowid % ? = ?' + (f' limit {a.limit}' if a.limit else '')
        for pid, m, ap_ in db.execute(q, (a.nshards, a.shard)):
            mt = zlib.decompress(m).decode('utf-8', 'ignore') if m else ''
            at = zlib.decompress(ap_).decode('utf-8', 'ignore') if ap_ else ''
            for i, (s, p) in enumerate([('main', x) for x in V.passages(mt)] + [('appendix', x) for x in (V.passages(at) if at else [])]):
                rows.append((pid, i, s, p))
        db.close()
        print(json.dumps(dict(container=path, shard=a.shard, passages=len(rows), minutes=round((time.time() - t0) / 60, 1))), flush=True)
        p = D2.predict(model, tok, [V.norm(r[3]) for r in rows], bs=128)
        z = np.log(np.clip(p, 1e-300, None)) - np.log(np.clip(1 - p, 1e-300, None))
        tmp = out / f'tmp-{Path(path).stem}-{a.shard}.sqlite'
        tmp.unlink(missing_ok=True)
        o = sqlite3.connect(tmp)
        o.execute('create table scores (paper_id text, i int, section text, words int, midcap real, z real, abstain int, flagged int)')
        batch = []
        for (pid, i, s, t), zz in zip(rows, z):
            w = len(t.split()); mc = V.quality(t)['midcap']
            ab = int(w < op['abstain_words'] or mc > cut)
            batch.append((pid, i, s, w, mc, float(zz), ab, int((not ab) and zz >= thr)))
        o.executemany('insert into scores values (?,?,?,?,?,?,?,?)', batch)
        o.execute('create index sc on scores (paper_id, i)'); o.commit(); o.close()
        tmp.replace(dst)
        print(json.dumps(dict(done=str(dst), rows=len(batch), minutes=round((time.time() - t0) / 60, 1))), flush=True)


if __name__ == '__main__':
    main()
