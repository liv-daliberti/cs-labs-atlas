"""V4a (owner 2026-11-17): sharded, per-PI stage-3 discovery; Wayback history moved to the students track; first source that proves a website stops the search."""
import json
import re
from types import SimpleNamespace

import pytest

import atlas_paths as P
import discovery_marker as DM
import labpage_audit as L
import stage_gate as G


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setattr(P, 'data', lambda name, school=None, **k: tmp_path / (school or '_') / name)
    (tmp_path / 'u').mkdir()
    pis = [{'pi': f'PI {i}'} for i in range(12)]
    (tmp_path / 'u' / 'pis.json').write_text(json.dumps(pis))
    return SimpleNamespace(root=tmp_path, pis=[p['pi'] for p in pis])


def write(path, names, **extra):
    with open(path, 'a', encoding='utf-8') as f:
        for n in names:
            f.write(json.dumps(dict(pi=n, **extra)) + '\n')


def test_shards_partition_the_pis_and_do_not_depend_on_what_is_done(tree):
    of = 4
    parts = [[n for n in tree.pis if DM.shard_of(n, of) == i] for i in range(of)]
    assert sorted(sum(parts, [])) == sorted(tree.pis) and all(len(set(x)) == len(x) for x in parts)
    write(tree.root / 'u' / 'labpage-audit-discovery.jsonl', tree.pis[:3])
    assert [n for n in tree.pis if DM.shard_of(n, of) == 1] == parts[1]   # unchanged by progress


def test_shard_files_count_as_records_and_a_rerun_takes_only_open_pis(tree):
    d = tree.root / 'u'
    write(d / 'labpage-audit-discovery.jsonl', tree.pis[:4])
    write(d / 'labpage-audit-discovery.shard-0of2.jsonl', tree.pis[4:8])
    assert DM.recorded('u') == set(tree.pis[:8])
    assert DM.open_pis('u') == sorted(tree.pis[8:])
    assert DM.status('u')['complete'] is False
    write(d / 'labpage-audit-discovery.shard-1of2.jsonl', tree.pis[8:])
    assert DM.status('u')['complete'] is True and DM.merged('u') is False


def test_merge_folds_shards_once_and_writes_the_marker(tree):
    d = tree.root / 'u'
    write(d / 'labpage-audit-discovery.jsonl', tree.pis[:2], tag='old')
    write(d / 'labpage-audit-discovery.shard-0of2.jsonl', tree.pis[2:7], tag='s0')
    write(d / 'labpage-audit-discovery.shard-1of2.jsonl', tree.pis[7:], tag='s1')
    assert L.merge_shards('u') == 10
    assert not list(d.glob('*.shard-*')) and DM.merged('u') and DM.status('u')['marker'] is True
    got = {json.loads(x)['pi']: json.loads(x)['tag'] for x in (d / 'labpage-audit-discovery.jsonl').read_text().splitlines()}
    assert len(got) == 12 and got[tree.pis[0]] == 'old' and got[tree.pis[11]] == 's1'
    assert L.merge_shards('u') == 0   # idempotent


def test_a_pi_redone_in_a_shard_wins_over_the_merged_record(tree):
    d = tree.root / 'u'
    write(d / 'labpage-audit-discovery.jsonl', tree.pis, tag='old')
    write(d / 'labpage-audit-discovery.shard-0of2.jsonl', tree.pis[:1], tag='redo')
    assert L.read_discovery('u')[tree.pis[0]]['tag'] == 'redo'
    L.merge_shards('u')
    assert L.read_discovery('u')[tree.pis[0]]['tag'] == 'redo'


def test_history_is_pending_only_for_pis_with_a_people_page(tree):
    d = tree.root / 'u'
    write(d / 'labpage-audit-discovery.jsonl', ['PI 0'], chosen={'lab_site': 'https://a.edu/', 'people_page': 'https://a.edu/people'})
    write(d / 'labpage-audit-discovery.jsonl', ['PI 1'], chosen={'lab_site': 'https://b.edu/'}, history_pages=[])
    write(d / 'labpage-audit-discovery.jsonl', ['PI 2'], chosen={'lab_site': None}, history_pages=[])
    write(d / 'labpage-audit-discovery.jsonl', ['PI 3'], chosen={'lab_site': 'https://c.edu/'}, history_pages=[['alumni', 'https://c.edu/alumni']])
    assert DM.history_pending('u') == ['PI 0', 'PI 3']
    write(d / 'labpage-audit-history.shard-0of2.jsonl', ['PI 0'], wayback={})
    assert DM.history_pending('u') == ['PI 3']
    # the audit sees the captures history requested, laid over the discovery record
    write(d / 'labpage-audit-history.shard-1of2.jsonl', ['PI 3'], wayback={'https://c.edu/alumni': ['https://web.archive.org/web/2020id_/https://c.edu/alumni']})
    assert L.read_discovery('u')['PI 3']['wayback']['https://c.edu/alumni']
    assert 'wayback' not in L.read_discovery('u', history=False)['PI 3']


def test_stage_3_discovery_is_a_sharded_array_and_stage_6_owns_the_history():
    s3 = {s['name']: s for s in G.STEPS['3']}
    assert s3['labpage-discover']['array'] == 8 and '--shard {task} --of 8' in s3['labpage-discover']['cmd']
    assert s3['labpage-discover']['complete'] == 'discovery_marker' and 'discover-merge' in s3['labpage-discover-merge']['cmd']
    names3 = [s['name'] for s in G.STEPS['3']]
    assert names3.index('labpage-discover') < names3.index('labpage-discover-merge') < names3.index('labpage-audit')
    assert not any('history' in s['cmd'] for s in G.STEPS['3'] if s.get('cmd'))
    s6 = [s['name'] for s in G.STEPS['6']]
    assert s6[:3] == ['labpage-history', 'labpage-history-merge', 'labpage-audit-history'] and s6.index('labpage-links') > 2


def test_the_stage_3_gate_never_reads_the_wayback_history_checks():
    import inspect

    import lab_websites
    for name in ('entry', 'gate', 'dated_checks', 'official_check', 'how_found'):
        body = inspect.getsource(getattr(lab_websites, name))
        assert "'wayback_cdx'" not in body and "'wayback_capture'" not in body


# ---- discover_lab with a fake kit: the order of sources, the stop, and the history flag
PAGE = b'<html><title>Wilson Lab</title><body>Ashia Wilson leads the Wilson Lab. Students: Ann Lee, PhD student.</body></html>'


class FakeLp:
    @staticmethod
    def page_text(content, ctype=None):
        return re.sub(rb'<[^>]+>', b' ', content).decode()

    @staticmethod
    def links(content, base):
        from urllib.parse import urljoin
        return [(urljoin(base, h), t) for h, t in re.findall(rb'<a href="([^"]+)">([^<]*)</a>', content) and [(a.decode(), b.decode()) for a, b in re.findall(rb'<a href="([^"]+)">([^<]*)</a>', content)]]

    @staticmethod
    def collapse(x):
        return ' '.join(x.split())

    @staticmethod
    def decode(b):
        return b.decode()

    @staticmethod
    def wayback_id(ts, orig):
        return f'https://web.archive.org/web/{ts}id_/{orig}'


class FakeKit:
    def __init__(self, pages):
        self.pages, self.asked, self.cdx_calls = pages, [], []
        self.lpcap, self.robots_log, self.deferred_archive_urls = FakeLp, {}, set()
        self.names = SimpleNamespace(match_one=lambda a, b: a if a.lower() in b.lower() or b.lower() in a.lower() else None)

    def get(self, url, wb=True):
        self.asked.append(url)
        body = self.pages.get(url)
        if body is None:
            return dict(url=url, status=404, content=b'', error=None)
        return dict(url=url, status=200, content=body, content_type='text/html', sha256='a' * 64, capture_url=None)

    def fetch(self, url, **kw):
        self.asked.append(url)
        return dict(url=url, status=404, content=b'')

    def stored(self, u):
        return (None, None)

    def cdx(self, url, frm=2016, to=2026):
        self.cdx_calls.append(url)
        return [['20200101000000', url, 'd1'], ['20230101000000', url, 'd2']]


@pytest.fixture
def newu(monkeypatch):
    import school_config
    cfg = {'name': 'Newu', 'web': {'domains': ['newu.edu']}}
    monkeypatch.setattr(school_config, 'get', lambda k: cfg if k == 'newu' else (_ for _ in ()).throw(KeyError(k)))
    return 'newu'


def ctx_for(**kw):
    return dict(prior={}, dossier={}, plan={}, seeds={}, registered={}, homepage_finds={}, dblp_persons=kw.get('dblp', {}), cfg=dict(domain='newu\\.edu'))


def pi_row(**kw):
    return dict(pi='Ashia Wilson', names=[], dblp=['d/1'], orcid=['0000-0000-0000-0001'], listings=[], periods=[], **kw)


def test_a_lab_site_from_dblp_stops_the_search_and_skips_orcid_and_later_candidates(newu, monkeypatch):
    monkeypatch.setitem(L.SCHOOLS, 'newu', dict(L.SCHOOLS['newu'], domain='newu\\.edu'))
    pages = {'https://wilson.newu.edu/': PAGE, 'https://other.example.org/~aw/': PAGE}
    ctx = ctx_for(dblp={'d/1': dict(urls=['https://wilson.newu.edu/', 'https://other.example.org/~aw/'])})
    kit = FakeKit(pages)
    rec = L.discover_lab(kit, newu, pi_row(), ctx, first_stop=True)
    assert rec['chosen']['lab_site'] == 'https://wilson.newu.edu/'
    assert set(kit.asked) == {'https://wilson.newu.edu/'}, kit.asked   # no ORCID record, no second candidate
    skipped = [c for c in rec['checks'] if c['source'] == 'later_sources_skipped']
    assert skipped and skipped[0]['result'] == 'site_proven_by_dblp_person_url' and 'orcid_researcher_url' in skipped[0]['skipped']
    # the pre-V4a evaluation asks everything and chooses the same site
    kit2 = FakeKit(pages)
    rec2 = L.discover_lab(kit2, newu, pi_row(), ctx, first_stop=False)
    assert rec2['chosen']['lab_site'] == rec['chosen']['lab_site'] and len(kit2.asked) > len(kit.asked)
    assert any(u.startswith('https://orcid.org/') for u in kit2.asked)


def test_without_a_proof_the_orcid_record_is_asked_after_the_local_sources(newu, monkeypatch):
    monkeypatch.setitem(L.SCHOOLS, 'newu', dict(L.SCHOOLS['newu'], domain='newu\\.edu'))
    kit = FakeKit({'https://aw.example.org/': PAGE})
    ctx = ctx_for(dblp={'d/1': dict(urls=['https://aw.example.org/'])})   # a personal homepage off the school host: not final, so the search goes on
    rec = L.discover_lab(kit, newu, pi_row(), ctx, first_stop=True)
    assert rec['chosen']['lab_site'] == 'https://aw.example.org/'
    assert kit.asked.index('https://aw.example.org/') < next(i for i, u in enumerate(kit.asked) if u.startswith('https://orcid.org/'))
    assert not [c for c in rec['checks'] if c['source'] == 'later_sources_skipped']


def test_discovery_requests_no_wayback_history_unless_asked_and_keeps_the_page_list(newu, monkeypatch):
    monkeypatch.setitem(L.SCHOOLS, 'newu', dict(L.SCHOOLS['newu'], domain='newu\\.edu'))
    page = b'<html><title>Wilson Lab</title><body>Ashia Wilson. <a href="/people">People</a> <a href="/alumni">Alumni</a></body></html>'
    pages = {'https://wilson.newu.edu/': page, 'https://wilson.newu.edu/people': PAGE, 'https://wilson.newu.edu/alumni': PAGE}
    ctx = ctx_for(dblp={'d/1': dict(urls=['https://wilson.newu.edu/'])})
    kit = FakeKit(pages)
    rec = L.discover_lab(kit, newu, pi_row(), ctx)
    assert kit.cdx_calls == [] and rec['wayback'] == {}
    assert not [c for c in rec['checks'] if c['source'] in ('wayback_cdx', 'wayback_capture')]
    assert [k for k, _ in rec['history_pages']] == ['people', 'alumni'] and rec['chosen']['people_page'] == 'https://wilson.newu.edu/people'
    old = L.discover_lab(FakeKit(pages), newu, pi_row(), ctx, history=True, first_stop=False)
    assert set(old['wayback']) == {'https://wilson.newu.edu/people', 'https://wilson.newu.edu/alumni'}
    assert old['chosen'] == rec['chosen']


PROFILE = (b'<html><body><h1>Ashia Wilson</h1><div class="views-field views-field-field-profile-website"><strong>Website: </strong>'
           b'<div class="field-content"><a href="http://www.newu.edu/~aw/">http://www.newu.edu/~aw/</a></div></div>'
           b'<a href="http://www.newu.edu/class">Class Web Pages</a></body></html>')
FRAMESET = b'<html><frameset><frame src="main.html"></frameset></html>'   # a frameset homepage has no text


def test_the_profiles_website_field_outranks_the_registers_earlier_find_and_other_candidates(newu, monkeypatch):
    monkeypatch.setitem(L.SCHOOLS, 'newu', dict(L.SCHOOLS['newu'], domain='newu\\.edu'))
    pages = {'https://www.newu.edu/people/wilson': PROFILE, 'http://www.newu.edu/~aw/': FRAMESET, 'http://www.newu.edu/class': PAGE,
             'https://aw.other.edu/': PAGE}
    ctx = ctx_for(dblp={'d/1': dict(urls=['https://aw.other.edu/'])})
    ctx['registered'] = {'Ashia Wilson': {'url': 'http://www.newu.edu/class'}}   # the earlier (wrong) register find
    kit = FakeKit(pages)
    row = pi_row()
    row['listings'] = [dict(url='https://www.newu.edu/people/wilson', year=2024)]
    rec = L.discover_lab(kit, newu, row, ctx, first_stop=True)
    assert rec['chosen']['lab_site'] == 'http://www.newu.edu/~aw/', rec['chosen']

    assert any(c['source'] == 'school_profile_link' and c.get('field') for c in rec['checks'])
    assert not any(c['source'] == 'school_profile_link' and c['url'].endswith('/class') and c.get('field') for c in rec['checks'])


def test_a_website_field_link_the_generic_anchor_rule_already_listed_still_counts_as_the_field_on_a_port_and_bare_host_wayback_profile(newu, monkeypatch):
    monkeypatch.setitem(L.SCHOOLS, 'newu', dict(L.SCHOOLS['newu'], domain='newu\\.edu'))
    prof = (b'<html><body><h1>Ashia Wilson</h1><div class="views-field views-field-field-profile-website"><strong>Website: </strong>'
            b'<div class="field-content"><a href="http://www.newu.edu/~aw/">Personal Website</a></div></div>'
            b'<a href="http://www.newu.edu/class">Class Web Pages</a></body></html>')
    pages = {'http://newu.edu:80/people/aw': prof, 'http://www.newu.edu/~aw/': PAGE, 'http://www.newu.edu/class': PAGE}
    ctx = ctx_for()
    ctx['registered'] = {'Ashia Wilson': {'url': 'http://www.newu.edu/class'}}
    ctx['homepage_finds'] = {'Ashia Wilson': ['http://www.newu.edu/class']}
    row = pi_row()
    row['listings'] = [dict(url='http://newu.edu:80/people', year=2017)]
    row['lab'] = dict(url='/people/aw')   # the census profile address carries no name (cs.umd.edu/people/vs)
    rec = L.discover_lab(FakeKit(pages), newu, row, ctx, first_stop=True)
    assert rec['chosen']['lab_site'] == 'http://www.newu.edu/~aw/', rec['chosen']



def test_a_registered_blog_section_gives_way_to_the_profile_linked_site_root(newu, monkeypatch):
    monkeypatch.setitem(L.SCHOOLS, 'newu', dict(L.SCHOOLS['newu'], domain='newu\\.edu'))
    prof = (b'<html><body><h1>Ashia Wilson</h1><a href="https://wilsonlab.github.io">https://wilsonlab.github.io</a>'
            b'<a href="https://wilsonlab.github.io/blog">Wilson lab blog</a></body></html>')
    pages = {'https://www.newu.edu/people/wilson': prof, 'https://wilsonlab.github.io': PAGE, 'https://wilsonlab.github.io/blog': PAGE}
    ctx = ctx_for()
    ctx['registered'] = {'Ashia Wilson': {'url': 'https://wilsonlab.github.io/blog'}}
    ctx['homepage_finds'] = {'Ashia Wilson': ['https://wilsonlab.github.io/blog']}
    row = pi_row()
    row['listings'] = [dict(url='https://www.newu.edu/people/wilson', year=2024)]
    rec = L.discover_lab(FakeKit(pages), newu, row, ctx, first_stop=True)
    assert rec['chosen']['lab_site'].rstrip('/') == 'https://wilsonlab.github.io', rec['chosen']
