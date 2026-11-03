/* map: loaded before app.js; shared atlas state is initialized there. */
'use strict';
function renderLegend(papers) {
  const entries = papers
    ? [
        ...(labMap?.students.some((p) => p.isPI) ? [['PI / lab advisor', '#e8ba70']] : []),
        ['Researcher', '#c7a6f0'],
        ['Paper · open access', '#69cbb0'],
        ['Paper · other / unknown access', '#8daae4'],
        ['Verified authorship connection', '#dfccff'],
        ['Candidate / profile-listing connection', '#a89bc0'],
      ]
    : [
        ['Computer & information sciences', CS_COLORS.field],
        ['Computing department · other recorded field', CS_COLORS.department],
        [state.sizing === 'works' ? 'No linked works yet' : 'Inventory pending', ''],
      ];
  const box = $('#map-legend');
  box.replaceChildren();
  for (const [name, color] of entries) {
    const item = el('span'),
      swatch = el('i');
    if (name === 'Researcher') swatch.className = 'student-swatch';
    if (name.includes('connection'))
      swatch.className =
        'line-swatch' + (name.startsWith('Candidate') ? ' candidate-line-swatch' : '');
    if (color) swatch.style.background = color;
    else swatch.className = 'unknown';
    item.append(swatch, document.createTextNode(name));
    box.append(item);
  }
}

function workTree(selection) {
  const peers = (selection.children || []).filter(
      (n) => selection.data.kind !== 'department' || unitMatches(n.data.record),
    ),
    u =
      selection.data.kind === 'root'
        ? null
        : selection.data.kind === 'university'
          ? selection.data.record
          : selection.data.university;
  const ids = new Set(peers.map((n) => n.data.id));
  const labNodes = new Map(
    (selection.children || [])
      .filter((n) => n.data.kind === 'lab')
      .map((n) => [n.data.record.id, n.data.id]),
  );
  const peerFor = (m) =>
    selection.data.kind === 'root'
      ? [m.uni]
      : selection.data.kind === 'university'
        ? AtlasAffiliations.peers(m, u.id, labById)
        : [labNodes.get(m.lab) || m.lab];
  const totals = AtlasSizing.counts(
    u ? u.metrics : globalMetrics,
    (m) => peerFor(m).filter((id) => ids.has(id)),
    (m) => matches(m.field, m.status, m.uni) && (!u || labById.has(m.lab)),
    state.view,
    state.from,
    state.to,
  );
  const layout = AtlasSizing.layout(
    d3,
    peers.map((n) => ({
      id: n.data.id,
      count: totals.selected.get(n.data.id) || 0,
      reference: totals.reference.get(n.data.id) || 0,
    })),
  );
  const points = new Map(layout.points.map((p) => [p.id, p]));
  const root = d3.hierarchy({
    ...selection.data,
    children: peers.map((n) => ({
      ...n.data,
      children: undefined,
      unitCount:
        n.data.kind === 'university' ? n.data.known : AtlasAffiliations.uniqueLabs(n).length,
      workCount: points.get(n.data.id).count,
      noLinkedWorks: points.get(n.data.id).missing,
    })),
  });
  root.x = 350;
  root.y = 350;
  root.r = 350;
  for (const n of root.children || []) Object.assign(n, points.get(n.data.id));
  root.sizing = { mode: 'works', scale: layout.scale, maxReference: layout.maxReference };
  return root;
}

function unitTree(selection) {
  const peers = (selection.children || []).filter(
      (n) => selection.data.kind !== 'department' || unitMatches(n.data.record),
    ),
    counts = peers.map((n) => ({
      id: n.data.id,
      count: n.data.kind === 'university' ? n.data.known : AtlasAffiliations.uniqueLabs(n).length,
      reference:
        n.data.kind === 'university' ? n.data.known : AtlasAffiliations.uniqueLabs(n).length,
    }));
  const layout = AtlasSizing.layout(d3, counts),
    points = new Map(layout.points.map((p) => [p.id, p]));
  const root = d3.hierarchy({
    ...selection.data,
    children: peers.map((n) => ({
      ...n.data,
      children: undefined,
      unitCount: points.get(n.data.id).count,
    })),
  });
  root.x = 350;
  root.y = 350;
  root.r = 350;
  for (const n of root.children || []) Object.assign(n, points.get(n.data.id));
  root.sizing = { mode: 'units' };
  return root;
}

function renderSizeKey() {
  const box = $('#size-key'),
    svg = d3.select('#size-key-svg'),
    enabled = renderedSizing?.mode === 'works';
  box.hidden = !enabled;
  if (!enabled) return;
  const matrix = $('#map').getScreenCTM();
  if (!matrix) return;
  const pixels =
    ((renderedSizing.scale * 690) / currentView[2]) *
    camera.transform.k *
    Math.hypot(matrix.a, matrix.b);
  const cap = AtlasSizing.niceCount((31 / pixels) ** 2),
    caption = $('#size-key-caption');
  svg.selectAll('*').remove();
  if (cap < 1) {
    svg.attr('hidden', true);
    caption.textContent =
      'Area scale: 1 work has a diameter of ' +
      fmt(Math.round(pixels * 2)) +
      ' pixels at this zoom. Hollow circles: no linked works yet.';
    return;
  }
  svg.attr('hidden', null);
  const values = [...new Set([Math.max(1, AtlasSizing.niceCount(cap / 4)), cap])];
  values.forEach((value, i) => {
    const x = 58 + i * 126,
      r = Math.sqrt(value) * pixels;
    svg
      .append('circle')
      .attr('cx', x)
      .attr('cy', 35)
      .attr('r', r)
      .attr('fill', '#8baaaa22')
      .attr('stroke', '#b1c9cc')
      .attr('data-count', value);
    svg
      .append('text')
      .attr('x', x)
      .attr('y', 84)
      .attr('text-anchor', 'middle')
      .text(fmt(value) + ' ' + (value === 1 ? 'work' : 'works'));
  });
  caption.textContent =
    'Area ∝ distinct works · hollow markers: no linked works yet. Scale stays fixed across years and publication views within this selection.';
}

function fill(n) {
  if (n.data.kind === 'pi') return '#e8ba70';
  if (n.data.kind === 'student') return '#c7a6f0';
  if (n.data.kind === 'paper') return n.data.record.oa ? '#69cbb0' : '#8daae4';
  if (n.data.kind === 'university' && !n.data.known) return '#30424f';
  if (n.data.kind === 'lab')
    return CSScope.reasonOf(n.data.record) === 'department'
      ? CS_COLORS.department
      : CS_COLORS.field;
  return CS_COLORS.field;
}

function cameraPoint(d) {
  const v = currentView,
    k = 690 / v[2],
    a = (camera.angle * Math.PI) / 180,
    x = (d.x - v[0]) * k,
    y = (d.y - v[1]) * k;
  return camera.transform.apply([
    500 + x * Math.cos(a) - y * Math.sin(a),
    365 + x * Math.sin(a) + y * Math.cos(a),
  ]);
}

function drawCamera() {
  if (!nodeLayer || !currentView) return;
  const t = camera.transform;
  nodeLayer.attr('transform', `${t.toString()} rotate(${camera.angle},500,365)`);
  nodeIcons
    ?.attr('display', (d) => (((d.r * 690) / currentView[2]) * t.k > 15 ? null : 'none'))
    .attr('transform', (d) => {
      const p = cameraPoint(d),
        offset =
          ((d.r * 690) / currentView[2]) * t.k > 25
            ? Math.min(22, ((d.r * 690) / currentView[2]) * t.k * 0.42)
            : 0;
      return `translate(${p[0] - 7},${p[1] - offset - 7})`;
    });
  labelCandidates
    .attr('display', (d) => (((d.r * 690) / currentView[2]) * t.k > 25 ? null : 'none'))
    .attr('transform', (d) => {
      const p = cameraPoint(d);
      return `translate(${p[0]},${p[1]})`;
    })
    .text((d) => shortName(d.data.name, ((d.r * 690) / currentView[2]) * t.k));
  labelCandidates
    .filter((d) => ((d.r * 690) / currentView[2]) * t.k > 25)
    .each(function (d) {
      const width = ((d.r * 690) / currentView[2]) * t.k * 1.65;
      let text = this.textContent;
      while (this.getComputedTextLength() > width && text.length > 1) {
        text = text.slice(0, -1);
        this.textContent = text + '…';
      }
    });
  $('#zoom-level').textContent = Math.round(t.k * 100) + '%';
  $('#rotation-level').textContent = camera.angle + '°';
  $('#zoom-in').disabled = t.k >= 24;
  $('#zoom-out').disabled = t.k <= 0.25;
  renderSizeKey();
}

function scheduleCamera() {
  if (!cameraFrame)
    cameraFrame = requestAnimationFrame(() => {
      cameraFrame = 0;
      drawCamera();
    });
}

function stopMapAnimation() {
  d3.select('#map').interrupt();
  $('#tooltip').hidden = true;
}

function zoomMap(factor) {
  stopMapAnimation();
  d3.select('#map').call(cameraZoom.scaleBy, factor, [500, 365]);
}

function rotateMap(degrees) {
  stopMapAnimation();
  const t = camera.transform,
    a = (degrees * Math.PI) / 180,
    center = t.apply([500, 365]),
    dx = center[0] - 500,
    dy = center[1] - 365;
  const next = [
    500 + dx * Math.cos(a) - dy * Math.sin(a),
    365 + dx * Math.sin(a) + dy * Math.cos(a),
  ];
  camera.angle = (camera.angle + degrees + 360) % 360;
  d3.select('#map').call(
    cameraZoom.transform,
    d3.zoomIdentity.translate(next[0] - 500 * t.k, next[1] - 365 * t.k).scale(t.k),
  );
}

function resetCamera() {
  stopMapAnimation();
  camera.angle = 0;
  currentView = [focus.x, focus.y, focus.r * 2 + 18];
  toView(currentView);
  d3.select('#map').call(cameraZoom.transform, d3.zoomIdentity);
}

function setupCamera() {
  const svg = d3.select('#map');
  cameraZoom = d3
    .zoom()
    .extent([
      [0, 0],
      [1000, 730],
    ])
    .scaleExtent([0.25, 24])
    .clickDistance(5)
    .on('start', (e) => {
      if (e.sourceEvent) {
        stopMapAnimation();
        svg.classed('is-dragging', true);
      }
    })
    .on('zoom', (e) => {
      camera.transform = e.transform;
      scheduleCamera();
    })
    .on('end', () => {
      svg.classed('is-dragging', false);
      drawCamera();
    });
  svg.call(cameraZoom).on('dblclick.zoom', null);
  $('#zoom-in').onclick = () => zoomMap(1.4);
  $('#zoom-out').onclick = () => zoomMap(1 / 1.4);
  $('#rotate-left').onclick = () => rotateMap(-15);
  $('#rotate-right').onclick = () => rotateMap(15);
  $('#reset-view').onclick = resetCamera;
  svg.on('keydown.camera', (e) => {
    let handled = true;
    if (['+', '='].includes(e.key)) zoomMap(1.4);
    else if (e.key === '-') zoomMap(1 / 1.4);
    else if (e.key === '[') rotateMap(-15);
    else if (e.key === ']') rotateMap(15);
    else if (e.key === '0') resetCamera();
    else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
      stopMapAnimation();
      const dx = e.key === 'ArrowLeft' ? 50 : e.key === 'ArrowRight' ? -50 : 0,
        dy = e.key === 'ArrowUp' ? 50 : e.key === 'ArrowDown' ? -50 : 0;
      svg.call(cameraZoom.translateBy, dx / camera.transform.k, dy / camera.transform.k);
    } else handled = false;
    if (handled) e.preventDefault();
  });
}

function toView(v) {
  const k = 690 / v[2];
  currentView = v;
  nodes
    .attr('transform', (d) => `translate(${500 + (d.x - v[0]) * k},${365 + (d.y - v[1]) * k})`)
    .attr('r', (d) => Math.max(0, d.r * k));
  authorshipLines
    ?.attr('x1', (d) => 500 + (d.source.x - v[0]) * k)
    .attr('y1', (d) => 365 + (d.source.y - v[1]) * k)
    .attr('x2', (d) => 500 + (d.target.x - v[0]) * k)
    .attr('y2', (d) => 365 + (d.target.y - v[1]) * k);
  drawCamera();
}

function paint(root, target, animate = false) {
  const svg = d3.select('#map'),
    wasAdjusted =
      camera.angle !== 0 ||
      camera.transform.k !== 1 ||
      camera.transform.x !== 0 ||
      camera.transform.y !== 0,
    preserveCamera =
      root.sizing?.mode === 'works' &&
      renderedSizing?.mode === 'works' &&
      focus?.data.id === root.data.id;
  renderedSizing = root.sizing || null;
  svg.interrupt();
  svg.selectAll('*').interrupt();
  svg.selectAll('*').remove();
  if (cameraFrame) {
    cancelAnimationFrame(cameraFrame);
    cameraFrame = 0;
  }
  if (!preserveCamera) {
    camera.transform = d3.zoomIdentity;
    camera.angle = 0;
  }
  svg.property('__zoom', camera.transform);
  const desc = root.descendants().filter((d) => d !== root);
  nodeLayer = svg.append('g').attr('class', 'map-nodes');
  const positions = new Map(desc.map((d) => [d.data.id, d]));
  authorshipLines = nodeLayer
    .append('g')
    .selectAll('line')
    .data(
      (root.connections || [])
        .filter((e) => positions.has(e.student) && positions.has(e.paper))
        .map((e) => ({ ...e, source: positions.get(e.student), target: positions.get(e.paper) })),
    )
    .join('line')
    .attr(
      'class',
      (e) => 'authorship-line' + (e.status === 'verified' ? '' : ' candidate-authorship-line'),
    )
    .attr('aria-label', LabMapRecords.connectionLabel);
  authorshipLines.append('title').text(LabMapRecords.connectionLabel);
  nodes = nodeLayer
    .selectAll('circle')
    .data(desc)
    .join('circle')
    .attr(
      'class',
      (d) =>
        'node' +
        (d.data.kind === 'pi' ? ' pi-node' : d.data.kind === 'student' ? ' student-node' : '') +
        (d.data.studentOnly ? ' student-paper' : '') +
        (d.data.noLinkedWorks ? ' no-linked-works' : ''),
    )
    .attr('data-work-count', (d) => d.data.workCount ?? null)
    .attr('data-node-id', (d) => d.data.id)
    .attr('data-kind', (d) => d.data.kind)
    .attr('data-unit-kind', (d) =>
      d.data.kind === 'lab' ? ResearchUnitKinds.get(d.data.record).key : null,
    )
    .attr('role', 'button')
    .attr('tabindex', 0)
    .attr(
      'aria-label',
      (d) => (d.data.kind === 'pi' ? 'PI / lab advisor' : d.data.kind) + ': ' + d.data.name,
    )
    .attr('fill', fill)
    .attr('fill-opacity', (d) =>
      d.children?.length ? 0.1 : d.data.kind === 'university' && !d.data.known ? 0.15 : 0.38,
    )
    .attr('stroke', fill)
    .attr('stroke-opacity', (d) => (d.data.kind === 'university' && !d.data.known ? 0.4 : 0.6))
    .attr('stroke-width', 0.7)
    .on('click', (event, d) => {
      if (event.defaultPrevented) return;
      event.stopPropagation();
      select(d.data.id);
    })
    .on('keydown', (event, d) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        event.stopPropagation();
        select(d.data.id);
      }
    })
    .on('mousemove', (event, d) => {
      if (!$('#map').classList.contains('is-dragging')) tooltip(event, d);
    })
    .on('mouseleave', () => ($('#tooltip').hidden = true));
  nodes
    .append('title')
    .text(
      (d) =>
        d.data.name +
        (d.data.workCount !== undefined
          ? ' · ' +
            fmt(d.data.workCount) +
            ' linked works' +
            (d.data.noLinkedWorks ? ' · No linked works yet' : '')
          : ''),
    );
  nodeIcons = svg
    .append('g')
    .attr('aria-hidden', 'true')
    .selectAll('path')
    .data(desc.filter((d) => ['student', 'pi', 'paper'].includes(d.data.kind)))
    .join('path')
    .attr('class', 'node-icon')
    .attr('d', (d) =>
      d.data.kind !== 'paper'
        ? 'M10,4a3,3 0 1,1 -6,0a3,3 0 1,1 6,0 M1,15v-2a6,6 0 0,1 12,0v2'
        : 'M3,0h7l4,4v12H3z M10,0v5h4 M6,8h5 M6,11h5',
    );
  labels = svg
    .append('g')
    .attr('class', 'map-labels')
    .selectAll('text')
    .data(desc)
    .join('text')
    .attr('class', 'node-label')
    .attr('display', 'none')
    .attr('font-size', (d) => (['paper', 'student', 'pi'].includes(d.data.kind) ? 10 : 12));
  focus = target || root;
  const view = [focus.x, focus.y, focus.r * 2 + 18];
  labelCandidates = labels.filter((d) => d.parent === focus);
  nodes.attr('display', (d) => (isWithin(d, focus) && d.depth <= focus.depth + 2 ? null : 'none'));
  if (animate && currentView && !wasAdjusted) {
    const start = currentView.slice();
    svg
      .transition()
      .duration(matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 500)
      .tween('zoom', () => {
        const interpolate = d3.interpolateZoom(start, view);
        return (t) => toView(interpolate(t));
      });
  } else toView(view);
  svg.on('click', (event) => {
    if (!event.defaultPrevented) goBack();
  });
}

function isWithin(n, parent) {
  let p = n;
  while (p) {
    if (p === parent) return true;
    p = p.parent;
  }
  return false;
}

function shortName(name, r) {
  const clean = name
    .replace(/^The /, '')
    .replace('University of ', '')
    .replace('University', 'Univ.')
    .replace('Swiss Federal Institute of Technology Lausanne', 'EPFL')
    .replace('Massachusetts Institute of Technology', 'MIT');
  const compact = clean.replace(/^(Department|School|Faculty) of /, '');
  const max = Math.max(3, Math.floor((r * 1.65) / 7));
  return compact.length > max ? compact.slice(0, max - 1) + '…' : compact;
}

function tooltip(event, d) {
  const tip = $('#tooltip');
  tip.replaceChildren(el('span', d.data.name));
  let sub = '';
  if (d.data.kind === 'university')
    sub = d.data.known
      ? `${fmt(d.data.known)} computer science labs with papers · ARWU ${d.data.record.rank}`
      : 'Inventory pending · number of labs unknown';
  else if (d.data.kind === 'department')
    sub = `${fmt(d.data.unitCount ?? d.leaves().length)} computer science labs`;
  else if (d.data.kind === 'lab') sub = `${fmt(labCount(d.data.record))} linked works in this view`;
  else if (['student', 'pi'].includes(d.data.kind))
    sub = d.data.memberships.map(AdvisorAttribution.contextLabel).join('; ');
  else if (d.data.kind === 'paper')
    sub = `${d.data.record.year} · ${d.data.studentOnly ? 'Researcher-linked work; check connection evidence' : d.data.record.journal || d.data.record.type}`;
  if (d.data.workCount !== undefined)
    sub +=
      ' · ' +
      fmt(d.data.workCount) +
      ' distinct linked works' +
      (d.data.noLinkedWorks ? ' · No linked works yet' : '');
  tip.append(el('small', sub));
  tip.hidden = false;
  const box = $('#map-wrap').getBoundingClientRect();
  tip.style.left = Math.min(event.clientX - box.left + 14, box.width - tip.offsetWidth - 10) + 'px';
  tip.style.top = Math.max(5, event.clientY - box.top - 45) + 'px';
}

function paperTree(lab) {
  const u = uniById.get(lab.uniId);
  labMap = LabMapRecords.collect(lab, accepted(lab), DATA.works, state.from, state.to, state.view);
  selectedMapRecord = null;
  mapRecords = new Map([...labMap.students, ...labMap.papers].map((d) => [d.id, d]));
  const children = [
    ...(state.labView !== 'papers' ? labMap.students : []),
    ...(state.labView !== 'students' ? labMap.papers : []),
  ];
  const root = d3.pack().size([700, 700]).padding(8)(
    d3
      .hierarchy({
        id: lab.id,
        name: lab.name,
        kind: 'lab',
        record: lab,
        university: u,
        value: children.length ? undefined : 1,
        children: children.length ? children : undefined,
      })
      .sum((d) => d.value || 0)
      .sort(
        (a, b) =>
          (a.data.kind === 'pi' ? -1 : a.data.kind === 'student' ? 0 : 1) -
            (b.data.kind === 'pi' ? -1 : b.data.kind === 'student' ? 0 : 1) ||
          (b.data.record?.year || 0) - (a.data.record?.year || 0) ||
          a.data.name.localeCompare(b.data.name),
      ),
  );
  root.connections = labMap.links;
  return root;
}

function highlightMap(id) {
  selectedMapRecord = id;
  const related = new Set([id]);
  for (const e of labMap?.links || [])
    if (e.student === id || e.paper === id) {
      related.add(e.student);
      related.add(e.paper);
    }
  nodes
    ?.classed('is-selected', (d) => d.data.id === id)
    .classed('is-related', (d) => id && related.has(d.data.id))
    .classed('is-muted', (d) => id && !related.has(d.data.id));
  nodeIcons?.classed('is-muted', (d) => id && !related.has(d.data.id));
  authorshipLines
    ?.classed('is-active', (e) => e.student === id || e.paper === id)
    .classed('is-muted', (e) => id && e.student !== id && e.paper !== id);
  $('#lab-map-clear').hidden = !id;
  $('#lab-map-selection').hidden = !id;
  if (id) {
    const record = mapRecords.get(id),
      linked = (labMap?.links || []).filter((e) => e.student === id || e.paper === id),
      verified = linked.filter((e) => e.status === 'verified').length;
    $('#lab-map-selection').textContent =
      record.name +
      ' · ' +
      fmt(verified) +
      ' verified authorship connections · ' +
      fmt(linked.length - verified) +
      ' candidate or profile-listing connections in the selected years.';
  }
}
