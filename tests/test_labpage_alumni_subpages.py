"""Berkeley Tomizuka (recall-gap round 1113): alumni.html is an index; the dated alumni lists are its sub-pages (phd_alumni.html, masters_alumni.html, prev_postdocs.html)."""
import labpage_audit as L


class FakeKit:
    def __init__(self):
        self.got = []

    def get(self, url):
        self.got.append(url)
        return dict(status=200, content=b'x', url=url)


def _run(monkeypatch, links):
    monkeypatch.setattr(L, 'site_links', lambda kit, row, base: links)
    monkeypatch.setattr(L, 'link_base', lambda row, url: url)
    kit, seen = FakeKit(), []
    ok = L.fetch_alumni_subpages(kit, 'https://msc.berkeley.edu/people/alumni.html', lambda *a, **k: seen.append(a))
    return ok, kit, seen


def test_alumni_index_subpages_are_fetched(monkeypatch):
    links = [('https://msc.berkeley.edu/people/phd_alumni.html', 'PhD Alumni'), ('https://msc.berkeley.edu/people/masters_alumni.html', 'Master Alumni'),
             ('https://msc.berkeley.edu/people/prev_postdocs.html', 'Previous Post-Doctoral Researchers'),
             ('https://msc.berkeley.edu/people/students.html', 'PhD Students'), ('https://msc.berkeley.edu/people/tomizuka.html', 'Professor'),
             ('https://other.example.org/alumni.html', 'Alumni'), ('https://msc.berkeley.edu/people/alumni.html', 'Alumni')]
    ok, kit, seen = _run(monkeypatch, links)
    assert ok == ['https://msc.berkeley.edu/people/phd_alumni.html', 'https://msc.berkeley.edu/people/masters_alumni.html', 'https://msc.berkeley.edu/people/prev_postdocs.html']
    assert kit.got[0] == 'https://msc.berkeley.edu/people/alumni.html' and len(kit.got) == 4
    assert seen and '3 of 3' in seen[0][2]


def test_cap_and_no_sublinks(monkeypatch):
    many = [(f'https://msc.berkeley.edu/people/past{i}.html', 'Past') for i in range(10)]
    ok, _kit, _ = _run(monkeypatch, many)
    assert len(ok) == 6
    ok, _kit, _ = _run(monkeypatch, [('https://msc.berkeley.edu/people/students.html', 'PhD Students')])
    assert ok == []


def test_registered_site_outranks_other_candidates():
    assert L.registered_site('https://iconlab.negarmehr.com/people', 'https://iconlab.negarmehr.com/people/')
    assert not L.registered_site('https://negarmehr.com/', 'https://iconlab.negarmehr.com/people/')
    assert not L.registered_site('https://negarmehr.com/', None)
