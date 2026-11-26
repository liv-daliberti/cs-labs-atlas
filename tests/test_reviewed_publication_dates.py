"""Publisher dates are exact metadata evidence, never appointment exceptions."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from pihier import papers, publication_dates
from test_build_rules import SCHOOL, SWEEP, OVERRIDES, put, rows_of, run_stages, write_school

pytestmark = pytest.mark.usefixtures('layout')


def install(root, monkeypatch, *, old='2020-05-01', date='2020-08-26', xml_change=None):
    monkeypatch.setattr(publication_dates.P, 'store', lambda school: root / 'stores' / school)
    work = deepcopy(SWEEP[0])
    work['publication_date'] = old
    write_school(root, sweep=[work])
    raw = (f'<article><front><article-meta><article-id pub-id-type="doi">10.1/w1</article-id>'
           '<title-group><article-title>Learning to Compute</article-title></title-group>'
           f'<pub-date pub-type="epub"><day>{int(date[8:])}</day><month>{int(date[5:7])}</month>'
           f'<year>{date[:4]}</year></pub-date>'
           '<history><date date-type="accepted"><day>1</day><month>5</month><year>2020</year>'
           '</date></history></article-meta></front></article>')
    raw = (xml_change(raw) if xml_change else raw).encode()
    sha = hashlib.sha256(raw).hexdigest()
    capture = publication_dates.P.store(SCHOOL) / 'metadata/publication-date-sources' / (sha + '.xml')
    capture.parent.mkdir(parents=True)
    capture.write_bytes(raw)
    review = dict(decision='correct_publication_date', match=dict(oa=work['id'], doi=work['doi']),
                  title=work['title'], previous_date=old, date=date, reviewed_by='independent-source-reviewer',
                  reviewed_on='2026-11-24', why='Indexed date is acceptance; original gives electronic publication.',
                  source=dict(url='https://publisher.example/article.xml', sha256=sha, source_file=sha + '.xml',
                              format='jats_xml', http_status=200, captured='2026-11-24T20:00:00+00:00'))
    put(root, 'publication-date-review.json').write_text(json.dumps(dict(version=1, school=SCHOOL, decisions=[review])))
    return work, review, capture


def test_publisher_date_replays_before_appointment_and_preserves_raw_index(tmp_path, monkeypatch):
    import test_build_rules as fixture
    overrides = deepcopy(OVERRIDES)
    overrides[SCHOOL]['Ada Lovelace']['periods'][0]['end'] = '2020-06-30'
    monkeypatch.setattr(fixture, 'OVERRIDES', overrides)
    work, _, _ = install(tmp_path, monkeypatch)
    original = deepcopy(work)
    # Correct publication is after departure. The formerly admitted May date
    # cannot keep this paper, despite its correct author and school byline.
    assert 'Learning to Compute' not in rows_of(run_stages(tmp_path), 'Ada Lovelace')
    assert work == original


def test_verified_publication_date_keeps_proof_without_changing_identity(tmp_path, monkeypatch):
    work, review, _ = install(tmp_path, monkeypatch)
    row = rows_of(run_stages(tmp_path), 'Ada Lovelace')['Learning to Compute']
    assert row['date'] == review['date'] and row['year'] == 2020
    assert row['identity'] == 'reviewed_openalex_author_id'
    assert row['dated_by']['oa_date'] == work['publication_date']
    assert row['dated_by']['source']['sha256'] == review['source']['sha256']


@pytest.mark.parametrize('change', [
    lambda s: s.replace('10.1/w1', '10.1/other'),
    lambda s: s.replace('Learning to Compute', 'Another article'),
    lambda s: s.replace('pub-type="epub"', 'pub-type="accepted"'),
    lambda s: s.replace('<day>26</day>', ''),
    lambda s: s.replace('<day>26</day>', '<day>25</day>'),
])
def test_wrong_article_acceptance_or_incomplete_date_fails_closed(tmp_path, monkeypatch, change):
    install(tmp_path, monkeypatch, xml_change=change)
    with pytest.raises(ValueError):
        run_stages(tmp_path)


@pytest.mark.parametrize('failure', ['bytes', 'missing', 'path', 'status', 'reviewer', 'changed_index'])
def test_changed_or_unreviewed_evidence_fails_closed(tmp_path, monkeypatch, failure):
    work, review, capture = install(tmp_path, monkeypatch)
    if failure == 'bytes':
        capture.write_bytes(capture.read_bytes() + b' ')
    elif failure == 'missing':
        capture.unlink()
    elif failure == 'path':
        review['source']['source_file'] = '../../elsewhere.xml'
    elif failure == 'status':
        review['source']['http_status'] = 403
    elif failure == 'reviewer':
        review['reviewed_by'] = ''
    else:
        work['publication_date'] = '2020-05-02'
    put(tmp_path, 'publication-date-review.json').write_text(json.dumps(dict(version=1, school=SCHOOL, decisions=[review])))
    ctx = SimpleNamespace(school=SCHOOL, here=tmp_path)
    with pytest.raises(ValueError):
        papers.venue_version_date(work, {}, ctx)


def test_no_review_preserves_ordinary_venue_version_rule(tmp_path):
    work = dict(id='https://openalex.org/W999', title='Old paper', type='preprint',
                publication_date='2020-05-01', publication_year=2020)
    ctx = SimpleNamespace(school=SCHOOL, here=tmp_path)
    date, proof = papers.venue_version_date(work, {papers.norm_title(work['title']): (2019, 'conf/example')}, ctx)
    assert date == '2019' and proof['venue_year'] == 2019
