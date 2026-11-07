"""PhD-defense announcements as adviser evidence (tools/defense_students.py, R-STU-23 proposed): the candidate comes from the listing title, the adviser
from a cue on the PI's own entry; committee members, chairs without the cue and namesakes are not advisers."""
import defense_students as D


def names(text):
    return [n for n, _, _ in D.advisor_mentions(text)]


def test_candidate_name_from_listing_titles():
    assert D.candidate_name('PhD Defense by Wenyu Tang') == 'Wenyu Tang'
    assert D.candidate_name('Ph.D. Dissertation Defense - Nahid Shazon') == 'Nahid Shazon'
    assert D.candidate_name('PhD Defense by VISWA SRI RUPA ANNE') == 'Viswa Sri Rupa Anne'
    assert D.candidate_name('Ph.D. Proposal Oral Exam - Yuheng He') == 'Yuheng He'
    assert D.candidate_name('Spring Seminar') is None


def test_adviser_cue_forms():
    assert names('Committee: Dr. Azad Naeemi, ECE, Chair, Advisor Dr. Jeff Davis, ECE Dr. Asif Khan, ECE') == ['Azad Naeemi']
    assert names('Committee Dr. Justin Romberg (Advisor), School of Electrical and Computer Engineering Dr. Mark Davenport, School of ECE') == ['Justin Romberg']
    assert names('Committee: John Etnyre (advisor), Jennifer Hom, Johnathan Zung') == ['John Etnyre']
    assert names('Advisor: Dr. Ling Liu Committee: Dr. A Bee, Dr. C Dee') == ['Ling Liu']
    assert names('Advisors: Dr. Alan Smith and Dr. Mary Jones. Committee') == ['Alan Smith', 'Mary Jones']


def test_chair_without_cue_and_committee_members_are_not_advisers():
    assert names('Committee: Dr. Xiaoli Ma, ECE, Chair Dr. Yao Xie, ISYE, Co-Advisor Dr. Z Qiu, ECE') == ['Yao Xie']
    assert names('Committee Members: Dr. Ann Lee, Dr. Bo Chen, Dr. Cy Dunn') == []


def test_defense_year_prefers_a_full_date():
    assert D.defense_year('2022-12-20', 'Date: January 9, 2023 Time: 2 PM') == 2023
    assert D.defense_year('2022-12-20', 'Date: Friday, January 9th Time: 2 PM') == 2022


def test_source_quotes_bind_candidate_and_complete_adviser_cue_to_event_page():
    text = 'Dissertation Defense: ADA STUDENT Committee Dr. Ann Lee, ECE, Chair, Advisor Dr. Bo Chen, Reader'
    lo = text.index('Ann Lee'); hi = lo + len('Ann Lee')
    candidate, adviser = D.source_quotes('Ada Student', text, lo, hi)
    assert candidate == 'ADA STUDENT' and candidate in text
    assert adviser in text and 'Ann Lee, ECE, Chair, Advisor' in adviser
    assert D.source_quotes('Different Student', text, lo, hi) is None
    assert D.source_quotes('Ada Student', 'Nada Student. Advisor Ann Lee', 22, 29) is None


def test_legacy_defense_extracts_are_not_grouped_researched_inputs(tmp_path, monkeypatch):
    import collections
    import json
    from types import SimpleNamespace
    import pihier.students as S
    (tmp_path / 'defense-evidence.json').write_text(json.dumps([{'student': 'Legacy Student', 'host': 'Ann Lee'}]))
    (tmp_path / 'defense-adviser-evidence.json').write_text(json.dumps([
        {'pi': 'Ann Lee', 'students': [{'name': 'Ada Student', 'role': 'phd', 'years': [2024, 2024],
         'quote': 'Ada Student', 'host_quote': 'Advisor Ann Lee', 'sha256': 'abc', 'url': 'https://example.edu/defense'}]}]))
    monkeypatch.setattr(S.P, 'data', lambda name, *a, **kw: tmp_path / name)
    monkeypatch.setattr(S, 'accepted_additions', lambda *a: [])
    ctx = SimpleNamespace(here=tmp_path, school='example', pis=[{'pi': 'Ann Lee'}], ge={}, n=collections.Counter())
    students = collections.defaultdict(dict)
    S.researched(ctx, students, {})
    row = next(iter(students['Ann Lee'].values()))
    assert row['name'] == 'Ada Student'
    assert [source['quote'] for source in row['relations'][0]['sources']] == ['Ada Student', 'Advisor Ann Lee']
