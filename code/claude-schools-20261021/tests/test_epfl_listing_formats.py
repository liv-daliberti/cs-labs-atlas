import listing_formats as F


def test_epfl_legacy_sections_keep_rank_categories():
    html = '''
    <div id="1" class="  htmlBox"><h2>Professors</h2>
      <div class="g-span-1_4" itemscope="" itemtype="http://schema.org/Person">
        <h2 itemprop="name"><a href="https://people.epfl.ch/martin.odersky">
          <span itemprop="givenName">Martin</span> <span itemprop="familyName">Odersky</span>
        </a></h2></div>
    <div id="2" class="  htmlBox"><h2>Senior Scientists</h2>
      <div class="g-span-1_4" itemscope="" itemtype="http://schema.org/Person">
        <h2 itemprop="name"><a href="https://people.epfl.ch/martin.rajman">Martin Rajman</a></h2>
      </div>
    <div id="3" class="  htmlBox"><h2>Honorary Professors</h2>
      <div class="g-span-1_4" itemscope="" itemtype="http://schema.org/Person">
        <h2 itemprop="name"><a href="https://people.epfl.ch/emeritus">Retired Person</a></h2>
      </div>
    '''
    name, rows = F.parse(html)
    assert name == "epfl_ic_legacy"
    assert [(r["name_listed"], r["titles"]) for r in rows] == [
        ("Martin Odersky", ["Professor"]),
        ("Martin Rajman", ["Senior Scientist"]),
        ("Retired Person", ["Honorary Professor"]),
    ]


def test_epfl_contact_list_handles_multiline_tags_and_missing_title():
    html = '''
    <div class="contact-list-row" itemtype="http://schema.org/Person">
      <a href="https://people.epfl.ch/emmanuel.abbe" itemprop="name">Emmanuel Abbé</a>
      <p itemprop="jobTitle">Full Professor</p>
    </div>
    <div class="contact-list-row" itemtype="http://schema.org/Person">
      <a
        href="https://people.epfl.ch/unknown"
        itemprop="name"
        >Person Without Printed Title</a
      >
    </div>
    '''
    name, rows = F.parse(html)
    assert name == "epfl_ic_contact"
    assert [(r["name_listed"], r["titles"]) for r in rows] == [
        ("Emmanuel Abbé", ["Full Professor"]),
        ("Person Without Printed Title", []),
    ]


def test_epfl_legacy_french_rank_section_is_not_dropped():
    html = '''
    <div id="7" class="  htmlBox"><h2>Professeurs</h2>
      <div class="g-span-1_4"><h2 itemprop="name"><a href="/profile/martin">
      Martin Odersky</a></h2></div>
    <div id="8" class="  htmlBox"><h2>Maîtres d'enseignement et de recherche</h2>
      <div class="g-span-1_4"><h2 itemprop="name"><a href="/profile/teacher">
      Research Teacher</a></h2></div>
    '''
    name, rows = F.parse(html)
    assert name == "epfl_ic_legacy"
    assert [(r["name_listed"], r["titles"]) for r in rows] == [
        ("Martin Odersky", ["Professor"]),
        ("Research Teacher", ["Maître d'enseignement et de recherche"]),
    ]
