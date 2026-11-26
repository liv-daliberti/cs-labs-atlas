"""ETH Zurich stage 2: faculty evidence from the department people lists that are built by JavaScript (docs/JS-RENDER.md).

BAUG, BIOL, BSSE, HEST, MATL, MTEC and PHYS publish PersonListCard lists ('Last, First, Prof. Dr.') that no static fetch or Wayback capture holds.
tools/js_render_capture.py stored the rendered DOM of each list (table js_render of the school's capture store, sha256 = dom_sha256). This tool
writes one reviewed/cs-related-hand.json entry per professor card ('Prof.' in the card's name line, not emeritus): name, unit, url, sha256, observed
date and the verbatim card text as the quote, which hand_evidence() re-verifies against the stored DOM. Entries of other sources are kept.

usage: eth_js_hand.py ethz [--write]
"""
import json
import re
import sys
import zlib

import atlas_paths as P
import school_web as W

UNITS = {'baug.ethz.ch': 'BAUG', 'biol.ethz.ch': 'BIOL', 'bsse.ethz.ch': 'BSSE', 'hest.ethz.ch': 'HEST', 'mat.ethz.ch': 'MATL', 'mtec.ethz.ch': 'MTEC',
         'www.phys.ethz.ch': 'PHYS', 'math.ethz.ch': 'MATH', 'chab.ethz.ch': 'CHAB', 'usys.ethz.ch': 'USYS', 'eaps.ethz.ch': 'EAPS', 'arch.ethz.ch': 'ARCH',
         'gess.ethz.ch': 'GESS'}
PROFESSOR_PAGE = re.compile(r'/professors?(?:-[a-z]+)*\.html|/who-is-who/', re.I)


def professor_section(url):
    """True when the page is a department's professors list. A general people/staff list gives 'Prof. Dr.' to guests, lecturers,
    Privatdozenten and professors appointed elsewhere (D-0055 needs an ETH professorship), so its cards are not ladder evidence."""
    return bool(PROFESSOR_PAGE.search(url))


CARD = re.compile(r'^([^,|]{2,45}),\s+([^,|]{2,60}),\s+((?:em\.\s+)?Prof\.(?:\s+(?:Dr\.|em\.|h\.c\.|Dr\.\s*h\.c\.))*(?:\s+Dr\.)?(?:\s+\S{0,6}\.)?)$')


def flat(dom, url):
    return W.flat(W.extract.blocks(dom, 'text/html', url))


def main(key, write=False):
    from bs4 import BeautifulSoup
    c = W.con(key)
    out = []
    for url, fetched, dsha, dz in c.execute('select url, fetched_at, dom_sha256, dom_zlib from js_render order by url'):
        host = re.sub(r'^https?://', '', url).split('/')[0]
        unit = UNITS.get(host)
        who = re.search(r'/who-is-who/([a-z]+)\.html$', url)   # ETH's central who-is-who, one page per department (current professors; retired-professors is emeriti, skipped)
        if host == 'ethz.ch' and who and who.group(1) != 'retired-professors':
            unit = {'matl': 'MATL'}.get(who.group(1), who.group(1).upper())
        elif host == 'ethz.ch' or not unit or url.rstrip('/').endswith('gess.ethz.ch'):
            continue
        dom = zlib.decompress(dz)
        text = ' '.join(flat(dom, url).split())
        soup = BeautifulSoup(dom, 'html.parser')
        seen = set()
        for el in soup.select('.PersonListCard__name'):
            raw = ' '.join(el.get_text(' ', strip=True).replace('\xa0', ' ').split())
            m = CARD.match(raw)
            if not m or 'em.' in m.group(3) or raw in seen:
                continue
            seen.add(raw)
            if raw not in text:
                continue
            nm = f'{m.group(2)} {m.group(1)}'
            out.append(dict(name=nm, unit=unit, url=url, sha256=dsha, observed=fetched[:10].replace('-', ''), quote=raw, ladder=professor_section(url),
                            source='js_render PersonListCard (tools/eth_js_hand.py)'))
    print(json.dumps({u: sum(1 for e in out if e['unit'] == u) for u in sorted({e['unit'] for e in out})}), len(out))
    if write:
        path = P.data_w('cs-related-hand.json', key)
        old = [e for e in (json.loads(path.read_text()) if path.exists() else []) if not str(e.get('source', '')).startswith('js_render PersonListCard')]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(old + out, indent=1, ensure_ascii=False))
        print('wrote', path)


if __name__ == '__main__':
    main(sys.argv[1], '--write' in sys.argv)
