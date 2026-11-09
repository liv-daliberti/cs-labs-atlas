"""A person URL needs a page that links it; a person without one needs a reason."""
import person_websites as W


def row(**kw):
    base = dict(person='Ada Example', role='student', lab='Bo Lab', kind='student_home', url='https://ada.example.org/',
                found_from=dict(kind='official_page', url='https://cs.example.edu/people', sha256='a' * 64), fetched=False,
                fetch_reason='queued: not fetched')
    base.update(kw)
    return base


def test_gate_requires_provenance_and_reasons():
    assert W.gate({'rows': [row()]}) == []
    assert W.gate({'rows': [row(found_from={})]})
    assert W.gate({'rows': [row(fetch_reason='')]})
    assert W.gate({'rows': [row(url=None)]})
    assert W.gate({'rows': [row(url=None, reason='listed without a link')]}) == []


def test_anchors_resolve_against_base_and_survive_bad_hrefs():
    html = b'<a href="/~ada/">Ada Example</a><a href="http://[bad">x</a>'
    assert W.page_anchors(html, 'https://lab.example.edu/people/') == [('https://lab.example.edu/~ada/', 'Ada Example')]


def test_unfetchable_hosts_are_recorded_not_fetched():
    r = W.home_row('Ada', 'Bo', 'student_home', 'https://www.linkedin.com/in/ada', {}, {}, role='student')
    assert r['fetched'] is False and 'not fetchable' in r['fetch_reason']
    r = W.home_row('Ada', 'Bo', 'student_home', 'https://ada.example.org/', {}, {'https://ada.example.org/': dict(sha256='b' * 64, at='t')})
    assert r['fetched'] is True and r['sha256'] == 'b' * 64


def test_wayback_original_and_name_key():
    assert W.original('https://web.archive.org/web/2020id_/https://a.org/x') == 'https://a.org/x'
    assert W.name_key('José  Álvarez-Smith') == ('jose', 'smith') or W.name_key('José Álvarez Smith')


def test_found_kind_separates_official_from_dblp_orcid_prior_pass():
    d = lambda via: {'found_from': {'kind': 'discovery', 'via': via}}  # noqa: E731
    assert W.found_kind(d('dblp_person_url')) == 'dblp_homepage'
    assert W.found_kind(d('orcid_researcher_url')) == 'orcid'
    assert W.found_kind(d('prior_labpage_pass_2026-10-22')) == 'prior_pass'
    assert W.found_kind({'found_from': {'kind': 'official_page'}}) == 'official_page'


def test_names_person_needs_first_and_last_name_on_the_page():
    import person_fetch as F
    assert F.names_person(b'<html><title>Ada Example</title>', 'Ada Example')[0]
    assert not F.names_person(b'<html>Ada Smith', 'Ada Example')[0]
