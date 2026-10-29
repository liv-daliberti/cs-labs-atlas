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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402


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
    d = P.HIERARCHY / key; d.mkdir(parents=True, exist_ok=True)
    (d / 'hosts.json').write_text(json.dumps(dict(school=key, hosts=out, gate=all(x['consistent'] for x in out)), indent=1, ensure_ascii=False))
    bad = [x for x in out if not x['consistent']]
    print(f'{key}: {len(out)} hosts, {len(bad)} inconsistent' + (': ' + '; '.join(f"{x['host']}: {', '.join(x['problems'])}" for x in bad) if bad else ''))
    return not bad


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1], '--refresh' in sys.argv) else 1)
