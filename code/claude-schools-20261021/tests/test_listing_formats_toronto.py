import pytest
from listing_formats import parse
from listing_rows import rank_of


def table(section, body):
    return f'<h2 id="{section}">Faculty</h2><table class="blueTable"><tr><th>Name</th><th>Position</th></tr>{body}</table>'


def test_toronto_research_keeps_only_name_and_literal_rank():
    html = table('researchstream', '<tr><td><a href="/smith">Alex Smith</a><br>Associate Professor</td><td>[email removed]<br>5551234</td><td>Research: AI</td></tr><tr><td>Robin Doe<br>Incoming Assistant Professor</td><td>contact</td><td>interests</td></tr>')
    _, rows = parse(html, 'toronto_research')
    assert len(rows) == 2
    assert rows[0] == dict(name_listed='Alex Smith', titles=['Associate Professor'], homepage='/smith', division=None)
    assert rows[1]['homepage'] is None
    assert rank_of(rows[1]['titles']) == 'other'
    assert 'email' not in str(rows) and 'interests' not in str(rows)
    assert parse(html, 'toronto_emeriti')[1] == []


def test_toronto_split_role_preserves_teaching_phrase():
    html = table('teachingstream', '<tr><td>Alex Smith</td><td>Assistant Professor,<br> Teaching Stream</td><td>email</td><td>phone</td><td>office</td></tr>')
    assert parse(html, 'toronto_teaching')[1][0]['titles'] == ['Assistant Professor, Teaching Stream']


def test_toronto_cross_handles_missing_tr_and_keeps_home_unit():
    html = table('crossappointed', '<td><a href=" /smith ">Alex Smith</a></td><td>Professor<br>Psychology</td><td>Research</td></tr>')
    assert parse(html, 'toronto_cross')[1] == [dict(name_listed='Alex Smith', titles=['Professor Psychology'], homepage='/smith', division=None)]


def test_toronto_incomplete_cells_fail_closed():
    with pytest.raises(ValueError, match='incomplete directory row'):
        parse(table('adjunct', '<tr><td>Alex Smith</td><td>Adjunct Professor</td></tr>'), 'toronto_adjunct')


def test_toronto_missing_contact_closing_tag_does_not_merge_people():
    html = table('researchstream', '<tr><td>Alex Smith<br>Assistant Professor</td><td>contact<td>Research</td></tr><tr><td>Robin Doe<br>Professor</td><td>contact</td><td>Research</td></tr>')
    rows = parse(html, 'toronto_research')[1]
    assert [r['name_listed'] for r in rows] == ['Alex Smith', 'Robin Doe']
    assert rows[0]['titles'] == ['Assistant Professor']
