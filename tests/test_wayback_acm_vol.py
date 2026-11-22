"""wayback_acm_vol: one CDX prefix request per ACM volume, both URL forms, records in wayback_acm's cache form, shared slot, stop on 429."""
import json
from collections import Counter
from types import SimpleNamespace

import pytest
from channels import wayback_acm_vol as V


def test_volume_and_forms():
    assert V.volume('10.1145/3442381.3449999') == '10.1145/3442381.'
    assert V.volume('10.1145/3375633') == '10.1145/3375633'
    rows = [['2021', 'https://dl.acm.org/doi/pdf/10.1145/3442381.3449999', 'application/pdf', '200'],
            ['2023', 'https://dl.acm.org/doi/pdf/10.1145/3442381.3449999', 'application/pdf', '200'],
            ['2022', 'http://dl.acm.org:80/doi/pdf/10.1145/3442381.3440001?download=true', 'application/pdf', '200'],
            ['2022', 'https://dl.acm.org/doi/pdf/10.1145/3442381.3440002?casa_token=x', 'application/pdf', '200'],
            ['2022', 'https://dl.acm.org/doi/pdf/10.1145/3442381.3440003?foo=1', 'application/pdf', '200']]
    got = V.split_rows(rows)
    assert got['10.1145/3442381.3449999']['plain']['timestamp'] == '2023' and 'dl' not in got['10.1145/3442381.3449999']
    assert got['10.1145/3442381.3440001'] == {'dl': dict(timestamp='2022', original=rows[2][1])}
    assert '10.1145/3442381.3440002' not in got and '10.1145/3442381.3440003' not in got


def test_answer_follows_wayback_acm_order():
    c = dict(timestamp='1', original='o')
    assert V.answer({}, '10.1145/1') == (None, False)
    assert V.answer({V.plain('10.1145/1'): c}, '10.1145/1') == (c, True)
    assert V.answer({V.plain('10.1145/1'): None}, '10.1145/1') == (None, False)          # the twin not asked yet
    assert V.answer({V.plain('10.1145/1'): None, V.twin('10.1145/1'): c}, '10.1145/1') == (c, True)


class Ctx:
    def __init__(self, responses, dry=False):
        self.dry, self.n, self.written, self.asked = dry, Counter(), [], []
        self.responses = list(responses)

    def session(self):
        ctx = self

        def get(url, params, timeout):
            ctx.asked.append(params['url'])
            status, rows = ctx.responses.pop(0)
            body = [['timestamp', 'original', 'mimetype', 'statuscode']] + rows
            return SimpleNamespace(status_code=status, text=json.dumps(body), json=lambda: body)
        return SimpleNamespace(get=get)

    def write(self, rows, step):
        self.written += rows
        return len(rows)

    def result(self, p, status, urls=(), query=None, detail=None):
        return SimpleNamespace(work_id=p.work_id, status=status, urls=list(urls))


def paper(w, doi):
    return SimpleNamespace(work_id=w, r=dict(doi=doi), known=set())


@pytest.fixture
def env(tmp_path, monkeypatch):
    import ftp_common as F
    import host_throttle as H
    monkeypatch.setattr(F.P, 'FT_RAW', tmp_path)
    monkeypatch.setattr(V, 'cache_files', lambda: [tmp_path / 'wayback_lookups.jsonl'])
    waits, r429 = [], []
    monkeypatch.setattr(H, 'wait_slot', lambda host, d: waits.append(host))
    monkeypatch.setattr(H, 'record_429', lambda host: r429.append(host))
    return SimpleNamespace(log=tmp_path / 'wayback_lookups.jsonl', waits=waits, r429=r429)


def pdf(d, q=''):
    return ['2024', f'https://dl.acm.org/doi/pdf/{d}{q}', 'application/pdf', '200']


def test_one_request_per_volume_records_both_forms(env):
    ps = [paper('a', '10.1145/3442381.1'), paper('b', '10.1145/3442381.2'), paper('c', '10.1145/3442381.3'), paper('d', '10.1145/777')]
    ctx = Ctx([(200, [pdf('10.1145/3442381.1'), pdf('10.1145/3442381.2', '?download=true')]), (200, [])])
    res = {r.work_id: r for r in V.discover('x', ps, ctx)}
    assert ctx.asked == ['dl.acm.org/doi/pdf/10.1145/3442381.', 'dl.acm.org/doi/pdf/10.1145/777'] and env.waits == ['web.archive.org'] * 2
    assert {w: r.status for w, r in res.items()} == dict(a='found', b='found', c='none', d='none')
    assert all(u.get('written_by_step') for r in res.values() for u in r.urls)
    assert sorted(x['work_id'] for x in ctx.written) == ['a', 'b'] and {x['source'] for x in ctx.written} == {'wayback_acm_dl'}
    recs = [json.loads(x) for x in env.log.read_text().splitlines()]
    assert len(recs) == 8 and all(r['kind'] == 'acm' and r['status'] == 200 for r in recs)
    # a rerun asks nothing and writes nothing twice (the papers now hold their Wayback URL, so APPLIES drops them; here: the cache answers)
    ctx2 = Ctx([])
    assert len(list(V.discover('x', ps, ctx2))) == 4 and ctx2.asked == []


def test_truncated_volume_is_asked_per_doi(env, monkeypatch):
    monkeypatch.setattr(V, 'LIMIT', 2)
    ps = [paper('a', '10.1145/5.1'), paper('b', '10.1145/5.2')]
    ctx = Ctx([(200, [pdf('10.1145/5.9')] * 2), (200, [pdf('10.1145/5.1')]), (200, [])])
    res = {r.work_id: r.status for r in V.discover('x', ps, ctx)}
    assert ctx.asked == ['dl.acm.org/doi/pdf/10.1145/5.', 'dl.acm.org/doi/pdf/10.1145/5.1', 'dl.acm.org/doi/pdf/10.1145/5.2']
    assert res == dict(a='found', b='none') and ctx.n['wayback_acm_vol_truncated'] == 1


def test_429_records_and_stops_leaving_the_rest_open(env):
    ps = [paper('a', '10.1145/1.1'), paper('b', '10.1145/1.2'), paper('c', '10.1145/2.1')]
    ctx = Ctx([(429, [])])
    res = list(V.discover('x', ps, ctx))
    assert res == [] and env.r429 == ['web.archive.org'] and '429' in ctx.n['stopped'] and len(ctx.asked) == 1
    assert not env.log.exists() or env.log.read_text() == ''


def test_cached_hit_without_a_candidate_is_written_and_dry_asks_nothing(env):
    c = dict(timestamp='2020', original='https://dl.acm.org/doi/pdf/10.1145/9.9')
    env.log.write_text(json.dumps(dict(kind='acm', url='dl.acm.org/doi/pdf/10.1145/9.9', status=200, capture=c)) + '\n')
    ctx = Ctx([], dry=True)
    res = list(V.discover('x', [paper('a', '10.1145/9.9'), paper('b', '10.1145/9.8')], ctx))
    assert [(r.work_id, r.status) for r in res] == [('a', 'found')] and ctx.asked == [] and ctx.n['wayback_acm_vol_cached_hits'] == 1
    ctx = Ctx([(200, [])])
    list(V.discover('x', [paper('a', '10.1145/9.9')], ctx))
    assert [x['url'] for x in ctx.written] == ['https://web.archive.org/web/2020id_/https://dl.acm.org/doi/pdf/10.1145/9.9'] and ctx.asked == []
