"""`cs_related_school.py units` follows the pages of a paged unit directory (Georgia Tech friction 18)."""
import cs_related_school as C


def test_unit_pages_are_captured_for_the_same_year(monkeypatch):
    html = '<nav class="pager"><a href="?page=1">2</a><a href="?page=2">3</a></nav>'
    got = []
    monkeypatch.setattr(C.W, 'raw_html', lambda c, cap: html)

    def cdx(c, url, **k):
        return [dict(timestamp='20200301000000', original='https://u.edu/' + url.split('/', 1)[1]), dict(timestamp='20200901000000', original='https://u.edu/' + url.split('/', 1)[1])] if url.endswith('page=1') else []
    monkeypatch.setattr(C.W, 'cdx_rows', cdx)
    monkeypatch.setattr(C.W, 'capture', lambda c, ts, orig, url, code: got.append((ts, orig, code)) or ('cap', 200, 's', []))
    n = C.unit_pages_of(None, 'cap0', dict(timestamp='20200401000000', original='https://u.edu/people'), 'MATH', 'u.edu/people')
    assert n == 1 and got == [('20200301000000', 'https://u.edu/people?page=1', 'MATH')]   # page 2 is not archived; the nearest capture of page 1 wins


def test_an_unpaged_unit_page_adds_nothing(monkeypatch):
    monkeypatch.setattr(C.W, 'raw_html', lambda c, cap: '<ul><li>Ann Lee, Professor</li></ul>')
    assert C.unit_pages_of(None, 'cap0', dict(timestamp='20200401000000', original='https://u.edu/people'), 'X', 'u.edu/people') == 0


def test_faculty_evidence_matches_middle_initials_and_initial_first_given_names():
    pages = [('AE', 'u', 'sha', '20180101', 'Postdoctoral Fellow Montgomery-Knight View Full Profile Karen M Feigh Associate Professor Knight-419 View Full Profile Eric Feron'),
             ('SB', 'u2', 'sha2', '20180101', 'Todd, Bill Toktay, L. Beril Associate Professor Faculty Turner, Deborah')]
    ev = C.faculty_evidence(pages, ['Karen M. Feigh'])
    assert ev and ev[0]['unit'] == 'AE' and ev[0]['quote'].endswith('Associate Professor') and ev[0]['ladder']
    assert C.faculty_evidence(pages, ['L. Beril Toktay'])[0]['unit'] == 'SB'
    assert C.faculty_evidence(pages, ['Karen Smith']) == []
