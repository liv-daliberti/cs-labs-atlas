"""tools/ora_theses.py: supervisor-to-PI resolution (R-STU-03 logic) and the contributor parser."""

import ora_theses as O  # noqa: E402

PIS = [dict(pi='Aleks Kissinger', names=['Aleks Kissinger'], orcid=['0000-0001-0000-0001']),
       dict(pi='Paul Goldberg', names=['Paul Goldberg'], orcid=[]),
       dict(pi='Leslie Ann Goldberg', names=['Leslie Ann Goldberg'], orcid=[])]


def test_family_initial_unique_and_ambiguous():
    idx, orc = O.pi_index(PIS)
    assert O.supervisor_pi(dict(name='Kissinger, A', orcid=None), idx, orc) == ('Aleks Kissinger', 'family_initial')
    assert O.supervisor_pi(dict(name='Goldberg, P', orcid=None), idx, orc)[0] == 'Paul Goldberg'
    assert O.supervisor_pi(dict(name='Goldberg, L', orcid=None), idx, orc)[0] == 'Leslie Ann Goldberg'
    assert O.supervisor_pi(dict(name='Goldberg, X', orcid=None), idx, orc)[0] is None
    assert O.supervisor_pi(dict(name='Kissinger, A', orcid='0000-0001-0000-0001'), idx, orc)[1] == 'orcid'


def test_contributors_parse():
    h = ('<h4>Contributors</h4><div style="padding-bottom:10px"><a><span>+ </span>Townley, H\n</a><dl><dt>Institution:</dt><dd>University of Oxford</dd>'
         '<dt>Department:</dt><dd>Computer Science</dd><dt>Role:</dt><dd>Supervisor</dd></dl></div><script></script>')
    c = O.contributors(h)
    assert c and c[0]['name'] == 'Townley, H' and c[0]['role'] == 'Supervisor' and c[0]['department'] == 'Computer Science'


def test_oxford_person_index_strips_life_dates():
    import listing_formats as LF
    h = ('<li class="personIndex"><a href="/people/x"><span itemprop="name">Stephen Cameron (1958-2019)</span></a>'
         '<span class="list-unbulleted-extra">Reader in Computing Science</span></li>')
    assert LF.oxford_person_index(h)[0]['name_listed'] == 'Stephen Cameron'
