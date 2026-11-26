"""Parse ETH Board professorial entries (ethrat.ch releases) with the institution each entry belongs to.

An ETH Board release announces appointments, promotions and title awards at ETH Zurich AND at EPFL (rarely other ETH-domain institutes), under
section headings that vary ("New appointments at ETH Zurich", "Promotions at EPFL", "Award of the title of Professor at EPFL", ...) and sometimes with
no heading at all. Only ETH Zurich entries are evidence of an ETH professorship. The institution of an entry is decided in this order:
  1  the rank clause names it ("Adjunct Professor at EPFL", "... in the Department of X at ETH Zurich")
  2  the rank clause names an EPFL school or college ("in the School of Computer and Communication Sciences") with no ETH "Department of"
  3  the rank clause names an ETH "Department of X" with no school or college
  4  the nearest preceding section heading
  5  a release whose first heading is an EPFL one: entries before it are ETH Zurich
  otherwise 'unknown' (kept out of ETH evidence).
usage: board_entries.py            self-test on built-in samples
       board_entries.py build <key>   rebuild the Board entries of reviewed/official-lists.json from the stored releases, each with its institution
"""
import re
import sys

ENT = re.compile(r"((?:Professor|Prof\.|Dr\.?|PD Dr\.?)(?:\s+(?:Prof\.|Dr\.?))?\s+[^()]{3,70}?)\s+\(\*\d{4}\)[^.]{0,400}?,\s+as\s+([^.]{3,200}?)\.(?=\s|$)")
HEAD = re.compile(r"(?:(?:New )?(?:[Aa]ppointments?|[Pp]romotions?)|[Aa]ward of the title of [^A-Za-z]{0,2}[A-Za-z ]+?[^A-Za-z]{0,2}) at (?:the )?(ETH Zurich|ETH|EPFL|EFPL|PSI|Empa|WSL|Eawag)")
OTHER = re.compile(r"\b(?:PSI|Paul Scherrer|Empa|WSL|Eawag)\b")


def institution(rank, heading=None, before_first_epfl_heading=False):
    """-> (institution, method) with institution in 'ETH Zurich', 'EPFL', 'other', 'unknown'."""
    m = re.search(r"\bat (ETH Zurich|EPFL)\b", rank)
    if m:
        return ('ETH Zurich' if m.group(1) == 'ETH Zurich' else 'EPFL'), 'rank_suffix'
    school = bool(re.search(r"\b(?:School|College) of\b", rank))
    dept = bool(re.search(r"\bDepartment of\b", rank))
    if school and not dept:
        return 'EPFL', 'rank_school'
    if dept and not school:
        return 'ETH Zurich', 'rank_department'
    if heading:
        if re.search(r"EPFL|EFPL", heading):
            return 'EPFL', 'heading'
        if re.search(r"ETH", heading):
            return 'ETH Zurich', 'heading'
        return 'other', 'heading'
    if before_first_epfl_heading:
        return 'ETH Zurich', 'before_first_epfl_heading'
    if OTHER.search(rank):
        return 'other', 'rank_other'
    return 'unknown', 'none'


def clean_name(n):
    n = re.sub(r"^.*(?:at ETH Zurich|at EPFL|\u201d)\s+(?=\S)", '', n.strip()) if re.search(r"at ETH Zurich|at EPFL|\u201d", n) else n.strip()
    while re.match(r"^(?:Professor|Prof\.|Dr\.?(?:\s+h\.c\.)?|PD Dr\.?)\s+", n):
        n = re.sub(r"^(?:Professor|Prof\.|Dr\.?(?:\s+h\.c\.)?|PD Dr\.?)\s+", '', n)
    return n.strip()


def parse_release(text, url=None, date=None, sha256=None):
    """Entries of one release text (flattened): dict(name, rank, quote, institution, method, heading, url, date, sha256)."""
    heads = [(h.start(), h.group(0), h.group(1)) for h in HEAD.finditer(text)]
    first_epfl = next((p for p, _, i in heads if re.search(r'EPFL|EFPL', i)), None)
    first_eth = next((p for p, _, i in heads if i.startswith('ETH')), None)
    out = []
    for mm in ENT.finditer(text):
        prev = [h for h in heads if h[0] < mm.start()]
        head = prev[-1][1] if prev else None
        pre = first_epfl is not None and mm.start() < first_epfl and (first_eth is None or mm.start() < first_eth)
        inst, how = institution(mm.group(2), head, pre)
        out.append(dict(name=clean_name(mm.group(1)), rank=mm.group(2).strip(), quote=text[mm.start():mm.end()], institution=inst, method=how, heading=head,
                        url=url, date=date, sha256=sha256))
    return out


def _selftest():
    svensson = ("Promotions at EPFL Professor Ola Svensson (*1981), currently Associate Professor at EPFL, as Full Professor of Computer Science in the "
                "School of Computer and Communication Sciences. Ola Svensson's research area is the theory of computation.")
    e = parse_release("New appointments at ETH Zurich Professor Dagmar Iber (*1975), currently Associate Professor at ETH Zurich, as Full Professor of "
                      "Computational Biology in the Department of Biosystems Science and Engineering. Text. " + svensson)
    by = {x['name']: x for x in e}
    assert by['Ola Svensson']['institution'] == 'EPFL', by['Ola Svensson']
    assert by['Dagmar Iber']['institution'] == 'ETH Zurich', by['Dagmar Iber']
    # no heading at all, school named: EPFL; rank suffix wins over a stale heading
    f = parse_release("New appointments at ETH Zurich Professor A B (*1970), currently X at EPFL, as Adjunct Professor at EPFL. Text.")
    assert f[0]['institution'] == 'EPFL' and f[0]['method'] == 'rank_suffix'
    g = parse_release("Dr C D (*1980), currently Senior Scientist, as Full Professor of Physics. Appointments at EPFL Dr E F (*1985), currently Postdoc, as Associate Professor of Physics.")
    assert [x['institution'] for x in g] == ['ETH Zurich', 'EPFL'], g
    print('board_entries self-test ok')


def build(key):
    """Rebuild the board_appointment / board_retirement entries of official-lists.json (SNSF and Eccellenza entries are kept)."""
    import datetime
    import json
    import zlib
    import atlas_paths as P
    import school_web as W
    c = W.con(key)
    path = P.data_w('official-lists.json', key) if 'official-lists.json' in getattr(P, 'DATA_FILES', {}) else P.data('cs-related-hand.json', key).parent / 'official-lists.json'
    old = json.loads(path.read_text())
    keep = [e for e in old if e['list'] not in ('board_appointment', 'board_retirement')]
    day = lambda s: (datetime.datetime.strptime(s.replace('. ', ' '), '%d %B %Y').strftime('%Y%m%d') if s else None)
    out = []
    for u, sha, raw in c.execute("select url, sha256, raw_zlib from live where status=200 and url like 'https://ethrat.ch/en/%' order by url"):
        t = ' '.join(W.flat(W.extract.blocks(zlib.decompress(raw), 'text/html', u)).split())
        m = re.search(r'Media release \| (\d{1,2}\. \w+ \d{4})', t)
        for e in parse_release(t, u, day(m.group(1)) if m else None, sha):
            out.append(dict(list='board_appointment', name=e['name'], url=u, sha256=sha, date=e['date'], rank=e['rank'], quote=e['quote'],
                            institution=e['institution'], institution_basis=e['method']))
    for u, sha, raw in c.execute("select url, sha256, raw_zlib from live where status=200 and url like 'https://ethz.ch/en/news-and-events/eth-news/news/20%' order by url"):
        if not re.search(r'/(2013/12/new-professors|2016/\d\d/.*(professors|appointments))', u):
            continue
        t = ' '.join(W.flat(W.extract.blocks(zlib.decompress(raw), 'text/html', u)).split())
        m = re.search(r'(\d\d)\.(\d\d)\.(\d{4}) by', t)
        for e in parse_release(t, u, f'{m.group(3)}{m.group(2)}{m.group(1)}' if m else None, sha):
            out.append(dict(list='board_appointment', name=e['name'], url=u, sha256=sha, date=e['date'], rank=e['rank'], quote=e['quote'],
                            institution='ETH Zurich', institution_basis='eth_news_release_is_eth_only'))
    for e in old:   # retirements and resignations: kept as parsed (every entry names ETH Zurich as the employer it leaves)
        if e['list'] == 'board_retirement':
            q = e['quote']
            inst = 'ETH Zurich' if re.search(r'(?:Department of[^.]{0,160}at ETH Zurich|leav\w* ETH Zurich|Professor[^.]{0,120} at ETH Zurich)', q) else 'EPFL'
            out.append(dict(e, institution=inst, institution_basis='retirement_clause'))
    path.write_text(json.dumps(keep + out, ensure_ascii=False, indent=0))
    import collections
    print(json.dumps(dict(entries=len(out), by_institution=dict(collections.Counter(e['institution'] for e in out)))))


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'build':
        build(sys.argv[2])
    else:
        _selftest()
