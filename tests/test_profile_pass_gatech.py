"""Georgia Tech profile pass: only real profile pages count, and every decision uses a supported reason and an eligible URL."""
import profile_pass_gatech as G


def test_parse_page_reads_heading_and_links_and_names_the_pi():
    raw = '<title>Ann Example | X</title><h1>Ann Example</h1><a href="http://lab.example.org/">lab</a><footer><a href="http://f.example.org/">f</a></footer>'
    head, names_pi, links = G.parse_page(raw, 'https://ic.gatech.edu/people/ann-example', 'Ann Example')
    assert head == 'Ann Example' and names_pi
    assert [l['href'] for l in links] == ['http://lab.example.org/']


def test_a_page_for_someone_else_does_not_name_the_pi():
    _, names_pi, _ = G.parse_page('<h1>Unknown person requested!</h1>', 'https://lmc.gatech.edu/x', 'Nassim Parvin')
    assert not names_pi


def test_register_decisions_use_supported_reason_codes_and_eligible_urls():
    import lab_websites as LW
    for pi, d in G.DECISIONS.items():
        assert d['code'] in LW.ABSENCE_REASONS or d['code'] in LW.WEBSITE_REASONS, pi
        if d['kind'] == G.SITE:
            assert not LW.selection_gaps(d['linked']), pi
            assert d['code'] in LW.WEBSITE_REASONS, pi
        else:
            assert d['code'] in LW.ABSENCE_REASONS, pi
