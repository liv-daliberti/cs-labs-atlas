"""Stage-0 gate for a school's hosts (docs/ADDING-A-SCHOOL.md): every host named in schools/<key>.toml [[hosts]] is
checked against its robots.txt (requests with a timeout, stored in captures/<key>.sqlite table robots) and, when the
charter says use = "live", probed once with its `probe` URL through school_web.live(), which records a bot challenge
and blocks the host. The verdict per host goes to hierarchy/<key>/hosts.json.

verdicts  robots     allowed | disallowed (our UA or '*') | disallowed-for-ai-agents (ClaudeBot / anthropic-ai /
                     Claude-Web named) | unreachable
          probe      ok | challenge | http <status> | skipped (use != live, or no probe URL) | disallowed
          consistent the charter's `use` agrees: use = live needs robots allowed and a probe that is not a challenge; a
                     host that disallows AI agents must be use = none; a host that challenged must be wayback-only or none
The gate passes when every host is consistent. Learned from Michigan (2026-10-29): robots.txt allowing a host proves
nothing about a Cloudflare challenge in front of it (cse/ece.engin.umich.edu), so the probe is part of the gate.

usage: school_hosts.py <key> [--refresh]
"""
import json, sys, time

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402


def urls_on_host(cfg, host):
    """Listing URLs of the charter's departments and affiliated units that sit on `host` (a moved department site: UChicago friction 25)."""
    out = []
    for grp in (cfg.get('departments') or []) + (cfg.get('affiliated_units') or []):
        for u in [s.get('url') for s in grp.get('listings') or [] if isinstance(s, dict)] + [x for x in grp.get('listings') or [] if isinstance(x, str)]:
            if u and host in u and u not in out:
                out.append(u)
    return out


def main(key, refresh=False):
    cfg = S.get(key); c = W.con(key); out = []
    for h in cfg.get('hosts') or []:
        host, use, probe = h['host'], h.get('use') or 'live', h.get('probe') or ''
        st, body = W.robots_row(c, host, refresh=refresh)
        ours, ai, delay = W.robots_decision(st, body, probe or '/')
        robots = 'unreachable' if (st == -1 or st >= 500) else ('allowed' if ours and ai else ('disallowed-for-ai-agents' if ours else 'disallowed'))
        pr = 'skipped'
        blocked = c.execute('select why from blocked where host=?', (host,)).fetchone()
        if blocked:
            pr = 'challenge'
        elif use == 'live' and probe and robots == 'allowed':
            res = W.live(c, probe, refresh=refresh)
            pr = 'disallowed' if res is None else ('challenge' if res[0] == 999 else ('ok' if res[0] == 200 else f'http {res[0]}'))
            if res is not None and res[0] == 310:  # an off-host redirect (a moved department site): say where, the charter then names the new host
                pr = 'http 310 ' + W.live_html(c, probe).replace('redirected off host to ', '->').strip()
                mine = urls_on_host(cfg, host)
                if mine:
                    pr += f'; the charter has {len(mine)} listing URL(s) on {host} to move or add on the new host: ' + ', '.join(mine[:4])
        elif probe and robots != 'allowed':
            pr = 'disallowed'
        problems = []
        if use == 'live' and robots != 'allowed':
            problems.append(f'use = live but robots {robots}')
        if use == 'live' and pr == 'challenge':
            problems.append('use = live but the probe was a challenge')
        if robots == 'disallowed-for-ai-agents' and use != 'none':
            problems.append('robots disallows AI agents by name: use must be none')
        if pr == 'challenge' and use not in ('wayback-only', 'none'):
            problems.append('challenged: use must be wayback-only or none')
        if use == 'live' and pr.startswith('http') and pr not in ('http 200',):
            problems.append(f'probe returned {pr}')
        out.append(dict(host=host, use=use, purpose=h.get('purpose'), robots=robots, robots_status=st, crawl_delay=delay, probe=probe, probe_result=pr,
                        blocked=blocked[0] if blocked else None, consistent=not problems, problems=problems,
                        checked_at=time.strftime('%Y-%m-%dT%H:%M:%S')))
        print(json.dumps(out[-1], ensure_ascii=False), flush=True)
    P.data_w('hosts.json', key).write_text(json.dumps(dict(school=key, hosts=out, gate=all(x['consistent'] for x in out)), indent=1, ensure_ascii=False))
    bad = [x for x in out if not x['consistent']]
    print(f'{key}: {len(out)} hosts, {len(bad)} inconsistent' + (': ' + '; '.join(f"{x['host']}: {', '.join(x['problems'])}" for x in bad) if bad else ''))
    return not bad


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1], '--refresh' in sys.argv) else 1)
