"""Latin names of native-script census persons, from their own profile page (KAIST CS, 2026-11-24, coordinator ruling).

usage: profile_romanization_school.py <key>

A census person whose only listed name is Hangul (the School of Computing roster is Hangul-only from 2024H2) has a Latin name only when the SAME profile
(`[census].profile_id_pattern` id) states it: the live profile page is fetched (robots and per-host delay honoured, stored in the school's `live` table) and the
page text must hold `<Hangul name>[particle](<Latin name>)`. The sentence is kept as the verbatim quote with the page URL and its sha256. A page that does not state a
Latin name gives `romanization_missing`: nothing is guessed and no name is matched across profile ids. Writes reviewed/profile-romanization.json, which
census_build.py reads (display name = the stated Latin name, the Hangul spelling stays an alias).
"""
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402

HANGUL = re.compile(r'[가-힯]')
PARTICLES = '은는이가의도'


def stated_latin(flat, hangul):
    """(latin name, quote) when the page text gives `Hangul[particle](Latin Name)`, else (None, None)."""
    m = re.search(re.escape(hangul) + '[' + PARTICLES + r']?\s*\(\s*([A-Za-z][A-Za-z.\'\- ]{2,60}?)\s*\)', flat)
    return (m.group(1).strip(), m.group(0)) if m else (None, None)


def main(key):
    cfg = S.get(key)
    rx = re.compile(S.field(cfg, 'census.profile_id_pattern', '') or r'(?!)')
    census = json.loads(P.data('census-faculty.json', key).read_text())['faculty']
    rows = json.loads(P.data('rows.json', key).read_text())
    c = W.con(key)
    out, seen = [], set()
    for p in census:
        names = [p['name']] + list(p.get('aliases') or [])
        if any(not HANGUL.search(n) for n in names):
            continue   # a Latin spelling is already listed
        prof = {r['profile'] for r in rows if r['name_listed'] in names and r.get('profile')}
        for url in sorted(prof):
            m = rx.search(url)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            res = W.live(c, url)
            rec = dict(profile_id=m.group(1), profile_url=url, name_hangul=p['name'])
            if not res or res[0] != 200:
                out.append(dict(rec, status='romanization_missing', reason='profile page not fetched (status %s)' % (res[0] if res else 'disallowed')))
                continue
            flat = W.flat(res[2])
            latin, quote = stated_latin(flat, p['name'])
            if latin:
                out.append(dict(rec, status='page_stated', name_latin=latin,
                                evidence=dict(url=url, sha256=res[1], quote=quote, fetched_at=datetime.datetime.now().isoformat(timespec='seconds'))))
            else:
                out.append(dict(rec, status='romanization_missing', reason='the profile page states no Latin name next to the Hangul name',
                                evidence=dict(url=url, sha256=res[1])))
    P.data_w('profile-romanization.json', key).write_text(json.dumps(dict(school=key, rows=out), ensure_ascii=False, indent=1))
    print(json.dumps(dict(persons=len(out), page_stated=sum(r['status'] == 'page_stated' for r in out), missing=sum(r['status'] != 'page_stated' for r in out))))


if __name__ == '__main__':
    main(sys.argv[1])
