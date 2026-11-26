import cs_related_school as CR

PAGES = {'u.example.org/dir?page=1': ['20190110000000', '20190110120000', '20190620000000', '20220301000000', '20220907000000', '20231201000000'],
         'u.example.org/dir?page=2': ['20190301000000', '20220501000000', '20220502000000'],
         'u.example.org/dir?page=3': ['20210101000000']}


def rows_for(url, frm, to, collapse):
    out = [dict(timestamp=ts, original='https://' + url) for ts in PAGES.get(url, []) if frm <= ts[:4] <= to]
    if collapse == 'timestamp:8':
        seen, kept = set(), []
        for r in out:
            if r['timestamp'][:8] not in seen:
                seen.add(r['timestamp'][:8]); kept.append(r)
        out = kept
    return out


def run(monkeypatch):
    calls, chosen = [], []
    def cdx_rows(c, want, exact=True, frm='2016', to='2026', collapse='timestamp:6', status_200=True):
        calls.append((want, frm, to, collapse)); return rows_for(want, frm, to, collapse)
    monkeypatch.setattr(CR.W, 'cdx_rows', cdx_rows)
    monkeypatch.setattr(CR.W, 'capture', lambda c, ts, orig, url, code: chosen.append((orig, ts)) or ('cap', 200, 'sha', []))
    monkeypatch.setattr(CR.W, 'raw_html', lambda c, cap: 'html')
    import listing_formats as LF
    monkeypatch.setattr(LF, 'is_paged', lambda h: True)
    monkeypatch.setattr(LF, 'page_links', lambda h, u: {n: f'https://u.example.org/dir?page={n}' for n in (1, 2, 3)})
    CR._PAGE_CDX.clear()
    for ts0 in ('20190401000000', '20220601000000', '20231101000000', '20240101000000'):
        CR.unit_pages_of(object(), 'cap', dict(timestamp=ts0, original='https://u.example.org/dir'), 'U', 'u.example.org/dir')
    return calls, chosen



def test_all_years_query_picks_the_same_capture_with_fewer_queries(monkeypatch):
    new_calls, new_chosen = run(monkeypatch)
    # reference: the per-year, uncollapsed query of the old unit_pages_of for each page and listing year
    ref = []
    for ts0 in ('20190401000000', '20220601000000', '20231101000000', '20240101000000'):
        for n in (1, 2, 3):
            want = f'u.example.org/dir?page={n}'
            rows = [x for x in rows_for(want, ts0[:4], ts0[:4], None) if x['timestamp'].startswith(ts0[:4])]
            if rows:
                x = min(rows, key=lambda z: abs(int(z['timestamp'][:8]) - int(ts0[:8])))
                ref.append((x['original'], x['timestamp']))
    assert new_chosen == ref and ref
    assert len(new_calls) == 3 and all(c[1:] == ('2016', '2026', 'timestamp:8') for c in new_calls)   # one query per page URL, not 3 x 4 listing years
