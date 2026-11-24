"""Per-PI filtering of the school-wide derived files of a partial release (Q-0340, tools/pi_release_derived.py)."""
import json


import pi_release_derived as D

HELD = {'Hal Held'}


def plan(partial=True, included=('Ann Inc', 'Bob Inc'), held=('Hal Held',)):
    return dict(school='x', included=list(included), held={h: ['r'] for h in held}, partial=partial)


def test_named_records_and_drop():
    assert D.named('Hal Held', HELD) and not D.named('Ann Inc', HELD)
    assert D.named(dict(pi='Hal Held'), HELD) and D.named(dict(key='Hal Held | ext:s'), HELD) and D.named(['m', 'Hal Held', 's'], HELD)
    assert not D.named(dict(key=['hal', 'held']), HELD)
    doc = dict(a=['Hal Held', 'Ann Inc'], b=[dict(pi='Hal Held', n=1), dict(pi='Ann Inc', n=2)], c={'Hal Held': 1, 'Ann Inc': 2},
               d={'k1': dict(pi='Hal Held'), 'k2': dict(pi='Ann Inc')}, e=dict(unexplained=[dict(key='Hal Held'), dict(key='Ann Inc')], n_unexplained=2))
    out = D.drop(doc, HELD)
    assert out['a'] == ['Ann Inc'] and out['b'] == [dict(pi='Ann Inc', n=2)] and out['c'] == {'Ann Inc': 2} and list(out['d']) == ['k2']
    assert out['e']['n_unexplained'] == 1 and not D.leaks(out, HELD) and D.leaks(doc, HELD)


def test_held_name_that_is_also_included_is_not_held():
    assert D.held_names(plan(held=('Hal Held', 'Ann Inc'))) == {'Hal Held'}


def test_report_keeps_provenance_and_counts_and_loses_held_lists():
    rep = dict(school='x', counts=dict(pis=3), provenance=dict(code=dict(commit='c')), pisWithoutPapers=['Hal Held', 'Ann Inc'],
               linkGuardSamples=[dict(pi='Hal Held', oa='W1')], notPaperSamples=dict(editorial=[dict(pi='Hal Held', oa='W2'), dict(pi='Bob Inc', oa='W3')]))
    out = D.filter_report(rep, HELD)
    assert out['counts'] == dict(pis=3) and out['provenance'] == rep['provenance'] and out['pisWithoutPapers'] == ['Ann Inc']
    assert out['linkGuardSamples'] == [] and out['notPaperSamples']['editorial'] == [dict(pi='Bob Inc', oa='W3')] and out['scope'] == D.SCOPE
    assert list(out)[:4] == ['school', 'counts', 'provenance', 'pisWithoutPapers']   # key order is the input's


def test_ledger_summary_is_recounted_like_the_ledger_builder():
    rows = [dict(reason_code='r1', publisher='P', final=True, missing_checks=['s2']), dict(reason_code='r1', publisher='Q', final=False, missing_checks=[]),
            dict(reason_code='r2', publisher='P', final=True, missing_checks=['s2', 'core'])]
    s = D.ledger_summary(dict(school='x', built_at='t', inputs={}, max_age_days=30), rows)
    assert (s['papers'], s['final'], s['not_final']) == (3, 2, 1) and s['by_reason'] == dict(r1=2, r2=1) and s['by_publisher'] == dict(P=2, Q=1)
    assert s['by_reason_publisher'] == dict(r1=dict(P=1, Q=1), r2=dict(P=1)) and s['missing_checks'] == dict(s2=2, core=1) and s['built_at'] == 't'


def test_link_diagnosis_drops_held_students_and_recounts_the_summary():
    ld = dict(summary=dict(a=2, b=1, total_note='x'), students={'Hal Held | s1': dict(pi='Hal Held', category='a'), 'Ann Inc | s2': dict(pi='Ann Inc', category='a'),
                                                                'Ann Inc | s3': dict(pi='Ann Inc', category='b')})
    out = D.filter_link_diagnosis(ld, HELD)
    assert list(out['students']) == ['Ann Inc | s2', 'Ann Inc | s3'] and out['summary'] == dict(a=1, b=1, total_note='x')


def test_shared_files_lose_only_the_partial_schools_held_rows():
    per = dict(x=dict(plan=plan()), y=dict(plan=plan(partial=False, held=())))
    homes = [dict(school='x', name='Hal Held'), dict(school='x', name='Ann Inc'), dict(school='y', name='Hal Held')]
    assert D.filter_home_departments(homes, per) == homes[1:]
    z = dict(zero_papers=[dict(school='x', pi='Hal Held', verdict='v'), dict(school='x', pi='Ann Inc', verdict='v'), dict(school='y', pi='Hal Held', verdict='v')],
             zero_students=[dict(school='x', pi='Hal Held'), dict(school='y', pi='Zed')], counts={'x:zero_papers:v': 2, 'x:zero_students': 1, 'y:zero_students': 1})
    out = D.filter_zero_paper_labs(z, per)
    assert [r['pi'] for r in out['zero_papers']] == ['Ann Inc', 'Hal Held'] and out['zero_students'] == [dict(school='y', pi='Zed')]
    assert out['counts'] == {'x:zero_papers:v': 1, 'y:zero_students': 1}
    entries = [dict(school='x', across=[['m', 'Hal Held', 's']], keep=1), dict(school='y', across=[['m', 'Hal Held', 's']])]
    got = D.per_school(entries, per)
    assert got[0]['across'] == [] and got[0]['scope'] == D.SCOPE and got[1] == entries[1]   # another school's namesake stays


def test_reader_export_follows_the_included_papers(monkeypatch):
    monkeypatch.setattr(D, 'paper_keys', lambda school, inc: {'W1', 'W2'})
    per = dict(x=dict(plan=plan()), y=dict(plan=plan(partial=False, held=())))
    rows_x = [dict(oa='W1', decision='host', sha256='a', license='cc-by', license_basis='asset', stored_copy=True, path='objects/a.pdf', school='x'),
              dict(oa='W3', decision='host', sha256='b', license='cc-by', license_basis='asset', stored_copy=True, path='objects/b.pdf', school='x'),
              dict(oa='W2', decision='link', link_basis='openalex_location', license=None, license_basis='none', stored_copy=False, school='x')]
    rows_y = [dict(oa='Y1', decision='host', sha256='c', license='cc-by', license_basis='asset', stored_copy=True, path='objects/c.pdf', school='y')]
    files = {
        'reader/x.jsonl.gz': D.gz_lines(rows_x), 'reader/y.jsonl.gz': D.gz_lines(rows_y),
        'reader/hosted-files.tsv': b'sha256\tbytes\tschool\tpath\na\t1\tx\tobjects/a.pdf\nb\t1\tx\tobjects/b.pdf\nc\t1\ty\tobjects/c.pdf\n',
        'reader/upload.tsv': b'sha256\tbytes\tschool\tpath\nb\t1\tx\tobjects/b.pdf\n',
        'reader/unpublish.tsv': b'sha256\tbytes\tpath\treason\tlicense\tbasis\tschools\tworks\n',
        'reader/link-check-requests.tsv': b'host\tschool\tkey\ttitle\ndx\tx\tW2\tt\ndx\tx\tW3\tu\ndy\ty\tY1\tv\n',
        'reader/SUMMARY.json': json.dumps(dict(schools=dict(x=dict(lab_papers=3), y=dict(lab_papers=1)), site_sync=dict(site_files=2, keep=1, upload=1, unpublish=0),
                                                hosted_files=3, link_check_request_urls=3, totals={})).encode()}
    out = D.filter_reader(per, set(files), lambda rel: files[rel])
    assert [r['oa'] for r in D.read_gz_lines(out['reader/x.jsonl.gz'])] == ['W1', 'W2'] and 'reader/y.jsonl.gz' not in out
    assert out['reader/hosted-files.tsv'].decode().split('\n')[1:-1] == ['a\t1\tx\tobjects/a.pdf', 'c\t1\ty\tobjects/c.pdf']
    assert out['reader/upload.tsv'].decode() == 'sha256\tbytes\tschool\tpath\n'            # b is not hosted by the filtered release, so nothing to add
    assert out['reader/link-check-requests.tsv'].decode().split('\n')[1:-1] == ['dx\tx\tW2\tt', 'dy\ty\tY1\tv']
    summ = json.loads(out['reader/SUMMARY.json'])
    assert summ['schools']['x']['readable'] == 2 and summ['schools']['x']['host'] == 1 and summ['schools']['x']['link'] == 1 and summ['hosted_files'] == 2
    assert summ['schools']['x']['newly_readable_from_candidates'] == 1 and summ['link_check_request_urls'] == 2 and summ['site_sync']['upload'] == 0


def test_a_hosted_file_the_site_has_today_is_unpublished_when_the_release_drops_it(monkeypatch):
    monkeypatch.setattr(D, 'paper_keys', lambda school, inc: {'W1'})
    per = dict(x=dict(plan=plan()))
    rows = [dict(oa='W1', decision='host', sha256='a', license='cc-by', license_basis='asset', stored_copy=True, school='x'),
            dict(oa='W3', decision='host', sha256='b', license='cc0', license_basis='asset', stored_copy=True, school='x', path='objects/b.pdf', bytes=7, catalog_work='x_w3')]
    files = {'reader/x.jsonl.gz': D.gz_lines(rows), 'reader/hosted-files.tsv': b'sha256\tbytes\tschool\tpath\na\t1\tx\tp\nb\t7\tx\tobjects/b.pdf\n',
             'reader/upload.tsv': b'sha256\tbytes\tschool\tpath\n', 'reader/unpublish.tsv': b'sha256\tbytes\tpath\treason\tlicense\tbasis\tschools\tworks\n'}
    out = D.filter_reader(per, set(files), lambda rel: files[rel])
    assert out['reader/unpublish.tsv'].decode().split('\n')[1] == 'b\t7\tobjects/b.pdf\toutside_release\tcc0\tasset\tx\tx_w3'


def test_nothing_partial_rewrites_nothing():
    assert D.filter_release_files(dict(x=dict(plan=plan(partial=False, held=()))), {}) == {}


def test_make_release_no_longer_refuses_a_partial_school():
    import make_release as MR
    t = open(MR.__file__).read()
    assert 'still name held PIs; --allow-derived-unfiltered' not in t and 'pi_release_derived' in t
