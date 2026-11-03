/* metrics: loaded before app.js; shared atlas state is initialized there. */
'use strict';
function accepted(lab) {
  return (lab.papers || []).filter(
    (p) =>
      p[state.view] &&
      DATA.works[p.work] &&
      DATA.works[p.work].year >= state.from &&
      DATA.works[p.work].year <= state.to,
  );
}

function labCount(lab) {
  return Object.entries(lab.paperCounts?.[state.view] || {}).reduce(
    (n, [y, v]) => n + (+y >= state.from && +y <= state.to ? v : 0),
    0,
  );
}

function matches(field, status, uid) {
  return (
    (!state.field || field === state.field) &&
    (!state.leadership || status === state.leadership) &&
    (!state.country || uniById.get(uid)?.country === state.country)
  );
}

function countCells(u, unfiltered = false) {
  return (u?.counts || DATA.counts).filter((c) => unfiltered || matches(c.field, c.status, c.u));
}

function countUnits(u, key = 'n', unfiltered = false) {
  return d3.sum(countCells(u, unfiltered), (c) => c[key] || 0);
}

function relevantLabs(u) {
  return (u.labs || []).filter((l) => matches(l.field, l.leadershipStatus, u.id));
}

function filteredUniversities() {
  return DATA.universities
    .filter((u) => !state.country || u.country === state.country)
    .filter((u) => (!state.field && !state.leadership) || countUnits(u));
}

function isDefaultScope() {
  return (
    !state.country && !state.field && !state.leadership && state.from === 2016 && state.to === 2026
  );
}

function summarize(metrics, allowed = null, labs = null) {
  const years = new Map();
  for (let y = state.from; y <= state.to; y++)
    years.set(y, {
      year: y,
      activity: 0,
      publishing: 0,
      works: 0,
      links: 0,
      oa: null,
      oaCount: 0,
      oaUnknown: 0,
      groups: new Set(),
    });
  if (labs) {
    for (const l of labs) for (const y of l.years) if (years.has(y)) years.get(y).activity++;
  } else
    for (const c of metrics.units)
      if (matches(c.field, c.status, c.u))
        for (const [y, n] of Object.entries(c.years))
          if (years.has(+y)) years.get(+y).activity += n;
  const totals = {
      works: 0,
      oa: 0,
      oaUnknown: 0,
      authorsKnown: 0,
      authorsSum: 0,
      countriesKnown: 0,
      international: 0,
    },
    topics = new Map(),
    groups = new Set(),
    labCounts = new Map();
  let groupLinks = 0;
  for (const b of metrics.buckets) {
    if (b.view !== state.view) continue;
    const members = b.members.filter(
      (m) => matches(m.field, m.status, m.uni) && (!allowed || allowed.has(m.lab)),
    );
    if (!members.length) continue;
    const gids = new Set(members.flatMap((m) => m.groups)),
      lids = new Set(members.map((m) => m.lab));
    for (const [y, v] of Object.entries(b.years)) {
      const a = years.get(+y);
      if (!a || !v.works) continue;
      for (const k of Object.keys(totals)) totals[k] += v[k] || 0;
      for (const [topic, n] of Object.entries(v.topics))
        topics.set(topic, (topics.get(topic) || 0) + n);
      gids.forEach((g) => {
        groups.add(g);
        a.groups.add(g);
      });
      groupLinks += v.works * gids.size;
      lids.forEach((l) => labCounts.set(l, (labCounts.get(l) || 0) + v.works));
      a.works += v.works;
      a.links += v.works * lids.size;
      a.oaCount += v.oa;
      a.oaUnknown += v.oaUnknown || 0;
    }
  }
  const topicTotal = d3.sum(topics.values()),
    links = d3.sum(labCounts.values());
  const stats = {
    works: totals.works,
    publishing: groups.size,
    groupLinks,
    oa: totals.works - totals.oaUnknown ? totals.oa / (totals.works - totals.oaUnknown) : null,
    meanAuthors: totals.authorsKnown ? totals.authorsSum / totals.authorsKnown : null,
    topicCount: topics.size,
    entropy: topicTotal
      ? -d3.sum(topics.values(), (n) => (n / topicTotal) * Math.log2(n / topicTotal))
      : null,
    international: totals.countriesKnown ? totals.international / totals.countriesKnown : null,
    hhi: links ? d3.sum(labCounts.values(), (n) => (n / links) ** 2) : null,
  };
  return {
    stats,
    annual: [...years.values()].map((a) => ({
      year: a.year,
      activity: a.activity,
      publishing: a.groups.size,
      works: a.works,
      links: a.links,
      oa: a.works - a.oaUnknown ? a.oaCount / (a.works - a.oaUnknown) : null,
    })),
  };
}

function globalSummary() {
  return globalMetrics ? summarize(globalMetrics) : DATA.overview[state.view];
}

function universitySummary(u) {
  if (u.loaded) return scopeSummary(relevantLabs(u), u);
  if (globalMetrics)
    return summarize({
      units: globalMetrics.units.filter((c) => c.u === u.id),
      buckets: globalMetrics.buckets.map((b) => ({
        ...b,
        members: b.members.filter((m) => m.uni === u.id),
      })),
    });
  return u.overview[state.view];
}

function scopeSummary(labs, u) {
  const unique = [...new Map(labs.map((l) => [l.id, l])).values()];
  return summarize(u.metrics, new Set(unique.map((l) => l.id)), unique);
}
