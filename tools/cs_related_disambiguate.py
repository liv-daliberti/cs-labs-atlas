"""A display name is not an identity (stage-2 gate): two candidate source records with one name ('Bin Li', two DBLP pids) must not share a decision key.
Post-step of `cs_related_school.py candidates <key>`: colliding names get their source id appended ('Bin Li [89/6764-38]'); unique names are untouched; idempotent.
usage: cs_related_disambiguate.py <key>"""
import collections
import json
import re
import sys

import atlas_paths as P


def toks(name):
    return re.sub(r'\s*\[[^\]]*\]$', '', name or '').lower().split()


def source_id(c):
    """A short source identity of a candidate: the DBLP pid tail ('89/6764-38') or the OpenAlex author id ('A5069353502')."""
    if c.get('dblp'):
        return c['dblp'].rsplit('/pid/', 1)[-1]
    return (c.get('openalex') or ['?'])[0].rsplit('/', 1)[-1]


def disambiguate_display_names(cands):
    groups = collections.defaultdict(list)
    for c in cands:
        groups[' '.join(toks(c['name']))].append(c)
    for rows in groups.values():
        if len(rows) > 1:
            for c in rows:
                base = re.sub(r'\s*\[[^\]]*\]$', '', c['name'])
                c['name'] = f'{base} [{source_id(c)}]'
    return cands


def main(key):
    path = P.data_w('cs-related-candidates.json', key)
    out = disambiguate_display_names(json.loads(path.read_text()))
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(candidates=len(out), disambiguated=sum('[' in c['name'] for c in out))))


if __name__ == '__main__':
    main(sys.argv[1])
