"""Toronto: a name-only DBLP candidate is either corroborated (>= 10 works with the PI name on a school authorship) or an explicit identity hold,
so the builder's unique-name dump rule (`dblp_ids_from_dump_name`) cannot bind a held R-PAP-44 name."""
import json
from pathlib import Path

OV = Path(__file__).resolve().parents[1] / 'hierarchy/toronto/reviewed/census-overrides-school.json'
NAME_ONLY = ['Murat Erdogdu', 'Yashar Ganjali', 'Eitan Grinspun', 'Rahul G. Krishnan', 'Aleksandar Nikolov', 'Ben Rossman', 'Sam Toueg', 'Nandita Vijaykumar',
             'Nathan Wiebe', 'Henry Yuen', 'Niv Dayan', 'Xujie Si', 'Aviad Levis', 'Colin Raffel', 'Varinia Bernales', 'Thomas Ristenpart']


def test_name_only_candidates_are_corroborated_or_held():
    ov = json.loads(OV.read_text())
    for n in NAME_ONLY:
        e = ov[n]
        if e.get('no_identity'):
            assert e.get('why_no_identity'), n
            assert not e.get('dblp'), n
        else:
            corr = e['dblp_identity_review']['corroboration']
            assert any(c.get('kind') == 'dblp_works_with_school_authorship' and c['count'] >= 10 for c in corr), n
