"""CUHK D-0077 (2026-11-25): read the department profile of PIs whose own research statement is not yet in the capture store (live hosts only; robots, pacing and
challenge handling by labpage_audit.Kit). Candidate profile addresses follow each department's own pattern; one JSON line per fetch: name, url, status, sha256, the
research-statement snippet. Nothing is decided here.   usage: cuhk_statement_fetch.py <names-file>   (lines: name|url|url|...)"""
import json
import re
import sys

import labpage_audit as L

RX = re.compile(r'(research (interests?|areas?|topics?|fields?|focus|expertise)|areas? of (research|interest|expertise)|area of expertise|(his|her) research)', re.I)


def main(path):
    kit = L.Kit('cuhk')
    for line in open(path):
        name, *urls = line.rstrip('\n').split('|')
        for u in urls:
            r = kit.get(u, wb=False)
            t = ''
            if r.get('status') == 200 and r.get('content'):
                try:
                    t = kit.lpcap.page_text(r['content'], r.get('content_type'))
                except Exception:  # noqa: BLE001
                    t = ''
            m = RX.search(t)
            print(json.dumps(dict(name=name, url=u, status=r.get('status'), error=r.get('error'), sha256=r.get('sha256'),
                                  snippet=(t[m.start():m.start() + 420] if m else t[:240]).replace('\n', ' ')), ensure_ascii=False), flush=True)
            if r.get('status') == 200 and m:
                break


if __name__ == '__main__':
    main(sys.argv[1])
