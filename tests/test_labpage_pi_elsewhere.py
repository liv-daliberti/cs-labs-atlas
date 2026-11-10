"""LP-STU-01 defect (Toronto lab-page round 1, 2026-11-10): a project-team page that describes the PI as a researcher at another institution
must not admit its members as the PI's students."""
import labpage_audit as L

TEAM = ('Team Hossein Shafagh Hossein Shafagh is a research scientist at the Distributed Systems Group at ETH Zurich, Switzerland. '
        'Anwar Hithnawi Anwar Hithnawi is a research scientist at the NetSys Lab at UC Berkeley, USA. '
        'Lukas Burkhalter Lukas Burkhalter is a Ph.D. candidate at ETH Zurich.')


def test_pi_described_at_another_institution_is_rejected():
    r = L.pi_elsewhere_reason(TEAM, 'Anwar Hithnawi', 'toronto')
    assert r and r[0] == 'site_at_other_institution'


def test_pi_described_at_the_school_is_kept():
    t = 'Meel Lab. Kuldeep Meel is an Assistant Professor at the University of Toronto, Canada. PhD students: Ashwin Karthikeyan.'
    assert L.pi_elsewhere_reason(t, 'Kuldeep Meel', 'toronto') is None


def test_page_not_describing_the_pi_is_kept():
    assert L.pi_elsewhere_reason('People: Ashwin Karthikeyan PhD', 'Kuldeep Meel', 'toronto') is None
