"""Merge shard-*.sqlite into sections.sqlite and verify the join to the existing passage scores.
usage: merge_sections.py DIR   (DIR = ai-writing/data/sections)
Join check: ai_scores.sqlite passages (paper_id, pidx) and detector_v2/passage_scores.jsonl.gz (key, pidx) against passage_tags."""
import gzip
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'tools'))
import atlas_paths as P  # noqa: E402

d = Path(sys.argv[1]); out = d / 'sections.sqlite'
tmp = Path('/tmp') / f'sections-merge-{out.stat().st_ino if out.exists() else 0}.sqlite'
tmp.unlink(missing_ok=True)
db = sqlite3.connect(tmp)
shards = sorted(d.glob('shard-*.sqlite'))
for i, s in enumerate(shards):
    db.execute(f"attach '{s}' as s{i}")
    if i == 0:
        for t in ('sections', 'passage_tags', 'passages'):
            db.execute(f'create table {t} as select * from s0.{t}')
    else:
        for t in ('sections', 'passage_tags', 'passages'):
            db.execute(f'insert into {t} select * from s{i}.{t}')
    db.commit(); db.execute(f'detach s{i}')
db.execute('create unique index sec_pk on sections (paper_id)'); db.execute('create index pt_i on passage_tags (src, id, pidx)'); db.execute('create index pp_i on passages (paper_id)')
db.commit()
res = dict(shards=len(shards), papers=db.execute('select count(*) from sections').fetchone()[0])
cols = 'sum(copy_missing), sum(split_error is not null), sum(appendix_found), sum(truncated), sum(n_main_passages), sum(n_main_identical), sum(n_old_passages), sum(n_appendix_passages)'
for k, v in zip(('copy_missing', 'split_error', 'appendix_found', 'truncated', 'main_passages_new', 'main_identical', 'old_passages', 'appendix_passages_new'), db.execute(f'select {cols} from sections').fetchone()):
    res[k] = v
res['papers_all_main_identical'] = db.execute('select count(*) from sections where n_main_identical = n_old_passages and n_main_passages = n_old_passages').fetchone()[0]
res['tags_by_src'] = {f'{s}/{t}': n for s, t, n in db.execute('select src, section, count(*) from passage_tags group by 1, 2')}
# join: ai_scores passages
a = sqlite3.connect(f'file:{P.AI_SCORES}/ai_scores.sqlite?mode=ro', uri=True)
tags = {}
for pid, pidx, sec in db.execute("select id, pidx, section from passage_tags where src = 'ai_scores'"):
    tags[(pid, pidx)] = sec
c, n = Counter(), 0
for pid, pidx in a.execute('select paper_id, pidx from passages'):
    c[tags.get((pid, pidx), 'NO_TAG')] += 1; n += 1
res['ai_scores_passages'] = n; res['ai_scores_join'] = dict(c)
del tags
tags = {}
for k, pidx, sec in db.execute("select id, pidx, section from passage_tags where src = 'detector_v2'"):
    tags[(k, pidx)] = sec
c, n = Counter(), 0
for line in gzip.open(P.AI_WRITING / 'detector_v2' / 'passage_scores.jsonl.gz', 'rt'):
    r = json.loads(line); c[tags.get((r['key'], r['pidx']), 'NO_TAG')] += 1; n += 1
res['detector_passages'] = n; res['detector_join'] = dict(c)
db.execute('create table meta (k text, v text)'); db.execute('insert into meta values (?,?)', ('verify', json.dumps(res))); db.commit(); db.close()
import shutil  # noqa: E402
shutil.copy2(tmp, out.with_suffix('.tmp')); out.with_suffix('.tmp').rename(out); tmp.unlink()
print(json.dumps(res, indent=1))
