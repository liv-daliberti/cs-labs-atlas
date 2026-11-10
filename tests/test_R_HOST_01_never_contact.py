"""R-HOST-01: the never-contact host rule is documented in the stage 0 text and the rule list (the behavior test lives with tools/school_hosts.py)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_R_HOST_01_never_contact_is_documented():
    guide = (ROOT / 'docs/ADDING-A-SCHOOL.md').read_text()
    rules = (ROOT / 'docs/RULES.md').read_text()
    assert 'NEVER_CONTACT' in guide and 'not_fetched' in guide
    for host in ('dblp.org', 'orcid.org', 'web.archive.org'):
        assert host in rules.split('### R-HOST-01')[1]
