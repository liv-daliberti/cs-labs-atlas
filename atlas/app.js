'use strict';
const $ = (s) => document.querySelector(s),
  fmt = (n) => new Intl.NumberFormat('en').format(n),
  el = (tag, text, cls) => {
    const x = document.createElement(tag);
    if (text !== undefined) x.textContent = text;
    if (cls) x.className = cls;
    return x;
  };
const COLORS = {
  biological_and_health_sciences: '#58c6b1',
  social_sciences: '#bd91ce',
  physical_sciences: '#89a7ed',
  mathematics_and_statistics: '#89a7ed',
  chemical_sciences: '#89a7ed',
  engineering_and_technology: '#d3b27d',
  computer_and_information_sciences: '#d3b27d',
  earth_and_environmental_sciences: '#618f81',
  agricultural_and_veterinary_sciences: '#79a887',
  interdisciplinary: '#839ba8',
};
const state = {
  country: '',
  field: '',
  leadership: '',
  view: 'combined',
  sizing: 'units',
  from: 2016,
  to: 2026,
  tab: 'atlas',
  selected: 'root',
  page: 0,
  labView: 'both',
  unitKind: '',
};
let cameraZoom,
  nodeLayer,
  labelCandidates,
  cameraFrame = 0,
  renderedSizing = null;
const camera = { transform: d3.zoomIdentity, angle: 0 };
let DATA,
  uniById,
  labById,
  nodeById,
  tree,
  focus,
  currentView,
  nodes,
  labels,
  visibleLabs = [],
  activeUniversities = [];
let expandedUniversity = null,
  navigation = 0,
  globalMetrics = null,
  refreshVersion = 0;
const assetCache = new Map();
let labMap = null,
  mapRecords = new Map(),
  authorshipLines,
  nodeIcons,
  selectedMapRecord = null;
// Computer-science scope (owner requests 2026-10-21 and 2026-10-22). scripts/build-cs-scope.py marks every lab
// (csScope; csShown: the CS departments' PI labs with lab papers at their schools, CS units with papers elsewhere)
// and writes counts, summaries and metrics over exactly the shown labs; the app reads only those. Hidden records
// stay in the data and are not shown.
const CS_COLORS = { field: '#d3b27d', department: '#89a7ed' };
const outOfScope = new Map();
let outOfScopeUniversities = new Map();
const CS_REASON_LABELS = {
  field: 'Field: computer and information sciences',
  department: 'Computing department',
  field_and_department: 'Field and computing department',
  cs_department_pi_lab: 'PI lab of a CS department',
};
const PI_SCHOOL_NAMES = {
  princeton: 'Princeton',
  cmu: 'CMU',
  epfl: 'EPFL',
  mit: 'MIT',
  berkeley: 'Berkeley',
  stanford: 'Stanford',
};
const plural = (n, one, many) => fmt(n) + ' ' + (n === 1 ? one : many);
function scopeNote(text) {
  const box = $('#scope-note');
  if (!box) return;
  box.textContent = text || '';
  box.hidden = !text;
}
function applyCSScope(data) {
  const cs = data.csScope;
  if (!cs?.rule || !cs.counts || !cs.overview || !cs.metricsFile)
    throw new Error('The CS scope is missing from this dataset; run scripts/build-cs-scope.py');
  CSScope.configure(cs.rule);
  AtlasAffiliations.setLabelFilter(CSScope.departmentLabels);
  const empty = {
    stats: {
      works: 0,
      publishing: 0,
      groupLinks: 0,
      oa: null,
      meanAuthors: null,
      topicCount: 0,
      entropy: null,
      international: null,
      hhi: null,
    },
    annual: [],
  };
  for (const u of data.universities) {
    u.counts = u.csScope?.counts || [];
    u.overview = u.csScope?.overview || { combined: empty, reviewed: empty, strict: empty };
  }
  outOfScopeUniversities = new Map(
    data.universities.filter((u) => !u.csScope?.labs).map((u) => [u.id, u]),
  );
  data.universities = data.universities.filter((u) => u.csScope?.labs > 0);
  data.counts = cs.counts;
  data.overview = cs.overview;
  data.metricsFile = cs.metricsFile;
  return data;
}
// "N units without papers are not shown" (owner decision 2026-10-22), per university and in the totals.
function hiddenCounts(unis) {
  const h = { no_papers: 0, no_lab_papers: 0, replaced_by_pi_labs: 0 };
  for (const u of unis) for (const k of Object.keys(h)) h[k] += u.csScope?.hidden?.[k] || 0;
  return h;
}
function piSchoolNames() {
  const ids = Object.keys(DATA.csScope.hierarchy || {}).map((id) => PI_SCHOOL_NAMES[id] || id);
  return ids.length > 1
    ? ids.slice(0, -1).join(', ') + ' and ' + ids[ids.length - 1]
    : ids.join('');
}
function hiddenNote(h, oneSchool = false) {
  const parts = [];
  if (h.no_papers)
    parts.push(
      plural(h.no_papers, 'CS unit', 'CS units') +
        ' without papers ' +
        (h.no_papers === 1 ? 'is' : 'are') +
        ' not shown',
    );
  if (h.no_lab_papers)
    parts.push(
      plural(h.no_lab_papers, 'PI lab', 'PI labs') +
        ' without lab papers ' +
        (h.no_lab_papers === 1 ? 'is' : 'are') +
        ' not shown',
    );
  if (h.replaced_by_pi_labs)
    parts.push(
      plural(h.replaced_by_pi_labs, 'earlier inventory unit', 'earlier inventory units') +
        (oneSchool ? '' : ' at ' + piSchoolNames()) +
        ' ' +
        (h.replaced_by_pi_labs === 1 ? 'is' : 'are') +
        ' replaced by the CS departments’ PI labs',
    );
  return parts.join(' · ');
}
function hiddenShort(u) {
  const h = u.csScope?.hidden || {},
    parts = [];
  if (h.no_papers) parts.push(fmt(h.no_papers) + ' without papers');
  if (h.no_lab_papers)
    parts.push(plural(h.no_lab_papers, 'PI lab', 'PI labs') + ' without lab papers');
  if (h.replaced_by_pi_labs) parts.push(fmt(h.replaced_by_pi_labs) + ' inventory units replaced');
  return parts.join(' · ');
}
function allCSUniversities() {
  return [...DATA.universities, ...outOfScopeUniversities.values()].filter(
    (u) => u.csScope?.inScope || u.csScope?.piLabs,
  );
}
function hiddenTotals() {
  return hiddenCounts(
    allCSUniversities().filter((u) => !state.country || u.country === state.country),
  );
}
function csDepartmentsLink(u, query = '') {
  const a = el('a', 'Open in CS departments →', 'aside-button');
  a.href = 'cs-departments.html?school=' + encodeURIComponent(u.csScope.school) + query;
  return a;
}
function labelField(v) {
  return (v || 'Unclassified').replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
function safeLink(url, text) {
  const a = el('a', text);
  try {
    const u = new URL(url);
    if (['http:', 'https:'].includes(u.protocol)) {
      a.href = u.href;
      a.target = '_blank';
      a.rel = 'noopener';
    }
  } catch {}
  return a;
}

// Works without an open-access flag (oaUnknown: CS departments PI-lab papers) are left out of the open-access share,
// as in scripts/lazy_atlas.py summarize_metrics.

function loadStatus(message = '', retry = null) {
  const box = $('#load-status');
  box.replaceChildren();
  box.hidden = !message;
  $('#map').setAttribute('aria-busy', message && !retry ? 'true' : 'false');
  if (message) box.append(el('span', message));
  if (retry) {
    const b = el('button', 'Retry');
    b.onclick = retry;
    box.append(b);
  }
}

const LEADERSHIP_LABELS = {
  missing_name: 'PI / leader missing',
  name_recorded: 'Name awaiting leadership review',
  leadership_reviewed: 'Leadership source checked',
  publication_identity_verified: 'Publication identity verified',
};

function hierarchy() {
  activeUniversities = filteredUniversities();
  visibleLabs = activeUniversities.filter((u) => u.id === expandedUniversity).flatMap(relevantLabs);
  const children = activeUniversities.map((u) => {
    const labs = u.id === expandedUniversity ? relevantLabs(u) : [],
      leaf = (l, name) => ({
        id: AtlasAffiliations.occurrence(l, name),
        name: l.name,
        kind: 'lab',
        field: l.field,
        record: l,
        university: u,
        value: 1,
      });
    const { groups, unassigned } = AtlasAffiliations.group(labs);
    const branches = [...groups].map(([name, list]) => ({
      id: u.id + '::' + name,
      name,
      kind: 'department',
      university: u,
      children: list.map((l) => leaf(l, name)),
    }));
    branches.push(...unassigned.map((l) => leaf(l, null)));
    const counts = countCells(u),
      byField = d3.rollup(
        counts,
        (v) => d3.sum(v, (c) => c.n),
        (c) => c.field,
      );
    return {
      id: u.id,
      name: u.name,
      kind: 'university',
      record: u,
      known: countUnits(u),
      field: [...byField].sort((a, b) => b[1] - a[1])[0]?.[0],
      children: branches.length ? branches : undefined,
      value: branches.length ? undefined : Math.max(1, countUnits(u)),
    };
  });
  const root = d3
    .hierarchy({
      id: 'root',
      name: 'All universities',
      kind: 'root',
      children: children.length ? children : undefined,
      value: children.length ? undefined : 1,
    })
    .sum((d) => d.value || 0)
    .sort((a, b) => b.value - a.value || a.data.name.localeCompare(b.data.name));
  d3
    .pack()
    .size([700, 700])
    .padding((d) => (d.depth === 0 ? 7 : d.depth === 1 ? 5 : 2))(root);
  root.eachAfter((n) => {
    if (n.data.kind === 'department') {
      const counts = d3.rollup(
        n.leaves(),
        (v) => v.length,
        (l) => l.data.field,
      );
      n.data.field = [...counts].sort((a, b) => b[1] - a[1])[0]?.[0];
    }
  });
  tree = root;
  nodeById = new Map(root.descendants().map((n) => [n.data.id, n]));
}
function unitMatches(lab) {
  return !state.unitKind || ResearchUnitKinds.get(lab).key === state.unitKind;
}
function departmentLabs(d) {
  return AtlasAffiliations.uniqueLabs(nodeById.get(d.id)).filter(unitMatches);
}
function unitControls(d) {
  const box = $('#unit-type-controls');
  box.hidden = d.kind !== 'department';
  if (box.hidden) return;
  const labs = AtlasAffiliations.uniqueLabs(nodeById.get(d.id)),
    counts = new Map();
  labs.forEach((l) => {
    const key = ResearchUnitKinds.get(l).key;
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  const select = $('#unit-kind');
  select.replaceChildren();
  const all = el('option', 'All research units (' + labs.length + ')');
  all.value = '';
  select.append(all);
  for (const [key, label] of Object.entries(ResearchUnitKinds.labels)) {
    if (!counts.has(key)) continue;
    const option = el('option', label + ' (' + counts.get(key) + ')');
    option.value = key;
    select.append(option);
  }
  select.value = state.unitKind;
  select.onchange = () => {
    state.unitKind = select.value;
    state.page = 0;
    window.atlas.select(state.selected, false);
  };
}

function labControls(isLab) {
  $('#lab-view-controls').hidden = !isLab;
  $('.size-control').hidden = isLab;
  if (!isLab) {
    labMap = null;
    mapRecords.clear();
    selectedMapRecord = null;
    return;
  }
  document.querySelectorAll('[data-lab-map-view]').forEach((b) => {
    b.setAttribute('aria-pressed', String(b.dataset.labMapView === state.labView));
    b.onclick = () => {
      state.labView = b.dataset.labMapView;
      select(state.selected, false);
    };
  });
  const extra = labMap.papers.filter((p) => p.studentOnly).length;
  $('#lab-map-summary').textContent =
    fmt(labMap.students.length) +
    ' researcher records (' +
    fmt(labMap.studentCount) +
    ' with student roles) · ' +
    fmt(labMap.acceptedCount) +
    ' source-associated papers' +
    (extra ? ' · ' + fmt(extra) + ' additional researcher-linked works' : '') +
    ' · ' +
    fmt(labMap.verifiedCount) +
    ' verified authorship connections · ' +
    fmt(labMap.candidateCount) +
    ' candidate or profile-listing connections. People include separately sourced roster, advising, and paper-specific collaboration contexts. ' +
    (labById.get(state.selected)?.hierarchy
      ? 'Lab papers have the PI on the byline, a supported university connection, and a date inside the PI’s appointment. A stated advisee co-author can support the connection when affiliations are absent. People include the PI, stated advisees and members of the PI’s own unit; candidate connections are supported name matches on each lab paper’s byline.'
      : labById.get(state.selected)?.unitType === 'department_publication_context'
        ? 'Department records preserve individually sourced research, including work with no established lab attribution.'
        : 'Default lab papers require PI authorship and supported faculty / lab dates. Roster and advising records stay visible even without qualifying papers.');
  $('#lab-map-clear').hidden = true;
  $('#lab-map-selection').hidden = true;
  $('#lab-map-clear').onclick = () => {
    highlightMap(null);
    detail(nodeById.get(state.selected).data);
  };
}

async function init() {
  try {
    DATA = await loadDataset();
    window.DatasetUpdates?.start();
    state.view = initialPublicationView(location.search);
    $('#view').value = state.view;
    uniById = new Map(DATA.universities.map((u) => [u.id, u]));
    labById = new Map();
    DATA.universities.forEach((u) =>
      u.labs.forEach((l) => {
        l.uniId = u.id;
        labById.set(l.id, l);
      }),
    );
    $('#cutoff').textContent =
      'DATA UPDATED ' + DATA.asOf + ' · PAPERS THROUGH ' + DATA.publicationSummary.window_end;
    {
      const s = DATA.csScope.summary,
        pi = s.byReason.cs_department_pi_lab;
      $('#collection-note').textContent =
        `${fmt(s.labs)} computer science labs with papers across ${fmt(DATA.universities.length)} universities: ${fmt(pi)} PI labs of the CS departments at ${piSchoolNames()}, and ${fmt(s.labs - pi)} CS units with linked papers elsewhere. ${fmt(DATA.overview.combined.stats.works)} distinct accepted research works.`;
    }
    $('#footer-note').textContent =
      `Data updated ${DATA.asOf} · Publications through ${DATA.publicationSummary.window_end} · Incomplete inventory`;
    for (const c of [...new Set(DATA.universities.map((u) => u.country))].sort()) {
      const o = el('option', c);
      o.value = c;
      $('#country').append(o);
    }
    for (let y = 2016; y <= 2026; y++) {
      for (const id of ['from', 'to']) {
        const o = el('option', String(y));
        o.value = y;
        $('#' + id).append(o);
      }
    }
    $('#from').value = 2016;
    $('#to').value = 2026;
    for (const key of ['country', 'leadership', 'view', 'sizing', 'from', 'to'])
      $('#' + key).onchange = () => {
        state[key] = ['from', 'to'].includes(key) ? Number($('#' + key).value) : $('#' + key).value;
        if (state.from > state.to) {
          if (key === 'from') state.to = state.from;
          else state.from = state.to;
          $('#from').value = state.from;
          $('#to').value = state.to;
        }
        refresh();
      };
    $('#clear').onclick = () => {
      Object.assign(state, {
        country: '',
        field: '',
        leadership: '',
        view: 'combined',
        sizing: 'units',
        from: 2016,
        to: 2026,
        selected: 'root',
        unitKind: '',
      });
      for (const k of ['country', 'field', 'leadership', 'view', 'sizing', 'from', 'to'])
        $('#' + k).value = state[k];
      $('#search').value = '';
      refresh();
    };
    $('#show-missing-leaders').onclick = () => {
      state.leadership = 'missing_name';
      $('#leadership').value = 'missing_name';
      refresh();
    };
    $('#use-map-scope').onchange = renderTrends;
    $('#search').oninput = search;
    $('#search').onkeydown = (e) => {
      if (e.key === 'Escape') $('#search-results').hidden = true;
    };
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.search-label')) $('#search-results').hidden = true;
    });
    $('#back').onclick = goBack;
    $('#reset-map').onclick = () => select('root');
    document.querySelectorAll('.tab').forEach((b) => (b.onclick = () => setTab(b.dataset.tab)));
    setupCamera();
    window.addEventListener('resize', () => {
      if (currentView) renderSizeKey();
    });
    await refresh();
    renderCoverage();
    const blockers = DATA.publicationSummary.api_collection_blockers || [];
    if (blockers.length) {
      $('#publication-status').hidden = false;
      $('#publication-status').textContent = 'Recorded collection limits: ' + blockers.join(' ');
    }
    window.atlas = {
      state,
      select,
      getData: () => DATA,
      getSizing: () => renderedSizing,
      getCamera: () => ({
        scale: camera.transform.k,
        x: camera.transform.x,
        y: camera.transform.y,
        rotation: camera.angle,
      }),
    };
    const route = new URLSearchParams(location.search);
    if (['strict', 'reviewed', 'combined'].includes(route.get('view'))) {
      state.view = route.get('view');
      $('#view').value = state.view;
      await refresh();
    }
    const routeUni = route.get('university');
    if (uniById.has(routeUni)) {
      await select(routeUni, false);
      const requestedDepartment = route.get('department');
      if (requestedDepartment) {
        const label = AtlasAffiliations.canonicalLabel({ uniId: routeUni }, requestedDepartment),
          id = routeUni + '::' + label;
        if (nodeById.has(id)) await select(id, false);
        else
          scopeNote(
            requestedDepartment +
              ' is not a computer science department in the CS atlas at ' +
              uniById.get(routeUni).name +
              '.',
          );
      }
      const requestedLab = route.get('lab');
      if (requestedLab && labById.get(requestedLab)?.uniId === routeUni)
        await select(requestedLab, false);
      else if (requestedLab && outOfScope.get(requestedLab)?.uniId === routeUni)
        await select(requestedLab, false);
      else if (requestedLab)
        scopeNote('That lab is not shown in the CS atlas at ' + uniById.get(routeUni).name + '.');
    } else if (outOfScopeUniversities.has(routeUni)) {
      const o = outOfScopeUniversities.get(routeUni);
      scopeNote(
        o.name +
          ' is not in the CS atlas: ' +
          (o.csScope?.inScope
            ? hiddenNote(o.csScope.hidden, true) +
              ', so no computer science units with papers are shown there.'
            : 'no computer science units are recorded there.'),
      );
    }
    if (location.hash === '#coverage') await setTab('coverage');
  } catch (error) {
    $('#error').hidden = false;
    $('#error').textContent =
      'The dataset could not load. Serve this folder over HTTP and retry. ' + error.message;
    console.error(error);
  }
}
init();
