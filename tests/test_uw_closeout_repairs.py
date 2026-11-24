"""Source failures found by UW's independent closeout review."""
import hashlib
import json

import pytest

import atlas_paths as P
import labpage_audit as L
import listing_formats as F
from listing_rows import quote_of
from pihier.periods import not_faculty_row
import stage_gate as G


def test_incoming_directory_office_is_not_a_faculty_appointment():
    html = """<h2>Faculty</h2><div class='directory-name'><a href='/althoff'>Tim Althoff</a></div>
    <div class='directory-office'>Arriving January 2019</div>
    <div class='directory-name'><a href='/anderson'>Richard Anderson</a></div>
    <div class='directory-office'>CSE 582</div>"""
    a, b = F.uw_allen_directory(html)
    assert a['titles'] == ['Faculty', 'Arriving January 2019']
    assert b['titles'] == ['Faculty']
    quote = quote_of('Faculty Tim Althoff Arriving January 2019 Richard Anderson CSE 582', a)
    assert 'Arriving January 2019' in quote and not_faculty_row(quote)
    assert not not_faculty_row('Richard Anderson')


@pytest.mark.parametrize(('indexed', 'listed', 'primary'), [
    ('NormAd: A Framework for Measuring Cultural Adaptability',
     'NormAd: A Benchmark for Measuring Cultural Adaptability',
     'N ORM A D: A Benchmark for Measuring Cultural Adaptability'),
    ('CQA-Eval: Designing Reliable Evaluations of Multi-paragraph Clinical QA',
     'LONGQAEVAL: Designing Reliable Evaluations of Long-Form Clinical QA',
     'L ONG QAE VAL: Designing Reliable Evaluations of Long-Form Clinical QA'),
])
def test_original_pdf_title_wins_over_conflicting_index(monkeypatch, indexed, listed, primary):
    monkeypatch.setattr(L, 'arxiv_titles', lambda ids: {'1': indexed})
    row = dict(arxiv='1', title=indexed, listed_title=listed, title_basis='arxiv_oai',
               evidence=dict(pdf_sha256='a' * 64))
    L.fix_titles_from_arxiv([row], pages={'a' * 64: primary + '\n\nAuthors\n\nAbstract'})
    assert row['title'] == listed and row['title_basis'] == 'page1_verified_title'
    assert row['previous_metadata_title'] == indexed


def test_substantive_title_is_not_overwritten_without_version_evidence(monkeypatch):
    monkeypatch.setattr(L, 'arxiv_titles', lambda ids: {'1': 'A different version title'})
    row = dict(arxiv='1', title='An owned substantive citation title', evidence={})
    L.fix_titles_from_arxiv([row], pages={})
    assert row['title'] == 'An owned substantive citation title'


def test_author_only_title_can_use_index_fallback(monkeypatch):
    monkeypatch.setattr(L, 'arxiv_titles', lambda ids: {'1': 'The complete paper title'})
    row = dict(arxiv='1', title='Smith, Jane', title_basis='author_only', evidence={})
    L.fix_titles_from_arxiv([row], pages={})
    assert row['title'] == 'The complete paper title'


def test_source_version_review_replays_only_against_exact_retained_pdf():
    sha = 'b' * 64
    row = dict(pi='PI', key='paper:1', title='Latest version title',
               evidence=dict(url='https://example.edu/paper-v1.pdf', pdf_sha256=sha))
    review = dict(pi='PI', key='paper:1', primary_title='The original version title',
                  decision='correct_to_exact_represented_source_title', reviewed_by='independent', reviewed_on='2026-11-24',
                  evidence=dict(url=row['evidence']['url'], pdf_sha256=sha, quote='The original version title'))
    L.apply_paper_metadata_reviews([row], [review], {sha: 'The original version title\n\nAn Author'})
    assert row['title'] == review['primary_title']
    assert row['evidence']['title_metadata_review'] == review
    with pytest.raises(ValueError, match='Unverifiable'):
        L.apply_paper_metadata_reviews([row], [review], {sha: 'A different paper title'})


@pytest.fixture
def accuracy_tree(tmp_path, monkeypatch):
    folder = tmp_path / 'u'
    folder.mkdir()
    acc = tmp_path / 'accuracy'
    acc.mkdir()
    monkeypatch.setattr(P, 'data', lambda name, school=None, **kw: folder / name)
    monkeypatch.setattr(G, 'ACCURACY_DIR', acc)
    for name in G.ACCURACY_FILES:
        (folder / name).write_text('[]')
    return folder, acc


def _summary(folder, names):
    hashes = {n: hashlib.sha256((folder / n).read_bytes()).hexdigest() for n in names}
    return dict(files=hashes, files_now=dict(hashes), lab_precision_uniform={'p': 1.0},
                student_precision_uniform={'p': 1.0}, lab_coverage={'p': 1.0})


def test_copy_refresh_does_not_invalidate_opted_out_attribution_but_rows_do(accuracy_tree, monkeypatch):
    folder, acc = accuracy_tree
    monkeypatch.setattr(G.S, 'get', lambda key: {'accuracy': {'bind_copies': False}})
    names = G.accuracy_files('u')
    assert len(names) == 4 and 'copies.json' not in names
    (acc / 'summary-u.json').write_text(json.dumps(_summary(folder, names)))
    (folder / 'copies.json').write_text('{"summary":{"local":1}}')
    assert G.g9('u')[0] == []
    (folder / 'students.json').write_text('{"changed":[]}')
    assert any('students.json differ' in item for item in G.g9('u')[0])


def test_other_schools_keep_five_file_binding(accuracy_tree, monkeypatch):
    folder, acc = accuracy_tree
    monkeypatch.setattr(G.S, 'get', lambda key: {})
    assert G.accuracy_files('u') == G.ACCURACY_FILES
    (acc / 'summary-u.json').write_text(json.dumps(_summary(folder, G.ACCURACY_FILES)))
    (folder / 'copies.json').write_text('{"summary":{"local":1}}')
    assert any('copies.json differ' in item for item in G.g9('u')[0])


def test_binding_option_is_not_truthy_string(monkeypatch):
    monkeypatch.setattr(G.S, 'get', lambda key: {'accuracy': {'bind_copies': 'false'}})
    with pytest.raises(ValueError, match='boolean'):
        G.accuracy_files('u')
def test_outgoing_directory_uses_specific_role_section_not_combined_title():
    from labpage_students_school import outgoing_directory_role
    text = ('Outgoing Ph.D.s & Postdocs Outgoing Postdocs Rohan Kadekodi Advisor(s): Baris Kasikci '
            'Outgoing Ph.D.s Alice Roe Advisor(s): Jane Doe')
    assert outgoing_directory_role(text, 'Rohan Kadekodi') == 'postdoc'
    assert outgoing_directory_role(text, 'Alice Roe') == 'phd'
    assert outgoing_directory_role('Outgoing Ph.D.s & Postdocs Pat Smith Advisor: Jane Doe', 'Pat Smith') is None
    assert outgoing_directory_role('PhD Students Pat Smith Advisor: Jane Doe', 'Pat Smith') is None

