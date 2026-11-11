"""ZJU charter: the college hosts whose robots are read at their http origin are listed (owner authorization 2026-11-11), never as a live collector host."""
import school_config as S

HOSTS = ['www.isee.zju.edu.cn', 'www.math.zju.edu.cn', 'www.cbeis.zju.edu.cn', 'zucc.zju.edu.cn', 'www.mtc.zju.edu.cn', 'www.psych.zju.edu.cn', 'www.spa.zju.edu.cn']


def test_college_hosts_carry_the_http_origin_authorization_and_stay_use_none():
    by = {h['host']: h for h in S.get('zju').get('hosts') or []}
    for h in HOSTS:
        assert h in by, h
        assert by[h]['use'] == 'none'
        assert 'Owner authorization 2026-11-11' in by[h]['note'] and 'HTTP-origin' in by[h]['note']
