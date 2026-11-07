"""Targeted discovery must preserve advisor/committee and member/affiliate distinctions."""
import datetime as dt
import json

from student_source_discovery import defense_rows, gatsby_rows, index_links


def test_defense_explicit_advisor_not_other_committee_members():
    html = '<h1>Ph.D. Dissertation Defense - Mine Kerpicci</h1><p>Dr. Milos Prvulovic, CoC, Chair, Advisor<br>Dr. David Anderson, ECE</p>'
    pis = [{'pi': 'Milos Prvulovic'}, {'pi': 'David Anderson'}]
    rows, reason = defense_rows(html, 'https://ece.gatech.edu/event/2026/05/20/defense', 'a' * 64, pis, dt.date(2026, 11, 7))
    assert reason == 'explicit_adviser'
    assert [(r['pi'], r['name'], r['role']) for r in rows] == [('Milos Prvulovic', 'Mine Kerpicci', 'phd')]
    assert rows[0]['host_quote'] == 'Dr. Milos Prvulovic, CoC, Chair, Advisor'


def test_defense_chair_without_adviser_label_and_future_date_are_held():
    html = '<h1>Ph.D. Dissertation Defense - Some Student</h1><p>Dr. David Anderson, ECE, Chair</p>'
    args = (html, 'https://ece.gatech.edu/event/2026/05/20/defense', 'a' * 64, [{'pi': 'David Anderson'}])
    assert defense_rows(*args, dt.date(2026, 11, 7)) == ([], 'no_unique_explicit_adviser')
    assert defense_rows(*args, dt.date(2026, 1, 1)) == ([], 'future_announcement')


def test_coadvisers_on_separate_lines_and_ambiguous_names():
    html = '<h1>Dissertation Defense: Some Student</h1><p>Dr. Jane Smith, ECE, Co-advisor<br>Dr. John Jones, ECE, Co-advisor</p>'
    pis = [{'pi': 'Jane Smith'}, {'pi': 'John Jones'}]
    rows, _ = defense_rows(html, 'https://ece.gatech.edu/event/2025/01/01/defense', 'a' * 64, pis, dt.date(2026, 1, 1))
    assert {r['pi'] for r in rows} == {'Jane Smith', 'John Jones'}
    pis.append({'pi': 'Another PI', 'names': ['John Jones']})
    rows, _ = defense_rows(html, 'https://ece.gatech.edu/event/2025/01/01/defense', 'a' * 64, pis, dt.date(2026, 1, 1))
    assert {r['pi'] for r in rows} == {'Jane Smith'}


def test_index_only_same_host_defenses_and_exact_index_pagination():
    html = '''<a href="?page=1">Next</a><a href="/event/2025/01/01/phd-dissertation-defense-a">Defense</a>
    <a href="https://evil.example/event/2025/01/01/defense">Other host</a><a href="/search/?page=1">Search</a>
    <a href="/event/2025/01/01/phd-proposal-a">Proposal</a><a href="?page=1&sort=x">Extra query</a>'''
    assert index_links(html, 'https://ece.gatech.edu/taxonomy/term/16445') == [
        {'url': 'https://ece.gatech.edu/taxonomy/term/16445?page=1', 'kind': 'defense_index'},
        {'url': 'https://ece.gatech.edu/event/2025/01/01/phd-dissertation-defense-a', 'kind': 'defense'},
    ]


def test_tabbed_roster_retains_student_category_without_inventing_adviser():
    bio = {'nodeType': 'document', 'content': [{'nodeType': 'paragraph', 'content': [{'nodeType': 'text', 'value': 'A visiting student at another university.'}]}]}
    contents = [dict(__typename='ContentfulPersonItem', name='Some Student', personCategory=['Students'], biography={'raw': json.dumps(bio)}, email='do-not-export@example.org'),
                dict(__typename='ContentfulPersonItem', name='Faculty Person', personCategory=['Affiliated Faculty'])]
    data = {'result': {'data': {'contentfulKLabPage': {'kLabContents': contents}}}}
    rows = gatsby_rows(json.dumps(data), 'https://lab.example/page-data/team/page-data.json', 'b' * 64)
    assert len(rows) == 1 and rows[0]['name'] == 'Some Student'
    assert rows[0]['biography'] == 'A visiting student at another university.'
    assert 'pi' not in rows[0] and 'email' not in rows[0] and 'role' not in rows[0]
