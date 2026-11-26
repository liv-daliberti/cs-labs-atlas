"""Non-PhD research advising can establish a PI, with separately checked sources."""
import pytest

from test_cs_related_school import research_review


def student():
    return dict(name='Casey Student', role='undergraduate', relationship='research_supervision',
                quote='Undergraduate research thesis: Casey Student.',
                research_context_quote='Undergraduate research thesis')


def test_teaching_pi_with_named_undergraduate_research_supervision(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, rank='teaching', kind='advises_students',
        period_text='Undergraduate research thesis: Casey Student.', research_students=[student()])
    assert decision['decision'] == 'accepted'
    assert additions[0]['rank'] == 'teaching'
    assert additions[0]['pi_basis']['kind'] == 'advises_students'
    assert additions[0]['is_pi']


@pytest.mark.parametrize('bad', [
    {},
    dict(name='Someone Else', role='undergraduate', relationship='research_supervision',
         quote='Undergraduate research thesis: Casey Student.', research_context_quote='Undergraduate research thesis'),
    dict(name='Casey Student', role='staff', relationship='research_supervision',
         quote='Undergraduate research thesis: Casey Student.', research_context_quote='Undergraduate research thesis'),
    dict(name='Casey Student', role='student', relationship='coursework',
         quote='Undergraduate research thesis: Casey Student.', research_context_quote='Undergraduate research thesis'),
    dict(name='Casey Student', role='student', relationship='research_supervision',
         quote='Uncaptured research thesis: Casey Student.', research_context_quote='Undergraduate research thesis'),
    dict(name='Casey Student', role='student', relationship='research_supervision',
         quote='Undergraduate research thesis: Casey Student.', research_context_quote='Uncaptured research thesis'),
])
def test_incomplete_or_unattested_student_claim_cannot_supply_pi_basis(monkeypatch, tmp_path, bad):
    with pytest.raises(SystemExit):
        research_review(monkeypatch, tmp_path, rank='teaching', kind='advises_students',
            period_text='Undergraduate research thesis: Casey Student.', research_students=[bad])


def test_course_reading_does_not_supply_research_student_basis(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match='research/thesis context'):
        research_review(monkeypatch, tmp_path, rank='teaching', kind='advises_students',
            period_text='Course reading: Casey Student.', research_students=[dict(
                name='Casey Student', role='student', relationship='research_supervision',
                quote='Course reading: Casey Student.', research_context_quote='Course reading')])


def test_research_advisees_do_not_replace_an_academic_appointment(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, appointment=False, rank='teaching',
        kind='advises_students', period_text='Undergraduate research thesis: Casey Student.',
        research_students=[student()])
    assert decision['decision'] != 'accepted'
    assert additions == []


def test_new_pi_basis_does_not_wire_phd_students(tmp_path, layout):
    import json
    import test_build_rules as fixture
    fixture.write_school(tmp_path)
    path = fixture.put(tmp_path, 'census-overrides.json', None)
    overrides = json.loads(path.read_text())
    overrides[fixture.SCHOOL]['Ada Lovelace']['pi_basis'] = dict(
        kind='advises_students', url='https://example.edu/source', sha256='a' * 64,
        quote='Casey Student May 2020 Ph.D. Thesis')
    path.write_text(json.dumps(overrides))
    ctx = fixture.run_stages(tmp_path)
    assert all(s['name'] != 'Casey Student' for s in ctx.stu['Ada Lovelace'].values())
