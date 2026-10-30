"""Adapter for the channels whose bodies still live in lab_channels.py (step_<name>) or its helper modules
(2026-10-30): discover() runs the step exactly as before, on every missing paper as the step always did, so its
candidate rows are the step's own; its outcome becomes Results:
  found  a paper the step produced rows for, or whose known URLs the step grew itself (dspace, infoscience and
         wayback_acm write their candidates as they go: those URLs are marked written_by_step and not written again)
  none   a paper in the step's scope (lab_channels.SCOPE[name]: what the step asks about a paper) with nothing found
  error  such a paper when the step stopped early (an OpenAlex budget stop, repeated S2 failures)
APPLIES is the step's scope."""
from collections import defaultdict

STOPPED = ('openalex_budget_stop', 's2_title_stopped_after_failures', 'stopped')


def _scope(name, school, r, known):
    import lab_channels as L
    sc = L.SCOPE.get(name)
    try:
        return (sc(school, r, known) or None) if sc else name
    except Exception:
        return None


def applies(name):
    def APPLIES(school, paper):
        return bool(_scope(name, school, paper.r, paper.known))
    return APPLIES


def discover(name, school, papers, ctx):
    import lab_channels as L
    before = {p.work_id: set(ctx.known[p.work_id]) for p in ctx.all_papers}
    rows = L.STEPS[name](school, ctx.miss, ctx.known, ctx.n)
    by_w = defaultdict(list)
    for x in rows:
        by_w[x['work_id']].append(x)
    for p in ctx.all_papers:
        grown = sorted(ctx.known[p.work_id] - before[p.work_id] - {x['url'] for x in by_w[p.work_id]})
        by_w[p.work_id] += [dict(work_id=p.work_id, url=u, written_by_step=True) for u in grown]
    stopped = any(ctx.n.get(k) for k in STOPPED)
    in_scope = {p.work_id for p in papers}
    for p in ctx.all_papers:
        found = by_w.get(p.work_id)
        if not found and p.work_id not in in_scope:
            continue
        yield ctx.result(p, 'found' if found else ('error' if stopped else 'none'), urls=found or [],
                         query=_scope(name, school, p.r, before[p.work_id]) or name,
                         detail=dict(stopped=True) if stopped and not found else None)
