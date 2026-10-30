"""The 2026-10-29 data-quality pass: link-gap rules (R-STU-09..11, R-LNK-04a), re-captured relation evidence (R-STU-08,
R-AUD-09) and reviewed move periods (R-PAP-03). Real cases from the link-gap sample (hierarchy/logs/tmp-ids/linkgaps/)."""
import json

import pi_hierarchy as h
import evidence_check as ec

SE_PHD = ('Cheng Moreno Advisor: David Garlan Publications ... Waqar Ahmad Advisor: Jonathan Aldrich and Christian Kästner '
          'Publications ... Daniel Smullen Advisor: Travis Breaux and David Garlan Office ...')


def test_own_roster_entry_se_phd_page():
    assert h.own_roster_entry(SE_PHD, ['Cheng Moreno'], ['Jonathan Aldrich']) == 'names_other'
    assert h.own_roster_entry(SE_PHD, ['Waqar Ahmad'], ['Christian Kästner']) == 'names_pi'
    assert h.own_roster_entry(SE_PHD, ['Waqar Ahmad'], ['Jonathan Aldrich']) == 'names_pi'
    assert h.own_roster_entry(SE_PHD, ['Daniel Smullen'], ['Jonathan Aldrich']) == 'names_other'
    assert h.own_roster_entry(SE_PHD, ['Daniel Smullen'], ['David Garlan']) == 'names_pi'
    # a single-entry quote is not judged here (R-STU-02 and relation_names_other_adviser handle it)
    assert h.own_roster_entry('Howard Chen — Adviser(s): Danqi Chen', ['Howard Chen'], ['Karthik Narasimhan']) == 'single'
    rel = dict(sources=[dict(quote=SE_PHD)])
    assert h.relation_own_entry_names_other(rel, ['Cheng Moreno'], ['Jonathan Aldrich'])
    assert not h.relation_own_entry_names_other(rel, ['Waqar Ahmad'], ['Jonathan Aldrich'])


def _directory(program, adviser, n):
    return {f'p{i}': dict(person=f'p{i}', name=f'S {i}', relations=[dict(type='source_advising_context', sources=[dict(
        quote=f'Student {i} Program: {program} Email s{i}@x Academic Advisor: {adviser}')])]) for i in range(n)}


def test_program_adviser_groups_and_weak_relations():
    stu = {'Eric Nyberg': _directory('Master of Science in Computational Data Science', 'Eric Nyberg', 12),
           'Carolyn Rose': _directory('Master of Language Technologies', 'Carolyn Rose', 3)}
    stu['Teruko Mitamura'] = {f'q{i}': dict(person=f'q{i}', name='x', relations=[dict(sources=[dict(
        quote='Haoyang Wen Program: Ph.D. in Language and Information Technology Email h@x Academic Advisor: Teruko Mitamura')])]) for i in range(6)}
    g = h.program_adviser_groups(stu)
    assert ('Master of Science in Computational Data Science', 'Eric Nyberg') in g
    assert not any(p.startswith('Ph.D.') for p, _ in g)          # 6 PhD students: under 10, a research adviser
    assert not any(p == 'Master of Language Technologies' for p, _ in g)
    rel = stu['Eric Nyberg']['p0']['relations'][0]
    assert h.relation_is_program_advising(rel, g)
    assert not h.relation_is_program_advising(stu['Teruko Mitamura']['q0']['relations'][0], g)


def test_basis_record_advisor_field():
    assert h.dspace_advisors('"dc.contributor.advisor" : [ { "value" : "Freund, Robert M." } ]') == ['Robert M Freund']
    assert h.dspace_advisors('"dc.contributor.advisor" : [ { "value" : "Georgia Perakis and David Simchi-Levi." } ]') == \
        ['Georgia Perakis', 'David Simchi-Levi']
    assert h.dspace_advisors('Kirstin Early August 2017 Ph.D. Thesis') == []
    nm = h.Name(['Bart Van Parys'])
    assert not any(nm.match(a) for a in h.dspace_advisors('"dc.contributor.advisor" : [ { "value" : "Freund, Robert M." } ]'))


def test_nickname_additions():
    h.NICK_MAP = None
    assert h.nick_ok('manolis', 'emmanouil') and h.nick_ok('robbie', 'robert') and h.nick_ok('dima', 'dmitry')
    assert h.nick_ok('agi', 'agnes') and h.nick_ok('lily', 'lillian')


def test_apply_relation_evidence(tmp_path):
    (tmp_path / 'hierarchy' / 'cmu').mkdir(parents=True)
    url = 'https://ml.cmu.edu/people/alumni-phd-people/istelmakh'
    (tmp_path / 'hierarchy/cmu/relation-evidence.json').write_text(json.dumps(dict(records=[
        dict(url=url, person='cmu_person_5bbbbe2361a868d8dd74', pi='Aarti Singh', names_pi=True, sha256='a' * 64,
             quote='Ivan Stelmakh ... Advisor: Aarti Singh', capture_url=url, observed='2026-10-29', method='live'),
        dict(url='https://csd.cmu.edu/x', person='cmu_person_other', pi=None, names_pi=False, sha256='b' * 64, quote='Jane Doe PhD student')])))
    stu = {'Aarti Singh': {'cmu_person_5bbbbe2361a868d8dd74': dict(person='cmu_person_5bbbbe2361a868d8dd74', name='Ivan Stelmakh', relations=[
        dict(type='source_advising_context', sources=[dict(url=url, sha256='', quote='')])])},
           'Someone Else': {'ext:cmu:jane-doe': dict(person='ext:cmu:jane-doe', merged=['cmu_person_other'], name='Jane Doe', relations=[
               dict(type='source_advising_context', sources=[dict(url='https://csd.cmu.edu/x', sha256='c' * 64, quote='')])])}}
    n = h.apply_relation_evidence(stu, 'cmu', tmp_path)
    q = stu['Aarti Singh']['cmu_person_5bbbbe2361a868d8dd74']['relations'][0]['sources'][0]
    assert ec.sourced(q) and q['names_pi'] is True and 'original_sha256' not in q
    q2 = stu['Someone Else']['ext:cmu:jane-doe']['relations'][0]['sources'][0]
    assert ec.sourced(q2) and q2['names_pi'] is False and q2['original_sha256'] == 'c' * 64      # merged ids match too
    assert n['relation_evidence_recaptured_names_pi'] == 1 and n['relation_evidence_recaptured_student_only'] == 1
    rs = h.relation_source(stu['Someone Else']['ext:cmu:jane-doe'])
    assert rs['names_pi'] is False


def test_evidence_check_counts_student_only_quotes_apart(tmp_path):
    d = tmp_path / 'x'; d.mkdir()
    (d / 'pis.json').write_text('[]')
    src_pi = dict(url='u', sha256='a' * 64, quote='Ivan Stelmakh Advisor: Aarti Singh', names_pi=True)
    src_only = dict(url='u', sha256='a' * 64, quote='Jane Doe', names_pi=False)
    (d / 'students.json').write_text(json.dumps({'P': [dict(person='a', name='A', relations=[dict(sources=[src_pi])]),
                                                       dict(person='b', name='B', relations=[dict(sources=[src_only])]),
                                                       dict(person='c', name='C', relations=[dict(sources=[dict(url='u')])])]}))
    import gzip
    with gzip.open(d / 'lab_papers.jsonl.gz', 'wt') as f:
        f.write('')
    with gzip.open(d / 'student_papers.jsonl.gz', 'wt') as f:
        f.write(json.dumps(dict(pi='P', student='b', oa='W1', byline='Jane Doe', basis='within_lab_byline_match',
                                relation_source=dict(src_only))) + '\n')
    r = ec.check('x', tmp_path)
    assert r['student_relation']['n'] == 1 and r['student_relation_student_only']['n'] == 1
    assert r['link_relation_source']['n'] == 0 and r['link_relation_source_student_only']['n'] == 1


def test_reviewed_move_period_sets_stale_listings_aside():
    listings = {2016: dict(year=2016), 2026: dict(year=2026)}
    rudin = [dict(start='2009', end='2016', evidence=[dict(kind='faculty_end_moved', quote='Duke ... Associate Professor 2016-2019')])]
    assert set(h.listings_after_move(listings, [], rudin)) == {2026}
    assert h.listings_after_move(listings, [], [dict(start='2009', end='2016', evidence=[dict(kind='cv')])]) == {}
