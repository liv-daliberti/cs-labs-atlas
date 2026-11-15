"""EPFL profile pass: a home is read from each position's own EPFL breadcrumb; teaching and administration positions never decide it."""
import profile_pass_people_directory as E

PAGE = '''<h1>Ann Example</h1><p id='contact'><a class="btn" href="mailto:a@epfl.ch">a@epfl.ch</a><a class="btn" href="http://lab.example.org/">x</a></p>
<p id='ext_data_links'></p>
<button class="collapse-title"><p class="title"><strong>Full Professor</strong>, <span class="font-weight-normal">Physics of Complex Systems Laboratory</span></p></button>
<p itemtype="x"><strong itemprop="name">EPFL SB IPHYS PCSL</strong></p>
<a href="https://search.epfl.ch/?filter=unit&amp;acro=EPFL">EPFL</a> › <a href="https://search.epfl.ch/?filter=unit&amp;acro=SB">SB</a> › <a href="https://search.epfl.ch/?filter=unit&amp;acro=IPHYS">IPHYS</a> › <a href="https://search.epfl.ch/?filter=unit&amp;acro=PCSL">PCSL</a>
<span class="sr-only">Website: </span><a href="https://pcsl.epfl.ch/">https://pcsl.epfl.ch/</a>
<button class="collapse-title"><p class="title"><strong>Full Professor</strong>, <span>SMA - Teaching</span></p></button>
<a href="https://search.epfl.ch/?filter=unit&amp;acro=EPFL">EPFL</a> › <a href="https://search.epfl.ch/?filter=unit&amp;acro=SB">SB</a> › <a href="https://search.epfl.ch/?filter=unit&amp;acro=SB-SMA">SB-SMA</a>'''


def test_parse_reads_positions_breadcrumbs_and_websites():
    p = E.parse(PAGE)
    assert p['h1'] == 'Ann Example'
    assert [x['crumb'] for x in p['positions']] == [['EPFL', 'SB', 'IPHYS', 'PCSL'], ['EPFL', 'SB', 'SB-SMA']]
    assert p['websites'] == ['https://pcsl.epfl.ch/']
    assert p['contact_links'] == [{'href': 'http://lab.example.org/', 'text': 'x'}]


def test_unit_name_names_an_institute_only_when_the_charter_does():
    assert E.unit_name('SB', 'IPHYS') == 'School of Basic Sciences (SB) — Institute of Physics (IPHYS)'
    assert E.unit_name('IC', 'IINFCOM') == 'School of Computer and Communication Sciences (IC)'
    assert E.unit_name('SV', 'IBI-SV') == 'School of Life Sciences (SV)'


def test_every_named_unit_is_a_charter_home_unit():
    import school_config as S
    homes = set((S.field(S.get('epfl'), 'census.home_units') or {}))
    for school in E.SCHOOLS:
        assert E.unit_name(school, 'none') in homes
    for (school, inst) in E.INSTITUTES:
        assert E.unit_name(school, inst) in homes
