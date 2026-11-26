"""DBLP person records whose <url> is on a school web domain, one streamed pass over DBLP's dump (never dblp.org).

Cache for the Han-name schools' reciprocal homepage binding (tools/cn_rank_admit.py): a person's official homepage URL that a
department list links, listed in the DBLP person's own <url> fields, binds the DBLP person without any name matching.

  DBLP_HP_OUT=<out.json.gz> dblp_school_homepages.py <domain> [<domain> ...]     (nice; ~2-3 min)
  (the output path is an environment variable: dblp_dump_persons reads sys.argv[1] as a school key when imported)
-> {domain: ..., persons: [{pid, names, urls, affiliations, orcid, disambiguation, sha256, xml}]}
"""
import gzip
import hashlib
import json
import os
import re
import sys

OUT = os.environ['DBLP_HP_OUT'] if __name__ == '__main__' else None
DOMS = [d.lower() for d in sys.argv[1:]]
sys.argv = sys.argv[:1]   # before dblp_dump_persons is imported

from dblp_dump_persons import NOTE, URL, AUTH, records, text  # noqa: E402

NOTE_AFF = re.compile(r'<note[^>]*type="affiliation"[^>]*>(.*?)</note>', re.S)


def main(out, doms):
    persons = []
    for typ, k, body in records():
        if typ != 'www' or not k.startswith('homepages/'):
            continue
        urls = [text(u) for u in URL.findall(body)]
        hosts = [re.sub(r'^https?://', '', u).split('/')[0].split(':')[0].lower() for u in urls]
        if not any(h == d or h.endswith('.' + d) for h in hosts for d in doms):
            continue
        persons.append(dict(pid='https://dblp.org/pid/' + k.split('/', 1)[1], names=[text(a) for _, a in AUTH.findall(body)], urls=urls,
                            affiliations=[text(v) for v in NOTE_AFF.findall(body)],
                            orcid=sorted({m.group(1) for u in urls for m in [re.search(r'orcid\.org/([0-9X-]{19})', u)] if m}),
                            disambiguation=any(t_ == 'disambiguation' for t_, _ in NOTE.findall(body)),
                            sha256=hashlib.sha256(body.encode()).hexdigest(), xml=body))
    with gzip.open(out, 'wt', encoding='utf-8') as f:
        json.dump(dict(domains=doms, persons=persons), f, ensure_ascii=False)
    print(json.dumps(dict(persons=len(persons))))


if __name__ == '__main__':
    main(OUT, DOMS)
