import faculty_periods as FP
import periods_school as PS


def test_fetch_live_only_never_asks_wayback(monkeypatch):
    class Con:
        def execute(self, *a, **k):
            class R:
                def fetchone(self_):
                    return None
            return R()
    calls = {'cdx': 0, 'live': 0}
    monkeypatch.setattr(PS.S, 'get', lambda key: {})
    monkeypatch.setattr(PS.S, 'host_use', lambda key, host: 'live' if host == 'a.example.org' else 'wayback-only')
    monkeypatch.setattr(PS.W, 'con', lambda key: Con())
    monkeypatch.setattr(PS.W, '_blocked', set(), raising=False)
    monkeypatch.setattr(PS.W, 'live', lambda c, u: calls.__setitem__('live', calls['live'] + 1) or (200, 'sha', []))
    monkeypatch.setattr(PS.W, 'cdx_rows', lambda *a, **k: calls.__setitem__('cdx', calls['cdx'] + 1) or [])
    monkeypatch.setattr(PS, 'targets', lambda key: [dict(name='A B', urls=['https://a.example.org/x', 'https://old.example.org/y'], first=2016)])
    PS.fetch('k', live_only=True, everyone=True)
    assert calls == {'cdx': 0, 'live': 1}
    PS.fetch('k', live_only=False, everyone=True)
    assert calls['cdx'] == 1


def test_korean_and_english_kaist_appointment_phrasing():
    FP.SCHOOL['kaist'] = r'(?i:\bKAIST\b|한국과학기술원|카이스트)'
    cases = {
        '2012년 3월 KAIST 조교수로 부임하여 2018년 부교수로 승진': '2012',
        '2009년 한국과학기술원 부임 이후 소프트웨어를 연구': '2009',
        '2015~현재 KAIST 부교수': '2015',
        '2010-2020 카이스트 정교수 재직': '2010',
        'He joined KAIST in 2014 as an assistant professor of computer science.': '2014',
        'Associate Professor, KAIST, since 2016': '2016',
    }
    for text, year in cases.items():
        got = FP.candidates(text, 'kaist')
        assert got and got[0][0] == year, text
    assert FP.candidates('2012년 서울대학교 조교수로 부임', 'kaist') == []
    assert PS.MOVED.search('2021년 KAIST를 떠나 서울대학교로 이직')
    assert PS.MOVED.search('before moving to KAIST')
