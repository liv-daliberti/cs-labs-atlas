"""v3.1 sources: light-edit-weighted rewrites of train-split human passages (data/sources31.jsonl).

Candidates: data/human_train.jsonl.gz (train-split 2016-2021 passages, not a paper's first, 60-400 words, paper has a title).
New generators (yi9b, falcon3-10b, internlm3-8b, qwen3b, phi35mini): 3000 sources each; existing generators (V31LIGHT): 1500 each.
Tasks (light edits weighted): minimal 30%, polish 25%, paraphrase 20%, humanize 15%, partial 10%; temperature 0.2 / 0.5 / 0.8.
Train split only: the v3 test sets (and so every number) stay comparable. One passage per paper per generator round.
usage: prep31.py
"""
import gzip, json, random
from collections import Counter, defaultdict
import v3common as C
import prep as P2
from prep3 import SENT

V = C.V
TASKS = ['minimal'] * 6 + ['polish'] * 5 + ['paraphrase'] * 4 + ['humanize'] * 3 + ['partial'] * 2
TEMPS = (0.2, 0.5, 0.8)


def main():
    meta = P2.load_meta()
    by = defaultdict(list)
    for line in gzip.open(C.DATA / 'human_train.jsonl.gz', 'rt'):
        r = json.loads(line)
        n = len(r['text'].split())
        if r['pidx'] > 0 and 60 <= n <= 400 and meta.get(r['key'], (0, 0, ''))[2]:
            by[r['key']].append(r)
    keys = sorted(by)
    out = []
    plan = [(g, 3000) for g in C.V31NEW] + [(g, 1500) for g in C.V31LIGHT]
    for gi, (gen, n) in enumerate(plan):
        rng = random.Random(f'{C.SEED}|31|{gen}')
        ks = keys[:]; rng.shuffle(ks)
        picked = [rng.choice(by[k]) for k in ks[:n]]
        for m, r in enumerate(picked):
            task = TASKS[(m + rng.randrange(len(TASKS))) % len(TASKS)]
            s = dict(sid=f'{gen}-l-{m}', gen=gen, family=C.FAMILY[gen], split='train', key=r['key'], school=r['school'], year=r['year'], title=meta[r['key']][2],
                     kind=r['kind'], pidx=r['pidx'], text=r['text'], task=task, temp=TEMPS[rng.randrange(3)])
            if task == 'partial':
                ss = SENT.split(r['text'])
                if len(ss) < 3:
                    s['task'] = 'polish'
                else:
                    s['sel'] = sorted(rng.sample(range(len(ss)), max(1, round(len(ss) * rng.choice((0.3, 0.5, 0.7))))))
            out.append(s)
    with open(C.DATA / 'sources31.jsonl', 'w') as f:
        for s in out:
            f.write(json.dumps(s, ensure_ascii=False) + '\n')
    print(json.dumps(dict(sources=len(out), tasks=Counter(s['task'] for s in out), gens=Counter(s['gen'] for s in out))))


if __name__ == '__main__':
    main()
