/* navigation: loaded before app.js; shared atlas state is initialized there. */
'use strict';
async function select(id, animate = true) {
  const token = ++navigation;
  scopeNote('');
  if (outOfScope.has(id) && !labById.has(id)) {
    const o = outOfScope.get(id),
      where =
        o.name +
        ' (' +
        (uniById.get(o.uniId)?.name || outOfScopeUniversities.get(o.uniId)?.name || o.uniId) +
        ')';
    scopeNote(
      o.hidden === 'no_lab_papers'
        ? where +
            ' is not shown in the CS atlas: it has no lab papers yet. PI labs without lab papers are not listed on CS departments either; the reason is kept with the data.'
        : o.hidden === 'no_papers'
          ? where + ' is not shown in the CS atlas: no papers are linked to it yet.'
          : where +
            ' is not in the CS atlas: its field and department are outside computer science.',
    );
    return;
  }
  try {
    if (mapRecords.has(id)) {
      loadStatus();
      const record = mapRecords.get(id);
      highlightMap(id);
      detail(record);
      if (matchMedia('(max-width:760px)').matches)
        $('#detail').scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    if (DATA.works[id]) {
      loadStatus();
      const parent = labById.get(state.selected) || nodeById.get(state.selected)?.data.record;
      const edge = parent?.papers?.find((p) => p.work === id);
      if (edge) detail({ kind: 'paper', record: DATA.works[id], lab: parent, edge });
      return;
    }
    const university = uniById.get(id),
      existing = nodeById?.get(id),
      lab = labById.get(id) || (existing?.data.kind === 'lab' ? existing.data.record : null);
    if (university) {
      loadStatus(university.loaded ? '' : 'Loading ' + university.name + ' labs…');
      await ensureUniversity(university);
    } else if (lab) {
      loadStatus(lab.papersLoaded ? '' : 'Loading ' + lab.name + ' papers…');
      await ensureLab(lab);
      await LabMapRecords.ensure(lab);
    } else if (id !== 'root' && !existing) return;
    if (state.sizing === 'works' && id === 'root') await ensureMetrics();
    if (token !== navigation) return;
    expandedUniversity =
      id === 'root' ? null : university?.id || lab?.uniId || existing?.data.university?.id;
    state.selected = id;
    state.page = 0;
    hierarchy();
    const n = nodeById.get(id) || tree;
    state.selected = n.data.id;
    if (n.data.kind === 'department' && !AtlasAffiliations.uniqueLabs(n).some(unitMatches))
      state.unitKind = '';
    if (n.data.kind === 'lab') paint(paperTree(n.data.record), null, false);
    else if (state.sizing === 'works') paint(workTree(n), null, false);
    else paint(unitTree(n), null, false);
    labControls(n.data.kind === 'lab');
    unitControls(n.data);
    renderLegend(n.data.kind === 'lab');
    $('#map-size-note').textContent =
      n.data.kind === 'lab'
        ? 'Each bubble is one researcher or paper. Solid lines show verified authorship; dashed lines show candidate authorship or a verified profile listing. Dashed paper borders mark researcher-linked works without a separate lab association. Years filter papers; roster and advising observations retain their separate source years.'
        : state.sizing === 'works'
          ? 'Size: distinct linked works in the selected years and publication view. Shared works count once within each circle. Positions and scale use the full 2016–2026 combined view; compare peers at this level. Hollow markers mean no linked works yet.'
          : 'Size: computer science labs in each circle. Affiliation groups can overlap; their counts must not be added together. University totals count each lab once. Compare peers at this level.';
    detail(n.data);
    breadcrumbs(n);
    renderList(n.data);
    loadStatus();
    $('#search').placeholder =
      n.data.kind === 'root'
        ? 'Search universities…'
        : n.data.kind === 'lab'
          ? 'Search people, papers, or university labs…'
          : 'Search this university’s labs / PIs…';
    if (state.tab === 'trends') await renderTrends();
  } catch (error) {
    if (token === navigation)
      loadStatus('Could not load this selection. ' + error.message, () => select(id, animate));
  }
}

function goBack() {
  if (state.selected === 'root') {
    select('root');
    return;
  }
  const n = nodeById.get(state.selected);
  select(n?.parent?.data.id || 'root');
}

function breadcrumbs(n) {
  const box = $('#breadcrumb');
  box.replaceChildren();
  n.ancestors()
    .reverse()
    .forEach((v, i) => {
      if (i) box.append(el('span', '/'));
      const b = el('button', v.data.kind === 'root' ? 'World' : v.data.name);
      b.onclick = () => select(v.data.id);
      box.append(b);
    });
  $('#back').disabled = n.depth === 0;
}

async function setTab(tab) {
  if (!['atlas', 'trends', 'coverage'].includes(tab)) tab = 'atlas';
  state.tab = tab;
  history.replaceState(
    null,
    '',
    tab === 'coverage' ? '#coverage' : location.pathname + location.search,
  );
  document
    .querySelectorAll('.tab')
    .forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.panel').forEach((p) => (p.hidden = p.id !== tab + '-panel'));
  if (tab === 'trends') await renderTrends();
  if (tab === 'atlas' && currentView) drawCamera();
}

async function refresh() {
  const version = ++refreshVersion,
    token = ++navigation,
    selected = state.selected;
  try {
    if (!isDefaultScope() || state.sizing === 'works') {
      loadStatus('Loading summary statistics…');
      await ensureMetrics();
    }
    if (version !== refreshVersion || token !== navigation) return;
    hierarchy();
    setStats();
    await select(nodeById.has(selected) ? selected : 'root', false);
    $('#search-results').hidden = true;
  } catch (error) {
    if (version === refreshVersion)
      loadStatus('Could not update filters. ' + error.message, refresh);
  }
}

function initialPublicationView(search) {
  const view = new URLSearchParams(search).get('view');
  return ['strict', 'reviewed', 'combined'].includes(view) ? view : 'combined';
}
