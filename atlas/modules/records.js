/* records: loaded before app.js; shared atlas state is initialized there. */
'use strict';
function row(label, value) {
  const r = el('div', undefined, 'detail-row');
  r.append(el('span', label), el('strong', String(value)));
  return r;
}

function setStats() {
  const n = countUnits(),
    named = countUnits(null, 'named'),
    verified = countUnits(null, 'verified'),
    hidden = hiddenNote(hiddenTotals());
  $('#s-unis').textContent = fmt(activeUniversities.length);
  $('#s-labs').textContent = fmt(n);
  $('#s-named').textContent = fmt(named);
  $('#s-active').textContent = fmt(countUnits(null, 'active'));
  $('#s-works').textContent = fmt(globalSummary().stats.works);
  $('#works-view-label').textContent =
    state.view === 'combined'
      ? 'accepted research works'
      : state.view === 'strict'
        ? 'works · PI last author only'
        : 'works · reviewed bibliography only';
  $('#leadership-note').textContent =
    fmt(named) +
    ' of ' +
    fmt(n) +
    ' computer science labs in the current filters have a recorded PI or leader name (' +
    (n ? (100 * named) / n : 0).toFixed(1) +
    '%). ' +
    fmt(verified) +
    ' have verified publication identities. Blank names are collection gaps.';
  const note = $('#hidden-note');
  if (note) {
    note.textContent = hidden ? hidden + '.' : '';
    note.hidden = !hidden;
  }
}

function unitBreakdown(box, labs) {
  const counts = new Map();
  labs.forEach((l) => {
    const type = ResearchUnitKinds.get(l);
    counts.set(type.label, (counts.get(type.label) || 0) + 1);
  });
  const section = el('div', undefined, 'unit-breakdown');
  for (const [label, n] of counts) section.append(row(label, n));
  box.append(section);
}

function studentDetail(box, d) {
  box.append(el('h2', d.record.name), el('p', d.lab.name));
  for (const [label, value] of AdvisorAttribution.personDetails(d.record))
    box.append(row(label, value));
  for (const m of d.memberships) {
    for (const [label, value] of AdvisorAttribution.contextDetails(m))
      box.append(row(label, value));
    if (m.degreeDate)
      box.append(
        row('Degree date', m.degreeDate),
        el('p', m.dateMeaning || 'Degree date; lab membership end is unresolved.'),
      );
    if (m.membershipObservedOn) box.append(row('Membership source date', m.membershipObservedOn));
    const proof = el('details', undefined, 'student-evidence');
    proof.append(el('summary', AdvisorAttribution.contextEvidenceLabel(m)));
    for (const e of m.evidence || []) {
      if (e.quote || e.excerpt) proof.append(el('blockquote', e.quote || e.excerpt));
      if (e.year) proof.append(el('p', 'Source year: ' + e.year));
      if (e.url) proof.append(safeLink(e.url, 'Relationship source ↗'));
    }
    box.append(proof);
  }
  if (d.record.profileUrl) box.append(safeLink(d.record.profileUrl, 'Researcher profile ↗'));

  if (d.record.personalWorkCount !== undefined)
    box.append(
      el(
        'p',
        fmt(d.record.personalWorkCount) +
          ' confirmed personal papers in 2016–2026. The lab map includes only papers that pass this lab’s PI authorship and date checks.',
      ),
    );
  const links = labMap.links.filter((e) => e.student === d.id);
  box.append(el('hr'), el('h3', 'Paper connections · ' + links.length));
  if (!links.length)
    box.append(
      el(
        'p',
        'No paper connections collected in these years. This does not mean the researcher has no publications.',
      ),
    );
  for (const e of links) {
    const paper = mapRecords.get(e.paper),
      b = el('button', paper.record.year + ' · ' + paper.name, 'student-work-button');
    b.onclick = () => select(e.paper);
    box.append(
      b,
      el(
        'p',
        LabMapRecords.connectionLabel(e) + ' · ' + LabMapRecords.period(e.authorship),
        'student-work-note',
      ),
    );
  }
  const b = el('button', '← Back to lab', 'aside-button');
  b.onclick = () => {
    highlightMap(null);
    detail(nodeById.get(state.selected).data);
  };
  box.append(b);
}

function paperStudents(box, d) {
  const links = labMap?.links.filter((e) => e.paper === d.id) || [];
  if (!links.length) return;
  box.append(el('hr'), el('h3', 'Researcher connections · ' + links.length));
  for (const e of links) {
    const person = mapRecords.get(e.student),
      b = el('button', person.name, 'student-work-button');
    b.onclick = () => select(e.student);
    box.append(
      b,
      el(
        'p',
        LabMapRecords.connectionLabel(e) + ' · ' + LabMapRecords.period(e.authorship),
        'student-work-note',
      ),
    );
    const proof = el('details', undefined, 'student-evidence');
    proof.append(
      el('summary', LabMapRecords.connectionLabel(e)),
      el('p', e.authorship.identityBasis || 'Source-backed connection'),
    );
    for (const source of (e.authorship.evidence || []).slice(0, 4))
      proof.append(safeLink(source.url, 'Authorship source ↗'), el('br'));
    box.append(proof);
  }
}

function detail(d) {
  const box = $('#detail');
  box.replaceChildren();
  box.append(
    el(
      'div',
      d.kind === 'root'
        ? 'RESEARCH ATLAS'
        : d.kind === 'department'
          ? 'DEPARTMENT / SCHOOL'
          : d.kind === 'paper'
            ? 'PUBLICATION'
            : d.kind === 'pi'
              ? 'PI / LAB ADVISOR'
              : d.kind === 'lab'
                ? ResearchUnitKinds.get(d.record).label.toUpperCase()
                : d.kind.toUpperCase(),
      'eyebrow',
    ),
  );
  if (['student', 'pi'].includes(d.kind)) {
    studentDetail(box, d);
    return;
  }
  if (d.kind === 'root') {
    const hidden = hiddenNote(hiddenTotals());
    box.append(
      el('h2', 'Computer science, worldwide.'),
      el(
        'p',
        'Follow the circles from university to computing department, lab, and publication. Each level brings the underlying sources into view.',
      ),
      el('hr'),
      row('Universities in view', activeUniversities.length),
      row('Computer science labs with papers', fmt(countUnits())),
      row('Publication-linked PI groups', globalSummary().stats.publishing),
      el('span', 'COLLECTION IN PROGRESS', 'pill'),
      el(
        'p',
        state.sizing === 'works'
          ? 'Circle area shows distinct linked works in the selected years and authorship view. Hollow markers mean no linked works yet in this selection. Collection coverage is uneven; these counts are observed lower bounds.'
          : 'Only computer science labs with papers are shown: at ' +
              piSchoolNames() +
              ' each CS faculty PI’s own lab, from the CS departments view; elsewhere the CS units with linked papers. Each lab counts equally; enclosing areas are approximate. Switch Bubble size to Linked works to compare collected output.',
      ),
    );
    if (hidden) box.append(el('p', hidden + '.', 'hidden-note'));
    const b = el('button', 'Explore labs with publication links →', 'aside-button');
    b.onclick = () => {
      const u = activeUniversities.find((u) => universitySummary(u).stats.works);
      if (u) select(u.id);
    };
    box.append(b);
    return;
  }
  if (d.kind === 'university') {
    const u = d.record,
      labs = relevantLabs(u),
      pi = !!u.csScope?.school,
      hidden = hiddenNote(u.csScope?.hidden || {}, true);
    box.append(
      el('h2', u.name),
      el('p', u.country + ' · ARWU ' + u.rank),
      el('hr'),
      row(pi ? 'PI labs with lab papers' : 'CS units with papers', fmt(labs.length)),
      pi
        ? row('PI labs in the CS departments view', fmt(u.csScope.piLabs))
        : row('CS units in the inventory', fmt(u.csScope.inScope)),
      row('Works in this view', fmt(scopeSummary(labs, u).stats.works)),
      row(
        'With PI / leader names',
        fmt(labs.filter((l) => l.pi).length) + ' / ' + fmt(labs.length),
      ),
      row('Publication identities verified', labs.filter((l) => l.pis.length).length),
      row('Collection', 'Partial / incomplete'),
    );
    if (hidden) box.append(el('p', hidden + '.', 'hidden-note'));
    if (pi)
      box.append(
        el(
          'p',
          'Each CS faculty PI’s own lab, from the CS departments view. A lab paper has the PI on the byline with a university affiliation, inside the PI’s appointment. Open a department to explore its labs, then a lab for its papers and students.',
        ),
        csDepartmentsLink(u),
      );
    else {
      box.append(
        row('Dated activity verified', labs.filter((l) => l.years.length).length),
        el('p', 'Open a department or research unit to explore its labs and publications.'),
      );
      const assigned = labs.filter((l) => l.department).length;
      box.append(
        row('With recorded department / school', fmt(assigned) + ' / ' + fmt(labs.length)),
      );
      if (assigned < labs.length)
        box.append(
          el(
            'p',
            fmt(labs.length - assigned) +
              ' units are shown directly under the university while we verify their department affiliations.',
          ),
        );
    }
    if (u.url) box.append(safeLink(u.url, 'University website ↗'));
    if (u.sweepReport && state.view === 'strict') {
      const b = el('button', 'Show reviewed lab publications', 'aside-button');
      b.onclick = async () => {
        state.view = 'combined';
        $('#view').value = 'combined';
        await refresh();
        await select(u.id, false);
      };
      box.append(b);
    }
    return;
  }
  if (d.kind === 'department') {
    const labs = departmentLabs(d),
      all = AtlasAffiliations.uniqueLabs(nodeById.get(d.id)),
      pi = !!d.university.csScope?.school;
    box.append(
      el('h2', d.name),
      el('p', d.university.name),
      el('hr'),
      row(
        pi
          ? 'PI labs with lab papers'
          : state.unitKind
            ? 'Units of selected type'
            : 'Research units & source contexts',
        labs.length,
      ),
      row('Linked works', scopeSummary(labs, d.university).stats.works),
    );
    if (state.unitKind) box.append(row('All inventoried units', all.length));
    if (pi) {
      box.append(
        el(
          'p',
          labs.some((l) => l.departmentCoverage === 'full')
            ? 'A computing department, covered in full: each faculty PI it lists has one lab, shown here when it has lab papers.'
            : 'Faculty of this department are listed when they work in computer science: their papers at the school are in CS venues (DBLP-indexed). The department is not covered in full.',
        ),
        csDepartmentsLink(d.university, '&dept=' + encodeURIComponent(d.name)),
      );
      return;
    }
    unitBreakdown(box, labs);
    box.append(
      el(
        'p',
        'Counts distinguish labs from centers and broader research communities. Units can have several affiliations and are counted once within this selection. Source labels remain visible on each record.',
      ),
    );
    return;
  }
  if (d.kind === 'lab' && d.record.hierarchy) {
    const l = d.record,
      u = d.university,
      inView = accepted(l).length;
    box.append(
      el('h2', l.name),
      el('p', u.name),
      el(
        'p',
        l.department +
          (l.departmentCoverage === 'full'
            ? ''
            : ' · home department of a PI the computing departments list'),
      ),
      el('hr'),
      row('PI', l.pi),
      row('In the CS atlas through', CS_REASON_LABELS[l.csScopeReason]),
      row('Lab papers · 2016–2026', fmt(l.labPapers)),
      row('Lab papers in this view', fmt(inView)),
      row('Students', fmt(l.students)),
      row(
        'Student–paper links',
        fmt(l.studentPaperLinks) + ' (' + fmt(l.verifiedStudentPaperLinks) + ' verified)',
      ),
    );
    if (l.otherDepartments?.length)
      box.append(el('p', 'Also listed by: ' + l.otherDepartments.join('; ')));
    const yrs = el('div', undefined, 'mini-years');
    for (let y = 2016; y <= 2026; y++) {
      const n = l.paperCounts.combined[y] || 0,
        x = el('span', String(y).slice(2), n ? 'yes' : '');
      x.title = y + ': ' + plural(n, 'lab paper', 'lab papers');
      yrs.append(x);
    }
    box.append(
      yrs,
      el(
        'p',
        'Filled years have lab papers. A lab paper has the PI on the byline, that authorship lists the university, and it falls in the PI’s reviewed faculty period or the year of a captured department listing. Students are stated advisees and members of the PI’s own unit.',
      ),
    );
    if (!inView)
      box.append(
        el(
          'p',
          state.view === 'combined'
            ? 'No lab papers in the selected years.'
            : 'Lab papers of the CS departments view appear in the All research publication view.',
        ),
      );
    box.append(csDepartmentsLink(u, '&lab=' + encodeURIComponent(l.hierarchy.id)));
    if (l.url) box.append(safeLink(l.url, 'Lab page ↗'), el('br'));
    for (const p of l.pis) box.append(safeLink(p.source, p.name + ' · DBLP identity ↗'), el('br'));
    return;
  }
  if (d.kind === 'lab') {
    const l = d.record,
      kind = ResearchUnitKinds.get(l);
    box.append(
      el('h2', l.name),
      el('p', d.university.name),
      ...(l.department ? [el('p', l.department)] : []),
      el('hr'),
      row('Unit type', kind.label),
      row('Discipline', labelField(l.field)),
      row(
        'In the CS atlas through',
        CS_REASON_LABELS[CSScope.reasonOf(l)] || 'Computer science scope',
      ),
      row(
        kind.key === 'adviser_group_listing'
          ? 'Source-listed advisor'
          : kind.key === 'pi_lab'
            ? 'PI'
            : kind.key === 'center_institute'
              ? 'Director / listed leaders'
              : 'PI / listed leaders',
        l.pi || 'Not yet identified',
      ),
      row(
        kind.key === 'adviser_group_listing' ? 'Source review' : 'Leadership review',
        LEADERSHIP_LABELS[l.leadershipStatus],
      ),
      row('Source-associated works in this view', accepted(l).length),
      row('Researcher records', LabMapRecords.roster(l).length || 'Coverage missing'),
      row(
        'Dated activity',
        l.years.length ? 'Supported in ' + l.years.join(', ') : 'Not yet verified',
      ),
    );
    box.append(
      el(
        'p',
        kind.note || 'Organization type checked against the linked source.',
        'unit-type-note',
      ),
    );
    if (kind.sourceUrl) box.append(safeLink(kind.sourceUrl, 'Unit type evidence ↗'));
    if (l.unitStatus)
      box.append(
        row(
          'Unit status',
          l.unitStatus.replaceAll('_', ' ') + (l.closedOn ? ' · ' + l.closedOn : ''),
        ),
        safeLink(l.statusSource || l.unitStatusSource, 'Status evidence ↗'),
      );
    if (l.researchSummary) box.append(el('p', l.researchSummary));
    if (l.departments?.length > 1)
      box.append(
        el('p', 'Also listed with: ' + l.departments.filter((x) => x !== l.department).join('; ')),
      );
    if (l.researchLinkCount || l.sweepReport) {
      box.append(
        row('Source-associated works', accepted(l).length),
        row('Candidate / profile-listing connections', labMap?.candidateCount || 0),
      );
    }
    if (
      state.view === 'strict' &&
      Object.values(l.paperCounts?.reviewed || {}).some((n) => n > 0)
    ) {
      const b = el('button', 'Show reviewed lab publications', 'aside-button');
      b.onclick = async () => {
        state.view = 'combined';
        $('#view').value = 'combined';
        const affiliationPath = state.selected;
        await refresh();
        await select(affiliationPath, false);
      };
      box.append(b);
    }
    const yrs = el('div', undefined, 'mini-years');
    for (let y = 2016; y <= 2026; y++) {
      const x = el('span', String(y).slice(2), l.years.includes(y) ? 'yes' : '');
      x.title = y + ': ' + (l.years.includes(y) ? 'Dated evidence' : 'Unknown activity');
      yrs.append(x);
    }
    box.append(yrs);
    box.append(
      el(
        'p',
        'Filled years have dated lab evidence. Empty years mean unknown activity. The year filter applies to publications.',
      ),
    );
    if (l.url) box.append(safeLink(l.url, 'Unit website ↗'), el('br'));
    box.append(safeLink(l.source, 'Official directory source ↗'));
    if (!l.department)
      box.append(
        el('p', 'Department affiliation is being checked. The university source is linked above.'),
      );
    if (l.departmentSource)
      box.append(el('br'), safeLink(l.departmentSource, 'Department affiliation evidence ↗'));
    if (l.leadership.length) {
      box.append(
        el('hr'),
        el(
          'span',
          kind.key === 'adviser_group_listing' ? 'SOURCE-LISTED ADVISOR' : 'SOURCED LEADERSHIP',
          'eyebrow',
        ),
      );
      l.leadership.forEach((p) => {
        box.append(el('p', p.name + ' · ' + p.role), safeLink(p.source, 'Leadership evidence ↗'));
      });
      box.append(
        el(
          'p',
          kind.key === 'adviser_group_listing'
            ? 'These records identify the source-listed advisor. They do not establish a separate laboratory or a continuous advising interval.'
            : 'These sources record listed leadership. Historical tenure and additional co-leaders still need review.',
        ),
      );
    } else if (l.pi && !l.pis.length && !l.leadershipHistory?.length) {
      box.append(
        el(
          'p',
          'A name is recorded, but its leadership role and publication identity still need review.',
        ),
      );
    }
    if (l.pis.length) {
      box.append(el('hr'));
      l.pis.forEach((p) =>
        box.append(safeLink(p.source, p.name + ' · identity evidence ↗'), el('br')),
      );
    }
    if (l.bibliographyUrls?.length) {
      box.append(el('hr'));
      l.bibliographyUrls
        .slice(0, 4)
        .forEach((url, i) =>
          box.append(safeLink(url, 'Research / bibliography source ' + (i + 1) + ' ↗'), el('br')),
        );
    }
    if (l.evidence.length) {
      box.append(el('hr'));
      l.evidence.slice(0, 3).forEach((e) => {
        box.append(
          el('p', e.start + ' · ' + labelField(e.type)),
          safeLink(e.url, 'Dated activity source ↗'),
        );
      });
    }
    if (!accepted(l).length)
      box.append(
        el(
          'p',
          'No accepted publication links in this view and date range. Publication collection or bibliography review may still be pending.',
        ),
      );
    return;
  }
  if (d.kind === 'paper') {
    const w = d.record;
    if (d.studentOnly)
      box.append(
        el(
          'p',
          'This work is linked through a researcher record. Read each connection’s verification status below. It is not counted as accepted lab output in this publication view.',
        ),
      );
    PaperReader.append(box, w);
    const piPaper = w.source === 'cs-departments';
    box.append(
      el('h2', w.title),
      el('p', w.journal || labelField(w.type)),
      el('hr'),
      row('Published', w.date || w.year),
      row('Authors', w.byline || w.authors || 'Unknown'),
      row(
        'Open access',
        w.oa === null ? 'Not established' : w.oa ? 'Yes' : 'No / not indexed as OA',
      ),
      row('Citations at collection', w.citations ?? 'Unknown'),
      row(
        'Retraction flagged',
        piPaper || w.retracted == null ? 'Not checked' : w.retracted ? 'Yes' : 'No flag in index',
      ),
      row(
        'View',
        piPaper && !d.studentOnly
          ? 'CS departments lab paper'
          : d.studentOnly
            ? 'Researcher-linked work · see connection evidence'
            : state.view === 'strict'
              ? 'PI last author'
              : state.view === 'combined'
                ? 'Strict + reviewed'
                : 'Reviewed bibliography',
      ),
      el(
        'p',
        d.edge?.reason?.includes(
          'reviewed_exact_lab_arxiv_bibliography_verified_PI_missing_affiliation',
        )
          ? 'Reviewed lab bibliography · verified PI'
          : d.edge?.reason || '',
      ),
    );
    if (
      d.edge?.reason?.includes(
        'reviewed_exact_lab_arxiv_bibliography_verified_PI_missing_affiliation',
      )
    )
      box.append(
        el(
          'p',
          'This exact arXiv preprint is listed in the lab bibliography and its complete author list matches a verified PI. Publication-time university affiliation is missing, so it is included through the reviewed bibliography rule. Historical lab tenure remains unknown.',
        ),
      );
    if (d.edge?.strict && !d.edge?.reviewed)
      box.append(
        el(
          'p',
          'Verified PI identity and university affiliation on this paper. Historical membership of the named lab may be unresolved.',
        ),
      );
    if (w.doi)
      box.append(
        safeLink(
          w.doi.startsWith('http') ? w.doi : 'https://doi.org/' + w.doi,
          'Read publication / DOI ↗',
        ),
        el('br'),
      );
    if (!w.doi && w.url) box.append(safeLink(w.url, 'Read publication ↗'), el('br'));
    if (w.openalex) box.append(safeLink(w.openalex, 'OpenAlex record ↗'));
    if (d.edge?.reviewSource)
      box.append(el('br'), safeLink(d.edge.reviewSource, 'Lab bibliography evidence ↗'));
    paperStudents(box, d);
    const b = el('button', '← Back to lab', 'aside-button');
    b.onclick = () => {
      highlightMap(null);
      detail(nodeById.get(state.selected).data);
    };
    box.append(b);
  }
}

function renderList(d) {
  let headers, data, title, caption;
  if (d.kind === 'root') {
    const hidden = hiddenNote(hiddenTotals());
    headers = [
      'University',
      'Country / region',
      'ARWU',
      'CS labs shown',
      'Not shown',
      'Linked works',
    ];
    data = activeUniversities.map((u) => ({
      id: u.id,
      values: [
        u.name,
        u.country,
        u.rank,
        fmt(countUnits(u)),
        hiddenShort(u) || '—',
        fmt(universitySummary(u).stats.works),
      ],
    }));
    title = 'Universities';
    caption =
      'Universities with computer science labs that have papers; collection is incomplete.' +
      (hidden ? ' ' + hidden + '.' : '');
  } else if (d.kind === 'university') {
    const n = nodeById.get(d.id),
      children = n.children || [],
      direct = children.some((v) => v.data.kind === 'lab'),
      pi = !!d.record.csScope?.school,
      hidden = hiddenNote(d.record.csScope?.hidden || {}, true);
    headers = [
      'Department or research unit',
      'Type',
      pi ? 'PI labs' : 'Computer science units',
      'Linked works',
    ];
    data = children
      .slice()
      .sort(
        (a, b) =>
          (a.data.kind === 'department' ? 0 : 1) - (b.data.kind === 'department' ? 0 : 1) ||
          a.data.name.localeCompare(b.data.name),
      )
      .map((v) => ({
        id: v.data.id,
        values: [
          v.data.name,
          v.data.kind === 'department'
            ? pi
              ? AtlasAffiliations.uniqueLabs(v).some((l) => l.departmentCoverage === 'full')
                ? 'Computing department'
                : 'Home department of listed PIs'
              : 'Department / school'
            : ResearchUnitKinds.get(v.data.record).label,
          AtlasAffiliations.uniqueLabs(v).length,
          scopeSummary(AtlasAffiliations.uniqueLabs(v), d.record).stats.works,
        ],
      }));
    title = direct ? 'Departments & research units' : 'Departments & schools';
    caption = d.record.name + (hidden ? ' · ' + hidden : '');
  } else if (d.kind === 'department' && d.university.csScope?.school) {
    headers = ['PI lab', 'PI', 'Lab papers', 'Students', 'Student–paper links'];
    data = nodeById
      .get(d.id)
      .leaves()
      .filter((n) => unitMatches(n.data.record))
      .map((n) => {
        const l = n.data.record;
        return {
          id: n.data.id,
          values: [l.name, l.pi, labCount(l), l.students, l.studentPaperLinks],
        };
      });
    title = 'PI labs';
    caption = d.name + ' · lab papers in the selected years and publication view';
  } else if (d.kind === 'department') {
    headers = [
      'Research unit',
      'Unit type',
      'PI / listed leaders',
      'Leadership status',
      'Linked works',
    ];
    data = nodeById
      .get(d.id)
      .leaves()
      .filter((n) => unitMatches(n.data.record))
      .map((n) => ({
        id: n.data.id,
        values: [
          n.data.name,
          ResearchUnitKinds.get(n.data.record).label,
          n.data.record.pi || 'Not yet identified',
          LEADERSHIP_LABELS[n.data.record.leadershipStatus],
          labCount(n.data.record),
        ],
      }));
    title = 'Labs, centers & research groups';
    caption = d.name + ' · organization types and publication coverage';
  } else if (d.kind === 'lab') {
    headers = ['Researcher or publication', 'Kind', 'Date / roster status', 'Connection'];
    data = [];
    if (state.labView !== 'papers')
      for (const person of labMap.students)
        data.push({
          id: person.id,
          values: [
            person.name,
            person.isPI ? 'PI / lab advisor' : person.isStudent ? 'Student' : 'Researcher',
            person.memberships.map(AdvisorAttribution.contextLabel).join('; '),
            labMap.links.filter((e) => e.student === person.id && e.status === 'verified').length +
              ' verified · ' +
              labMap.links.filter((e) => e.student === person.id && e.status !== 'verified')
                .length +
              ' candidate / profile listing',
          ],
        });
    if (state.labView !== 'students')
      for (const paper of [...labMap.papers].sort((a, b) => b.record.year - a.record.year))
        data.push({
          id: paper.id,
          values: [
            paper.name,
            'Paper',
            paper.record.date || paper.record.year,
            paper.studentOnly
              ? 'Researcher connection · see verification status'
              : paper.edge?.library
                ? paper.edge.reason
                : 'Accepted lab publication',
          ],
        });
    title =
      state.labView === 'both'
        ? 'People + papers'
        : state.labView === 'students'
          ? 'People'
          : 'Papers';
    caption = 'Select a row or bubble to explore its evidence and connections.';
  } else return;
  $('#list-title').textContent = title;
  $('#list-caption').textContent = caption;
  $('#list-head').replaceChildren();
  const h = el('tr');
  headers.forEach((v) => h.append(el('th', v)));
  $('#list-head').append(h);
  const body = $('#list-body');
  body.replaceChildren();
  const pageSize = 20;
  state.page = Math.min(state.page, Math.max(0, Math.ceil(data.length / pageSize) - 1));
  data.slice(state.page * pageSize, (state.page + 1) * pageSize).forEach((r) => {
    const tr = el('tr');
    tr.dataset.id = r.id;
    tr.tabIndex = 0;
    tr.setAttribute('aria-label', 'Explore ' + r.values[0]);
    r.values.forEach((v, i) => {
      const td = el('td');
      if (headers[i] === 'Unit type') {
        td.className = 'unit-type-cell';
        td.append(el('span', String(v), 'unit-type-pill'));
      } else td.textContent = String(v);
      tr.append(td);
    });
    tr.onclick = () => select(r.id);
    tr.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        select(r.id);
      }
    };
    body.append(tr);
  });
  if (!data.length) {
    const tr = el('tr'),
      td = el('td', 'No records collected for this selection yet.', 'empty');
    td.colSpan = headers.length;
    tr.append(td);
    body.append(tr);
  }
  const pages = $('#list-pagination');
  pages.replaceChildren(
    el(
      'span',
      data.length
        ? `${state.page * pageSize + 1}–${Math.min((state.page + 1) * pageSize, data.length)} of ${fmt(data.length)}`
        : '0 collected records',
    ),
  );
  if (data.length > pageSize) {
    for (const [text, dir] of [
      ['←', -1],
      ['→', 1],
    ]) {
      const b = el('button', text);
      b.setAttribute('aria-label', dir < 0 ? 'Previous page' : 'Next page');
      b.disabled = state.page + dir < 0 || (state.page + dir) * pageSize >= data.length;
      b.onclick = () => {
        state.page += dir;
        renderList(d);
      };
      pages.append(b);
    }
  }
}

function search() {
  const q = $('#search').value.trim().toLowerCase(),
    box = $('#search-results');
  box.replaceChildren();
  box.hidden = !q;
  if (!q) return;
  const matches = [];
  for (const u of activeUniversities)
    if (u.name.toLowerCase().includes(q))
      matches.push({ id: u.id, title: u.name, sub: 'University · ' + u.country });
  const u = uniById.get(expandedUniversity);
  for (const lab of u ? relevantLabs(u) : []) {
    if ((lab.name + ' ' + lab.pi + ' ' + (lab.aliases || []).join(' ')).toLowerCase().includes(q))
      matches.push({
        id: lab.id,
        title: lab.name,
        sub: u.name + ' · ' + (lab.pi || lab.department || 'Research unit'),
      });
    if (lab.id === (labById.get(state.selected) || nodeById.get(state.selected)?.data.record)?.id)
      for (const edge of accepted(lab)) {
        const w = DATA.works[edge.work];
        if ((w.title + ' ' + (w.doi || '')).toLowerCase().includes(q))
          matches.push({
            id: state.selected,
            paper: w.id,
            title: w.title,
            sub: w.year + ' · ' + lab.name,
          });
      }
  }
  for (const person of labMap?.students || [])
    if (person.name.toLowerCase().includes(q))
      matches.push({
        id: state.selected,
        paper: person.id,
        title: person.name,
        sub:
          (person.isPI ? 'PI / lab advisor' : person.isStudent ? 'Student' : 'Researcher') +
          ' · ' +
          person.lab.name,
      });
  for (const paper of labMap?.papers.filter((p) => p.studentOnly) || [])
    if ((paper.name + ' ' + (paper.record.doi || '')).toLowerCase().includes(q))
      matches.push({
        id: state.selected,
        paper: paper.id,
        title: paper.name,
        sub: 'Researcher-linked work · ' + paper.record.year,
      });
  for (const r of matches.slice(0, 25)) {
    const b = el('button');
    b.append(el('span', r.title), el('small', r.sub));
    b.onclick = async () => {
      if (r.href) {
        location.href = r.href;
        return;
      }
      await setTab('atlas');
      await select(r.id, false);
      if (r.paper) await select(r.paper);
      box.hidden = true;
      $('#search').value = '';
    };
    box.append(b);
  }
  if (!matches.length)
    box.append(
      el(
        'div',
        u
          ? 'No computer science matches in this university.'
          : 'No matching universities with computer science units. Open a university to search its labs.',
        'empty',
      ),
    );
}

function chart(id, points, color) {
  const svg = d3.select(id);
  svg.selectAll('*').remove();
  const width = 560,
    height = 260,
    m = { l: 40, r: 14, t: 24, b: 34 },
    x = d3
      .scaleBand()
      .domain(points.map((p) => p.year))
      .range([m.l, width - m.r])
      .padding(0.36),
    max = d3.max(points, (p) => p.value) || 1,
    y = d3
      .scaleLinear()
      .domain([0, max])
      .nice()
      .range([height - m.b, m.t]);
  svg
    .append('g')
    .attr('class', 'chart-grid')
    .selectAll('line')
    .data(y.ticks(4).filter(Number.isInteger))
    .join('line')
    .attr('x1', m.l)
    .attr('x2', width - m.r)
    .attr('y1', (d) => y(d))
    .attr('y2', (d) => y(d));
  svg
    .append('g')
    .selectAll('text')
    .data(y.ticks(4).filter(Number.isInteger))
    .join('text')
    .attr('class', 'chart-label')
    .attr('x', m.l - 8)
    .attr('y', (d) => y(d) + 3)
    .attr('text-anchor', 'end')
    .text((d) => fmt(d));
  svg
    .append('g')
    .selectAll('rect')
    .data(points)
    .join('rect')
    .attr('x', (d) => x(d.year))
    .attr('y', (d) => y(d.value))
    .attr('width', x.bandwidth())
    .attr('height', (d) => height - m.b - y(d.value))
    .attr('fill', color)
    .attr('opacity', (d) => (d.year === 2026 ? 0.45 : 0.85))
    .attr('rx', 2)
    .append('title')
    .text((d) => d.year + ': ' + fmt(d.value) + (d.year === 2026 ? ' (partial year)' : ''));
  svg
    .append('g')
    .selectAll('text')
    .data(points)
    .join('text')
    .attr('class', 'chart-label')
    .attr('x', (d) => x(d.year) + x.bandwidth() / 2)
    .attr('y', height - 12)
    .attr('text-anchor', 'middle')
    .text((d) => String(d.year).slice(2) + (d.year === 2026 ? '*' : ''));
  svg
    .append('g')
    .selectAll('text')
    .data(points)
    .join('text')
    .attr('class', 'chart-label')
    .attr('x', (d) => x(d.year) + x.bandwidth() / 2)
    .attr('y', (d) => y(d.value) - 7)
    .attr('text-anchor', 'middle')
    .text((d) => d.value || '0');
}

async function renderTrends() {
  const token = navigation,
    selected = nodeById.get(state.selected),
    scoped = $('#use-map-scope').checked && selected && selected.data.kind !== 'root';
  let result;
  try {
    if (scoped) {
      const u =
          selected.data.kind === 'university' ? selected.data.record : selected.data.university,
        labs =
          selected.data.kind === 'department'
            ? departmentLabs(selected.data)
            : AtlasAffiliations.uniqueLabs(selected);
      result = scopeSummary(labs, u);
    } else if (isDefaultScope()) result = globalSummary();
    else {
      loadStatus('Loading summary statistics…');
      await ensureMetrics();
      if (token !== navigation) return;
      result = globalSummary();
      loadStatus();
    }
  } catch (error) {
    loadStatus('Could not load statistics. ' + error.message, renderTrends);
    return;
  }
  $('#trend-scope').textContent =
    (scoped ? selected.data.name : 'Computer science at all filtered universities') +
    ' · Observed counts in the selected years and publication view.';
  const { annual, stats: s } = result;
  chart(
    '#activity-chart',
    annual.map((d) => ({ year: d.year, value: d.activity })),
    '#4e9b83',
  );
  chart(
    '#papers-chart',
    annual.map((d) => ({ year: d.year, value: d.works })),
    '#678db4',
  );
  const body = $('#annual-body');
  body.replaceChildren();
  annual.forEach((a) => {
    const tr = el('tr');
    [
      a.year + (a.year === 2026 ? '*' : ''),
      fmt(a.activity),
      fmt(a.publishing),
      fmt(a.works),
      fmt(a.links),
      a.oa === null ? '—' : (100 * a.oa).toFixed(1) + '%',
    ].forEach((v) => tr.append(el('td', String(v))));
    body.append(tr);
  });
  const pct = (n) => (n === null ? '—' : (100 * n).toFixed(1) + '%'),
    fixed = (n, d) => (n === null ? '—' : n.toFixed(d));
  const cards = [
    ['Publishing PI groups', fmt(s.publishing)],
    ['Works / publishing group', s.publishing ? (s.groupLinks / s.publishing).toFixed(1) : '—'],
    ['Known open-access share', pct(s.oa)],
    ['Mean author team size', fixed(s.meanAuthors, 1)],
    ['Distinct indexed topics', fmt(s.topicCount)],
    ['Topic diversity · bits', fixed(s.entropy, 2)],
    ['Cross-country works', pct(s.international)],
    ['Lab-output concentration', fixed(s.hhi, 3)],
  ];
  const box = $('#metric-cards');
  box.replaceChildren();
  cards.forEach(([name, value]) => {
    const c = el('div');
    c.append(el('strong', value), el('span', name));
    box.append(c);
  });
}

function renderCoverage() {
  const s = DATA.csScope.summary,
    h = s.hidden,
    pi = s.byReason.cs_department_pi_lab;
  const cards = [
    ['Universities in the cohort', 300],
    ['Universities with CS labs shown', DATA.universities.length],
    ['Computer science labs shown', countUnits(null, 'n', true)],
    ['PI labs of the CS departments · ' + piSchoolNames(), pi],
    ['CS units with papers at other universities', countUnits(null, 'n', true) - pi],
    ['CS units without papers · not shown', h.no_papers],
    ['PI labs without lab papers · not shown', h.no_lab_papers],
    ['Earlier inventory units replaced by PI labs', h.replaced_by_pi_labs],
    ['Shown labs with dated activity', countUnits(null, 'active', true)],
    ['Shown labs with PI / leader names', countUnits(null, 'named', true)],
    ['Publication identities verified', countUnits(null, 'verified', true)],
    ['Complete university inventories', 0],
  ];
  const box = $('#coverage-cards');
  box.replaceChildren();
  cards.forEach(([name, value]) => {
    const c = el('div');
    c.append(el('strong', fmt(value)), el('span', name));
    box.append(c);
  });
  const body = $('#coverage-body');
  body.replaceChildren();
  allCSUniversities()
    .sort((a, b) => (a.rankLow || 999) - (b.rankLow || 999) || a.name.localeCompare(b.name))
    .forEach((u) => {
      const tr = el('tr'),
        shown = uniById.has(u.id),
        n = shown ? countUnits(u, 'n', true) : 0;
      [
        u.name,
        u.rank,
        fmt(n),
        hiddenShort(u) || '—',
        shown ? fmt(countUnits(u, 'active', true)) : '—',
        shown ? fmt(countUnits(u, 'named', true)) + ' / ' + fmt(n) : '—',
      ].forEach((v) => tr.append(el('td', String(v))));
      if (shown) {
        tr.dataset.id = u.id;
        tr.tabIndex = 0;
        tr.onclick = async () => {
          state.country = '';
          state.field = '';
          state.leadership = '';
          $('#country').value = '';
          $('#field').value = '';
          $('#leadership').value = '';
          await refresh();
          await setTab('atlas');
          await select(u.id, false);
        };
        tr.onkeydown = (e) => {
          if (e.key === 'Enter') tr.click();
        };
      } else tr.className = 'not-shown';
      body.append(tr);
    });
}
