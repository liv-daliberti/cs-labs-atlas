"""WashU listing formats: McKelvey faculty-directory teasers (excerpt of a real 2026 capture of cse.washu.edu)."""
import listing_formats as F
from listing_rows import rank_of
from pathlib import Path
import tomllib

WU_TEASER = """<article aria-labelledby="profile16" class="faculty-directory__teaser" data-degree="facultybio" data-shortdept="cse">
<a class="faculty-directory__teaser-container" href="https://engineering.washu.edu/faculty/Roch-Guerin.html" target="blank"><div class="faculty-directory__teaser-image"><img alt="Roch Gu&eacute;rin" src="x.jpg"/></div>
<h3 class="faculty-directory__teaser-name" id="profile16">Roch Gu&eacute;rin</h3>
<p class="faculty-directory__teaser-title">Department Chair &amp; Professor</p></a></article>
<article aria-labelledby="profile17" class="faculty-directory__teaser" data-degree="facultybio" data-shortdept="cse">
<a class="faculty-directory__teaser-container" href="https://engineering.washu.edu/faculty/Michael-Hall.html"><h3 class="faculty-directory__teaser-name" id="profile17">Michael Hall</h3>
<p class="faculty-directory__teaser-title">Professor of Practice</p></a></article>"""


def test_wu_teaser_names_titles_and_profile():
    name, rows = F.parse(WU_TEASER)
    assert name == 'wu_teaser'
    assert [r['name_listed'] for r in rows] == ['Roch Guérin', 'Michael Hall']
    assert rows[0]['titles'] == ['Department Chair & Professor'] and rows[1]['titles'] == ['Professor of Practice']
    assert rows[0]['homepage'].endswith('/faculty/Roch-Guerin.html')


def test_real_2020_and_2026_department_cards_keep_all_entries_and_ranks(fixture_json):
    fixtures = fixture_json('washu-directory-eras.json')
    parsed = []
    for fixture in fixtures:
        fmt, rows = F.parse(fixture['html'])
        assert fmt == 'wu_teaser'
        assert len(rows) == fixture['html'].count('<article')
        assert all(row['homepage'] for row in rows)
        parsed.append({row['name_listed']: row for row in rows})
    old_cse, ese, bme = parsed
    assert rank_of(old_cse['Hila Ben Abraham']['titles']) == 'lecturer'
    assert old_cse['Aaron Bobick']['titles'] == ['Dean']
    charter = tomllib.loads((Path(__file__).resolve().parents[1] / 'schools/washu.toml').read_text())
    assert rank_of(ese['Hongyu An']['titles'], charter['census']['rank_words']) == 'courtesy'
    assert ese['Shantanu Chakrabartty']['titles'] == ['Vice Dean & Professor']
    assert rank_of(bme['Quentin R. R. Coquerel De Gracia']['titles']) == 'research'
