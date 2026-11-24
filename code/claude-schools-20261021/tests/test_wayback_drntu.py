"""wayback_drntu (D-0033, 2026-11-21): NTU papers known on DR-NTU get Wayback captures of the item's files; never a live dr.ntu.edu.sg request;
the shared web.archive.org slot; a pilot limit; a paper not asked yet gets no Result (its check stays open, never a false 'none')."""
import json
from collections import Counter

import channels as CH
from channels import wayback_drntu as WD


class Resp:
    def __init__(self, status, rows):
        self.status_code, self._rows = status, rows
        self.text = json.dumps(rows) if rows is not None else ''

    def json(self):
        return self._rows


class Ctx:
    def __init__(self, resp, dry=False):
        self.n, self.dry, self.urls, self.resp = Counter(), dry, [], resp

    def session(self):
        ctx = self

        class S:
            def get(self, url, params=None, timeout=None):
                ctx.urls.append((url, params['url']))
                return ctx.resp
        return S()

    def result(self, paper, status, urls=(), query=None, detail=None):
        return CH.Result(paper.key, paper.work_id, status, list(urls), query, detail)


def paper(i, known):
    return CH.Paper(f'k{i}', f'ntu_oa_W{i}', {}, set(known))


def setup(tmp_path, monkeypatch, limit='50'):
    import ftp_common as F
    import host_throttle as H
    monkeypatch.setattr(F.P, 'FT_RAW', tmp_path)
    slots = []
    monkeypatch.setattr(H, 'wait_slot', lambda host, delay, **k: slots.append((host, delay)) or 0.0)
    monkeypatch.setattr(H, 'record_429', lambda host, **k: slots.append(('429', host)))
    monkeypatch.setenv('WAYBACK_DRNTU_LIMIT', limit)
    return slots


HDR = ['timestamp', 'original', 'mimetype', 'statuscode']


def test_applies_only_to_ntu_papers_known_on_drntu():
    p = paper(1, {'https://hdl.handle.net/10356/147973'})
    assert WD.handles(p.known) == ['147973'] and WD.APPLIES('ntu', p) and not WD.APPLIES('mit', p)
    assert not WD.APPLIES('ntu', paper(2, {'https://arxiv.org/abs/1'}))
    assert not WD.APPLIES('ntu', paper(3, {'https://hdl.handle.net/10356/1', 'https://web.archive.org/web/1id_/https://dr.ntu.edu.sg/bitstream/10356/1/2/a.pdf'}))
    assert WD.handles({'https://dr.ntu.edu.sg/bitstream/10356/81018/1/x.pdf'}) == ['81018']


def test_latest_capture_of_each_file():
    rows = [['2021', 'https://dr.ntu.edu.sg/bitstream/10356/1/2/a.pdf', 'application/pdf', '200'],
            ['2023', 'https://dr.ntu.edu.sg/bitstream/10356/1/2/a.pdf?sequence=2', 'application/pdf', '200'],
            ['2022', 'https://dr.ntu.edu.sg/bitstream/10356/1/1/b.pdf', 'application/pdf', '200']]
    assert WD.best_captures(rows) == [dict(timestamp='2022', original='https://dr.ntu.edu.sg/bitstream/10356/1/1/b.pdf'),
                                      dict(timestamp='2023', original='https://dr.ntu.edu.sg/bitstream/10356/1/2/a.pdf?sequence=2')]


def test_lookup_only_on_the_archive_through_the_shared_slot_and_cached(tmp_path, monkeypatch):
    slots = setup(tmp_path, monkeypatch)
    ctx = Ctx(Resp(200, [HDR, ['2024', 'https://dr.ntu.edu.sg/bitstream/10356/7/2/p.pdf', 'application/pdf', '200']]))
    (r,) = list(WD.discover('ntu', [paper(1, {'https://hdl.handle.net/10356/7'})], ctx))
    assert r.status == 'found' and r.urls[0]['url'] == 'https://web.archive.org/web/2024id_/https://dr.ntu.edu.sg/bitstream/10356/7/2/p.pdf'
    assert all(u.startswith('https://web.archive.org/') for u, _ in ctx.urls) and slots == [('web.archive.org', 8)]
    ctx2 = Ctx(Resp(500, None))
    (r2,) = list(WD.discover('ntu', [paper(1, {'https://hdl.handle.net/10356/7'})], ctx2))
    assert r2.status == 'found' and ctx2.urls == []          # the cache answers; no second lookup


def test_pilot_limit_leaves_the_rest_unanswered(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, limit='2')
    ctx = Ctx(Resp(200, [HDR]))
    res = list(WD.discover('ntu', [paper(i, {f'https://hdl.handle.net/10356/{i}'}) for i in range(5)], ctx))
    assert [r.status for r in res] == ['none', 'none'] and len(ctx.urls) == 2


def test_a_429_is_shared_and_stops_the_run(tmp_path, monkeypatch):
    slots = setup(tmp_path, monkeypatch)
    ctx = Ctx(Resp(429, None))
    res = list(WD.discover('ntu', [paper(i, {f'https://hdl.handle.net/10356/{i}'}) for i in range(3)], ctx))
    assert res == [] and len(ctx.urls) == 1 and ('429', 'web.archive.org') in slots and '429' in ctx.n['stopped']
