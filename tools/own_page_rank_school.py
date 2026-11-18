"""Rank evidence from a person's OWN page for CSRankings/DBLP candidates whose homepage is on the school's web domain (owner D-0005, 2026-11-18).

A CSRankings entry binds a Latin name and a DBLP pid to a homepage; when that homepage is a page on the school's own domain, the page itself
is the rank source (its sentence naming the school and a ladder title, in the original script) and, for a Han-name page, the name pair. No
pinyin join: the URL is the identity link. Only hosts a charter allows live are fetched here (school_web.live honours robots.txt and
challenges); a wayback-only host is left to `cs_related_school.py profile` (Wayback). Writes reviewed/cs-related-hand.json entries
{name (the candidate's Latin name), unit, url, sha256 (a stored live capture), observed, quote, ladder: true, binding: csrankings_homepage}
that `cs_related_school.py review` verifies against the stored capture.

  own_page_rank_school.py <key> <recall.json> <unit> [--max N] [--wayback]   --wayback: a host that is wayback-only or answers no live page is read from the newest Wayback capture (one fetcher)
"""
import datetime, json, re, sys

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402

TITLE_NEAR = 160   # characters either side of a school mention in which the ladder title must stand


def rank_quote(text, school_rx, ladder_rx):
    """The first window of `text` that names the school and a ladder title (Chinese or English), or None."""
    for m in school_rx.finditer(text):
        win = text[max(0, m.start() - TITLE_NEAR): m.end() + TITLE_NEAR]
        t = next((x for x in ladder_rx.finditer(win) if not re.search(r'(?:客座|兼职|名誉|荣休|退休|adjunct|visiting|emeritus)\W*$', win[:x.start()], re.I)), None)
        if t:
            a = max(0, m.start() - TITLE_NEAR) + max(0, win.find(t.group(0)) - 40)
            seg = text[max(0, min(a, m.start() - 40)): max(m.end(), max(0, m.start() - TITLE_NEAR) + t.end()) + 12]
            return ' '.join(seg.split())
    return None


def main(key, recall, unit, limit=10**9, wayback=False):
    cfg = S.get(key)
    ladder = re.compile(r'(?<![助副理后])研究员|教授|大师讲席|\bprofessor\b', re.I)
    school = re.compile('|'.join(x for x in [S.field(cfg, 'affiliation.regex') or '', r'学院|研究院|研究所'] if x), re.I)
    doms = [d.lower() for d in (cfg.get('web') or {}).get('domains') or []]
    c = W.con(key)
    path = P.data('cs-related-hand.json', key)
    ents = json.loads(path.read_text()) if path.exists() else []
    have = {(e['name'], e['url']) for e in ents}
    done = n = 0
    for cand in json.load(open(recall))['candidates'].get(key, []):
        if 'csr' not in (cand.get('srcs') or []) or len(cand.get('dblp') or []) != 1:
            continue
        for h in cand.get('home') or []:
            url = h if h.startswith('http') else 'https://' + h
            host = re.sub(r'^https?://', '', url).split('/')[0].split(':')[0].lower()
            if not any(host == d or host.endswith('.' + d) for d in doms) or (S.host_use(key, host) != 'live' and not wayback):
                continue
            if (cand['name'], url) in have or n >= limit:
                continue
            n += 1
            if wayback and (S.host_use(key, host) != 'live' or not W.live(c, url)):   # a challenged / robots-blocked host: the newest Wayback capture of the page
                rows = W.cdx_rows(c, re.sub(r'^https?://', '', url), collapse='timestamp:4')
                best = sorted(rows or [], key=lambda x: x['timestamp'], reverse=True)[:1]
                got = W.capture(c, best[0]['timestamp'], best[0]['original'], url, unit) if best else None
                if not got or got[1] != 200:
                    print(json.dumps(dict(name=cand['name'], url=url, result='no Wayback capture')), flush=True)
                    continue
                cap, _st, sha, b = got
                q = rank_quote(W.flat(b), school, ladder)
                if not q:
                    print(json.dumps(dict(name=cand['name'], url=url, result='no ladder title near the school name (wayback)')), flush=True)
                    continue
                ents.append(dict(name=cand['name'], unit=unit, url=cap, sha256=sha, observed=best[0]['timestamp'], quote=q, ladder=True,
                                 binding='csrankings_homepage', dblp=cand['dblp'][0]))
                done += 1
                continue
            res = W.live(c, url)
            if not res or res[0] != 200:
                print(json.dumps(dict(name=cand['name'], url=url, result='not fetched', status=res and res[0])))
                continue
            text = W.flat(res[2])
            q = rank_quote(text, school, ladder)
            if not q:
                print(json.dumps(dict(name=cand['name'], url=url, result='no ladder title near the school name')))
                continue
            ents.append(dict(name=cand['name'], unit=unit, url=url, sha256=res[1], observed=datetime.date.today().isoformat().replace('-', ''),
                             quote=q, ladder=True, binding='csrankings_homepage', dblp=cand['dblp'][0]))
            done += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ents, indent=1, ensure_ascii=False))
    print(json.dumps(dict(key=key, tried=n, recorded=done)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10**9, '--wayback' in sys.argv)
