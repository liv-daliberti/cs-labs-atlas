"""Johns Hopkins listing formats (excerpts of real captures)."""
import listing_formats as F

WSE = """<ul class="entity_list_items" id="item_list" aria-label="Faculty"><li class="entity_list_item"><div class="entity" itemscope itemtype="https://schema.org/Person"><div class="entity_header"><div class="entity_info">
<h2 class="entity_name" itemprop="name"><a class="entity_name_link" href="https://www.cs.jhu.edu/faculty/yair-amir/">Yair Amir</a></h2>
<div class="entity_title">Professor Emeritus</div><div class="entity_department"><a href="https://www.cs.jhu.edu/"><span>Department of Computer Science</span></a></div></div></div></div></li>
<li class="entity_list_item"><div class="entity"><h2 class="entity_name" itemprop="name"><a class="entity_name_link" href="https://www.cs.jhu.edu/faculty/jason-eisner/">Jason Eisner</a></h2>
<div class="entity_title">Bloomberg Distinguished Professor</div></div></li></ul>"""


def test_wse_entity_reads_name_title_and_homepage():
    name, rows = F.parse(WSE)
    assert name == 'wse_entity' and [r['name_listed'] for r in rows] == ['Yair Amir', 'Jason Eisner']
    assert rows[0]['titles'] == ['Professor Emeritus'] and rows[1]['titles'] == ['Bloomberg Distinguished Professor']
    assert rows[0]['homepage'].endswith('/faculty/yair-amir/')
