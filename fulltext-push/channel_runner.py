"""The one runner for discovery channel plugins (fulltext-push/channels/; docs/CHANNELS.md; 2026-10-30).

For each channel: the school's missing lab papers (lab_channels.plan_for: the coverage counter's rule, matched to their
catalog works, with their known URLs) -> the papers the channel APPLIES to -> its discover() Results ->
  known-URL filtering   a found URL already among the work's candidates / attempts / pending packages is not written again
  candidates            committed batches into the catalog (Princeton: a discovery package), with evidence files
                        (lab_channels.write -> ftp_common.write_candidates)
  checks                one row per Result into fulltext-push/checks/<school>.sqlite (checks.py), the ledger's input
  summary               one line per channel in logs/channels.jsonl
--dry: nothing is written (no candidates, no checks, no summary line); the would-be candidate rows are returned.
usage: channel_runner.py <school> <channel> [<channel> ...] [--dry]      (lab_channels.py and run_steps.sh call it)
"""
import json, sys, time
from collections import Counter

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import ftp_common as F  # noqa: E402
import channels as CH  # noqa: E402


class Ctx:
    """What a channel gets besides its papers: the school, counters, the work's known URLs (live), keys, pacing and
    robots.txt (one Pacer per delay; robots.txt honoured for the client's user agent)."""

    def __init__(self, school, all_papers, known, dry):
        import lab_channels as L
        self.school, self.all_papers, self.known, self.dry = school, all_papers, known, dry
        self.miss = [(p.r, p.work_id) for p in all_papers]
        self.has_arxiv = L.has_arxiv
        self.n = Counter()
        self._s, self._pacers, self._robots = None, {}, {}

    def write(self, rows, step):
        """For a channel that writes as it goes (hours of lookups): known-URL filtering, then the candidate write."""
        import lab_channels as L
        return L.write(self.school, L.new_rows(rows, self.known), step, dry=self.dry)

    def result(self, paper, status, urls=(), query=None, detail=None):
        return CH.Result(paper.key, paper.work_id, status, list(urls), query, detail)

    def env(self, name):
        import os
        F.load_env()
        return os.environ.get(name)

    def session(self):
        if self._s is None:
            import requests
            self._s = requests.Session(); self._s.headers['User-Agent'] = F.UA
        return self._s

    def polite_get(self, url, delay=3.0):
        import lab_channels as L
        p = self._pacers.setdefault(delay, L.Pacer(delay))
        return L.polite_get(self.session(), url, p, self._robots)


def run_channel(school, name, miss, known, dry=False, log=True):
    """-> (rows written or, dry, would be written, Counter). miss: [(lab paper row, work id)] from plan_for."""
    import lab_channels as L
    mod = CH.load(name)
    t0 = time.time()
    papers = [CH.Paper(r['work'] or r['oa'], w, r, set(known[w])) for r, w in miss]
    ctx = Ctx(school, papers, known, dry)
    chosen = [p for p in papers if mod.APPLIES(school, p)]
    results = list(mod.discover(school, chosen, ctx))
    rows = []
    for res in results:
        if res.status != 'found':
            continue
        for u in res.urls:
            row = dict(u) if isinstance(u, dict) else dict(work_id=res.work_id, url=u, landing_url=None, version=None, source=name, detail=None)
            if not row.get('written_by_step'):
                rows.append(row)
    rows = L.new_rows(rows, known)
    added = L.write(school, rows, name, dry=dry)
    n = ctx.n
    if not dry:
        import checks
        try:
            n['checks_recorded'] = checks.record(school, [dict(paper_key=res.paper_key, work_id=res.work_id, channel=name, query=res.query, result=res.status,
                                                               detail=res.detail if res.status != 'found' else dict(urls=[(u.get('url') if isinstance(u, dict) else u) for u in res.urls][:5]))
                                                          for res in results])
        except Exception as e:  # the checks store never costs a channel its candidates
            n['checks_record_failed'] = str(e)[:200]
    rec = dict(at=F.now(), school=school, step=name, missing_in_catalog=len(miss), applies=len(chosen), rows=len(rows),
               works=len({r['work_id'] for r in rows}), candidates_added=added + n.pop('candidates_added', 0),
               results=dict(Counter(r.status for r in results)), seconds=round(time.time() - t0), dry=dry, **n)
    print(json.dumps(rec), flush=True)
    if log and not dry:
        with open(F.HERE / 'logs' / 'channels.jsonl', 'a') as f:
            f.write(json.dumps(rec) + '\n')
    return rows, n


def main(argv=None):
    import lab_channels as L
    argv = sys.argv[1:] if argv is None else argv
    args = [a for a in argv if not a.startswith('--')]
    dry = '--dry' in argv
    if dry:
        import labpage_channel
        labpage_channel.DRY = True
    school, names = args[0], args[1:]
    F.load_env()
    miss, known, base = L.plan_for(school)
    for name in names:
        run_channel(school, name, miss, known, dry=dry)


if __name__ == '__main__':
    main()
