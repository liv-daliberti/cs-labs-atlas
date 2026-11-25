"""The state 'linked by an official profile, not fetched (robots)': the row carries the linked URL, the dated profile and link checks and the
robots record that refuses the host; it is never produced when the host allows fetching, and the gate fails it without the profile evidence."""
import json

import lab_websites as W

PROFILE = 'https://cse.hkust.edu.hk/admin/people/faculty/profile/x'
SITE = 'https://x.home.example/'
ROBOTS = dict(host='x.home.example', robots_url='https://x.home.example/robots.txt', checked_at='2026-11-25T07:00:00+00:00', status=200,
              sha256='c' * 64, allowed=False, verdict='refused', agent='ClaudeBot', rule='Disallow: /')
PROF = dict(pi='A', profile_url=PROFILE, fetched_at='2026-11-25T06:00:00+00:00', status='ok', sha256='a' * 64,
            link=dict(url=SITE, anchor='Personal Homepage'), link_robots=ROBOTS)


def _build(monkeypatch, tmp_path, prof):
    f = tmp_path / 'profile-links.json'
    f.write_text(json.dumps({'rows': [prof]}))
    monkeypatch.setattr(W.P, 'data', lambda name, school=None, **k: f)
    monkeypatch.setattr(W, 'stored_captures', lambda school, urls: {})
    return W.apply_profile_links('x', {'labs': [{'pi': 'A', 'coverage': 'pending', 'checks': []}]})['labs'][0]


def test_refused_host_gives_the_state_and_it_passes_the_gate(monkeypatch, tmp_path):
    row = _build(monkeypatch, tmp_path, PROF)
    assert row['coverage'] == 'linked_not_fetched' and row['reason_code'] == W.LINKED_NOT_FETCHED and row['url'] == SITE and 'sha256' not in row
    assert W.gate({'school': None, 'labs': [row]}, ['A']) == []


def test_allowing_host_is_never_this_state(monkeypatch, tmp_path):
    row = _build(monkeypatch, tmp_path, dict(PROF, link_robots=dict(ROBOTS, allowed=True, rule=None)))
    assert row['coverage'] == 'pending' and row['evidence_gaps'] == ['linked_site_not_captured']
    row = _build(monkeypatch, tmp_path, {k: v for k, v in PROF.items() if k != 'link_robots'})
    assert row['coverage'] == 'pending'


def test_gate_fails_without_the_official_profile_evidence(monkeypatch, tmp_path):
    row = _build(monkeypatch, tmp_path, PROF)
    no_link = dict(row, checks=[c for c in row['checks'] if c['source'] != 'school_profile_link'])
    no_profile_sha = dict(row, checks=[dict(c, sha256=None) if c['source'] == 'school_profile' else c for c in row['checks']])
    no_robots = dict(row, robots=dict(ROBOTS, allowed=True))
    for bad in (no_link, no_profile_sha, no_robots, dict(row, robots={}), dict(row, url=None)):
        assert W.gate({'school': None, 'labs': [bad]}, ['A']), bad


def test_counts_treat_the_state_as_documented(monkeypatch, tmp_path):
    row = _build(monkeypatch, tmp_path, PROF)
    c = W.counts({'labs': [row]})
    assert c['linked_not_fetched'] == 1 and c['neither'] == 0 and c['documented']


def test_refused_and_no_usable_permission_stay_distinct(monkeypatch, tmp_path):
    refused = _build(monkeypatch, tmp_path, PROF)
    unusable = dict(ROBOTS, verdict='no_usable_permission', agent=None, rule='no usable robots.txt (SSL certificate verify failed)', status=None)
    row = _build(monkeypatch, tmp_path, dict(PROF, link_robots=unusable))
    assert 'refuses it' in refused['reason'] and 'disallow' not in row['reason'].lower() and 'no usable permission' in row['reason']
    assert row['robots']['verdict'] == 'no_usable_permission' and refused['robots']['verdict'] == 'refused'
    assert W.gate({'school': None, 'labs': [row]}, ['A']) == []
    # an unreadable robots.txt must not be labelled a Disallow, nor a Disallow rule an unusable file
    assert W.gate({'school': None, 'labs': [dict(row, robots=dict(unusable, verdict='refused'))]}, ['A'])
    assert W.gate({'school': None, 'labs': [dict(refused, robots=dict(ROBOTS, verdict='no_usable_permission'))]}, ['A'])
