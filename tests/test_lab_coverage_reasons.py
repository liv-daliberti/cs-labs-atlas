"""Reasons for labs with no students: built from the lab's own audit record plus the school-level sources."""
import lab_coverage_reasons as R


def test_lab_facts_name_the_page_status_and_the_listed_members():
    rec = dict(lab_page=dict(status='none_found', reason_code='no_web_presence_found', urls={}), students=dict(page_status='no_lab_page', reason_code='no_lab_page'))
    assert R.lab_facts(rec) == 'lab page: status none_found (no_web_presence_found), no site found; students section: no_lab_page (no_lab_page)'
    rec = dict(lab_page=dict(status='found', reason_code='lab_site', urls={'lab_site': 'https://x.edu/lab'}), students=dict(page_status='audited', reason_code='gaps_proposed', listed_current=[1, 2], listed_alumni=[3], reason='3 undated'))
    f = R.lab_facts(rec)
    assert 'site https://x.edu/lab' in f and 'lists 3 members, none admitted' in f and '3 undated' in f


def test_school_sources_list_rosters_adviser_lists_and_the_thesis_note(monkeypatch):
    monkeypatch.setattr(R.S, 'get', lambda key: {'students': {'rosters': [{'url': 'a.edu/phd', 'kind': 'students'}]}, 'thesis': {'note': 'ETD pending'}})
    s = R.school_sources('k')
    assert any('a.edu/phd' in x and 'R-STU-02' in x for x in s) and any('none exist' in x for x in s) and s[-1] == 'thesis repository: ETD pending'
