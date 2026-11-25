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


def test_register_decisions_use_supported_reason_codes_and_eligible_urls():
    import lab_websites as LW
    for pi, d in E.DECISIONS.items():
        if d['kind'] == E.SITE:
            assert d['code'] in LW.WEBSITE_REASONS, pi
            assert not LW.selection_gaps(d['linked']), pi          # never a profile card, identity index, document or feedback form
        else:
            assert d['code'] in LW.ABSENCE_REASONS and d['seen'], pi


def test_retired_hosts_have_a_registered_reason_and_dated_robots_redirect():
    import json
    import re
    from pathlib import Path
    import lab_websites as LW
    assert E.RETIRED_CODE in LW.ABSENCE_REASONS
    reg = {r['pi']: r for r in json.loads((Path(__file__).resolve().parents[1] / 'hierarchy/epfl/reviewed/lab-websites.json').read_text())['labs']}
    for pi, host in E.RETIRED.items():
        r = reg[pi]
        assert r['reason_code'] == E.RETIRED_CODE and r['coverage'] == 'reason' and not r.get('url')
        c = next(x for x in r['checks'] if x['source'] == 'host_robots')
        assert host in c['url'] and c['status'] == 302 and c['location'].startswith('https://archiveweb.epfl.ch/') and c['at']
        assert any(x['source'] == 'school_profile_link' and host in x['url'] and re.fullmatch(r'[0-9a-f]{64}', x['source_sha256']) for x in r['checks'])


def test_every_tracked_epfl_home_decision_carries_url_hash_and_quote():
    import json
    import re
    from pathlib import Path
    ov = json.loads((Path(__file__).resolve().parents[1] / 'hierarchy/epfl/reviewed/census-overrides-school.json').read_text())
    # an official EPFL page: the people.epfl.ch profile (the 2026-11-15 pass), another *.epfl.ch page, or a raw Wayback capture of one. A PI with
    # no live profile (Kozyrakis, Piguet: archived ic.epfl.ch/professors; Henzinger: the EDIC labs table) is homed from the school's own listing
    # (owner 2026-11-25, stage-3 closeout); never a non-EPFL host
    official = re.compile(r'https://(?:web\.archive\.org/web/\d{14}id_/https?://)?(?:[a-z0-9-]+\.)*epfl\.ch(?::\d+)?/')
    for pi, d in ov.items():
        if 'home_department' in d:
            assert d['home_department_evidence'], pi
            for e in d['home_department_evidence']:
                assert official.match(e['url']) and re.fullmatch(r'[0-9a-f]{64}', e['sha256']) and e['quote'], pi
