"""WashU profile pass: the two decided rows of the tracked website register pass the website gate and carry their profile evidence."""
import json
from pathlib import Path

import lab_websites as LW
import washu_profile_pass as WP

REG = Path(__file__).resolve().parent.parent / 'hierarchy' / 'washu' / 'reviewed' / 'lab-websites.json'


def rows():
    return {r['pi']: r for r in json.loads(REG.read_text())['labs']}


def test_decided_rows_pass_the_website_gate():
    doc = json.loads(REG.read_text())
    assert LW.gate(doc, list(WP.DECISIONS)) == []


def test_absence_row_cites_the_fetched_profile_and_chain_row_the_two_hop_links():
    r = rows()
    h = r['Jiaxin Huang']
    assert h['reason_code'] == 'profile_only_no_homepage' and 'url' not in h
    assert any(c['source'] == 'school_profile' and c['url'].endswith('Jiaxin-Huang.html') for c in h['checks'])
    z = r['Ning Zhang']
    chain = z['official_link_evidence'][0]['provenance_chain']
    assert [c['url'] for c in chain] == ['https://n1ngz.github.io/', 'https://cybersecurity.seas.wustl.edu']
    assert z['url'] == chain[-1]['url']
