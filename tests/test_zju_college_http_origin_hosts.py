"""ZJU charter: the college hosts whose robots are read at their http origin are listed (owner authorization 2026-11-11), never as a live collector host.
The five PI own-site hosts (+ bohanzhuang.github.io) are use=live and the CAD&CG HTTP grant covers the cad hosts (owner ruling 2026-11-11 (A))."""
import school_config as S

HOSTS = ['www.isee.zju.edu.cn', 'www.math.zju.edu.cn', 'www.cbeis.zju.edu.cn', 'zucc.zju.edu.cn', 'www.mtc.zju.edu.cn', 'www.psych.zju.edu.cn', 'www.spa.zju.edu.cn']
OWN_SITES = ['cshen.github.io', 'svbrdf.github.io', 'xchen-cs.github.io', 'zjuidg.org', 'www.zyouyi.com', 'bohanzhuang.github.io']
CAD_HOSTS = ['www.cad.zju.edu.cn', 'cad.zju.edu.cn']


def _by():
    return {h['host']: h for h in S.get('zju').get('hosts') or []}


def test_college_hosts_carry_the_http_origin_authorization_and_stay_use_none():
    by = _by()
    for h in HOSTS:
        assert h in by, h
        assert by[h]['use'] == 'none'
        assert 'Owner authorization 2026-11-11' in by[h]['note'] and 'HTTP-origin' in by[h]['note']


def test_pi_own_site_hosts_are_live_by_owner_ruling():
    by = _by()
    for h in OWN_SITES:
        assert by[h]['use'] == 'live', h
        assert 'Owner ruling 2026-11-11' in by[h]['note'] and 'robots' in by[h]['note']
        assert S.host_use('zju', h) == 'live'


def test_cad_grant_is_extended_over_the_cad_hosts_http_origin_only():
    by = _by()
    for h in CAD_HOSTS:
        assert by[h]['use'] == 'live', h
        n = by[h]['note']
        assert 'Owner ruling 2026-11-11 (A)' in n and 'EXTENDED' in n and 'HTTP origin only' in n
        assert S.host_use('zju', h) == 'live' and 'no HTTPS' in n


def test_person_zju_stays_off_limits():
    assert _by()['person.zju.edu.cn']['use'] == 'none'
