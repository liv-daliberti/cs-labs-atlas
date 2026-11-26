"""ETH Board release entries carry their institution; an EPFL appointee is not ETH evidence (stage-3 audit: Ola Svensson)."""

import board_entries as B

SVENSSON = ("Promotions at EPFL Professor Ola Svensson (*1981), currently Associate Professor at EPFL, as Full Professor of Computer Science in the "
            "School of Computer and Communication Sciences. His research area is the theory of computation.")


def test_svensson_is_epfl_even_without_a_trustworthy_heading():
    e = B.parse_release("New appointments at ETH Zurich Professor Dagmar Iber (*1975), currently Associate Professor at ETH Zurich, as Full Professor of "
                        "Computational Biology in the Department of Biosystems Science and Engineering. Text. " + SVENSSON)
    by = {x['name']: x for x in e}
    assert by['Ola Svensson']['institution'] == 'EPFL'
    assert by['Dagmar Iber']['institution'] == 'ETH Zurich'


def test_school_cue_beats_a_stale_eth_heading():
    e = B.parse_release("New appointments at ETH Zurich " + SVENSSON.replace('Promotions at EPFL ', ''))
    assert e[0]['institution'] == 'EPFL' and e[0]['method'] == 'rank_school'


def test_rank_suffix_and_first_epfl_heading():
    assert B.institution('Adjunct Professor at EPFL', 'New appointments at ETH Zurich')[0] == 'EPFL'
    g = B.parse_release("Dr C D (*1980), currently Senior Scientist, as Full Professor of Physics. Appointments at EPFL Dr E F (*1985), currently Postdoc, as Associate Professor of Physics.")
    assert [x['institution'] for x in g] == ['ETH Zurich', 'EPFL']
