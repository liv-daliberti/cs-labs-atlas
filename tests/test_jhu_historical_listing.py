import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import listing_formats as F


def test_old_jhu_cs_cards_keep_written_titles_and_only_card_people():
    html = '''
    <h2>Faculty</h2><a href="/staff">Staff Directory</a>
    <div class="highlight-box faculty-member-card">
      <a class="faculty-image"><img alt="Wrong image name"></a>
      <h3><a href="/faculty/yair-amir/">Yair Amir</a></h3>
      <h6>Professor AND CHAIR</h6><p><a href="/research/systems/">Systems Group</a></p>
    </div>
    <div class="highlight-box faculty-member-card">
      <h3><a href="/faculty/jason-eisner/">Jason Eisner</a></h3>
      <h6>Professor</h6>
    </div>
    <div class="highlight-box faculty-member-card">
      <h3><a href="/faculty/unknown-title/">Name Without Title</a></h3>
    </div>
    '''
    name, rows = F.parse(html)
    assert name == "jhu_cs_faculty_card"
    assert [(r["name_listed"], r["titles"]) for r in rows] == [
        ("Yair Amir", ["Professor AND CHAIR"]),
        ("Jason Eisner", ["Professor"]),
        ("Name Without Title", []),
    ]
    assert [r["homepage"] for r in rows] == [
        "/faculty/yair-amir/", "/faculty/jason-eisner/", "/faculty/unknown-title/"
    ]
