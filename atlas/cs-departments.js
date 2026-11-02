(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (s) =>
    String(s ?? '').replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
    );
  const fmt = (n) => Number(n || 0).toLocaleString('en-US');
  const YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
  const IDENT = {
    dblp_person_page_doi: 'PI’s DBLP page',
    dblp_person_page_title: 'PI’s DBLP page',
    dblp_verified_collection_work: 'PI’s verified work',
    anchored_author_id: 'PI’s OpenAlex author id',
    advisee_coauthor: 'advisee co-author',
    reviewed_openalex_author_id: 'PI’s reviewed OpenAlex author id',
    pi_orcid: 'PI’s ORCID',
    advisee_anchored_author_id: 'PI’s OpenAlex author id (seen with their advisees)',
    pi_institutional_publication_list: 'PI’s department publication list',
  };
  const PENDING_NAMES = { berkeley: 'UC Berkeley', stanford: 'Stanford' };
  // "PI labs with papers only" (owner decision 2026-10-22): a PI lab with zero lab papers stays in the school file but is
  // not listed here or in the atlas; data/cs-hierarchy/hidden-labs.json records why (scripts/build-cs-hierarchy.py).
  const hasPapers = (l) => l.papers.length > 0;
  const STUDENT_ROLES = new Set([
    'PhD student',
    'PhD alumnus',
    'Master’s',
    'Undergraduate',
    'Thesis student',
    'Student',
  ]);
  const params = new URLSearchParams(location.search);
  let index = null,
    data = null,
    state = {
      school: params.get('school'),
      dept: params.get('dept'),
      lab: params.get('lab'),
      q: '',
      filter: 'all',
    };
  const cache = {},
    abstractCache = new Map();
  let schoolRequest = 0;
  function abstractDisclosure(p, pi) {
    return p.abstractFile
      ? '<details data-abstract="' +
          pi +
          '"><summary>Abstract</summary><div class="csd-abstract"><p>Open to load the saved abstract.</p></div></details>'
      : '';
  }
  function bindAbstracts() {
    for (const el of $('csd-lab').querySelectorAll('[data-abstract]'))
      el.ontoggle = async () => {
        if (!el.open || el.dataset.loaded) return;
        const p = data.papers[Number(el.dataset.abstract)],
          file = p?.abstractFile;
        if (
          !/^data\/cs-abstracts\/(princeton|cmu|epfl|mit|berkeley|stanford)\.json\.gz$/.test(
            file || '',
          )
        )
          return;
        el.dataset.loaded = 'loading';
        const body = el.querySelector('.csd-abstract');
        body.textContent = 'Loading abstract…';
        try {
          if (!abstractCache.has(file))
            abstractCache.set(
              file,
              readResearchJSON(file).catch((e) => {
                abstractCache.delete(file);
                throw e;
              }),
            );
          const row = (await abstractCache.get(file))[p.abstractKey];
          if (!row?.abstract) throw Error('This abstract is unavailable.');
          body.innerHTML =
            '<p>' +
            esc(row.abstract) +
            '</p><p class="csd-ev"><a href="' +
            esc(p.oa) +
            '" target="_blank" rel="noopener">OpenAlex source ↗</a></p>';
          el.dataset.loaded = 'true';
        } catch (e) {
          delete el.dataset.loaded;
          body.textContent = e.message + ' Close and reopen to retry.';
        }
      };
  }

  function setURL() {
    const p = new URLSearchParams();
    if (state.school) p.set('school', state.school);
    if (state.dept) p.set('dept', state.dept);
    if (state.lab) p.set('lab', state.lab);
    history.replaceState(null, '', '?' + p.toString());
  }
  function fail(e) {
    $('csd-error').hidden = false;
    $('csd-error').textContent =
      'The CS department data could not load. ' + ((e && e.message) || e);
    $('csd-count').textContent = '';
  }
  async function loadSchool(id) {
    if (!cache[id]) cache[id] = await readResearchJSON('data/cs-hierarchy/' + id + '.json.gz');
    return cache[id];
  }
  function deptLabs(name) {
    const d = data.departments.find((x) => x.name === name);
    const own = (d ? d.labs : []).filter((i) => hasPapers(data.labs[i]));
    const joint = data.labs
      .map((l, i) => [l, i])
      .filter(([l, i]) => hasPapers(l) && l.dept !== name && (l.otherDepts || []).includes(name))
      .map(([l, i]) => i);
    return { own, joint };
  }
  function listedDepts() {
    return data.departments.filter((d) => {
      const { own, joint } = deptLabs(d.name);
      return own.length + joint.length > 0;
    });
  }
  function renderSchools() {
    const pend = (index.pending || [])
      .map(
        (id) =>
          '<button type="button" role="tab" disabled title="Being built">' +
          esc(PENDING_NAMES[id] || id) +
          ' · building</button>',
      )
      .join('');
    $('csd-schools').innerHTML =
      index.schools
        .map(
          (s) =>
            '<button type="button" role="tab" data-school="' +
            esc(s.id) +
            '" aria-selected="' +
            (s.id === state.school) +
            '">' +
            esc(s.name) +
            '</button>',
        )
        .join('') + pend;
    $('csd-schools')
      .querySelectorAll('[data-school]')
      .forEach((b) => (b.onclick = () => selectSchool(b.dataset.school)));
  }
  function renderStats() {
    const c = data.counts,
      shown = data.labs.filter(hasPapers),
      ids = new Set(shown.flatMap((l) => l.students.map((x) => x[0]))),
      ds = listedDepts(),
      full = ds.filter((d) => d.coverage === 'full').length;
    let students = 0,
      members = 0;
    for (const s of ids) STUDENT_ROLES.has(data.students[s].r) ? students++ : members++;
    $('csd-stats').innerHTML = [
      [
        full + (ds.length > full ? ' + ' + (ds.length - full) : ''),
        'departments (computing + home departments of listed PIs)',
      ],
      [shown.length, 'PI labs with lab papers'],
      [
        c.labs - shown.length,
        (c.labs - shown.length === 1 ? 'PI lab' : 'PI labs') + ' without lab papers · not listed',
      ],
      [shown.filter((l) => l.students.length).length, 'listed labs with students'],
      [c.labsComplete, 'labs with papers, students and links'],
      [
        fmt(c.papers) + ' / ' + fmt(students) + (members ? ' / ' + fmt(members) : ''),
        'papers / students' + (members ? ' / postdocs and other lab members' : ''),
      ],
    ]
      .map(
        ([n, t]) =>
          '<div><strong>' +
          esc(typeof n === 'number' ? fmt(n) : n) +
          '</strong><span>' +
          esc(t) +
          '</span></div>',
      )
      .join('');
  }
  function renderDepts() {
    $('csd-dept-list').innerHTML = [
      '<li><button type="button" data-dept="" aria-current="' +
        !state.dept +
        '">All departments<span>' +
        fmt(data.labs.filter(hasPapers).length) +
        '</span></button></li>',
    ]
      .concat(
        listedDepts().map((d) => {
          const { own, joint } = deptLabs(d.name);
          return (
            '<li><button type="button" data-dept="' +
            esc(d.name) +
            '" aria-current="' +
            (state.dept === d.name) +
            '">' +
            '<b style="font-weight:inherit">' +
            esc(d.name) +
            (d.coverage === 'full' ? '' : '<small>CS-related faculty only</small>') +
            '</b><span>' +
            fmt(own.length) +
            (joint.length ? ' +' + joint.length : '') +
            '</span></button></li>'
          );
        }),
      )
      .join('');
    $('csd-dept-list')
      .querySelectorAll('button')
      .forEach(
        (b) =>
          (b.onclick = () => {
            state.dept = b.dataset.dept || null;
            state.lab = null;
            $('csd-lab').hidden = true;
            setURL();
            renderDepts();
            renderRows();
          }),
      );
  }
  function matches(l, q) {
    if (!q) return 0;
    let n = 0;
    const has = (s) =>
      String(s || '')
        .toLowerCase()
        .includes(q);
    if (has(l.name) || has(l.pi.name)) n += 1;
    for (const s of l.students) if (has(data.students[s[0]].n)) n += 1;
    for (const p of l.papers) if (has(data.papers[p[0]].t)) n += 1;
    return n;
  }
  function rows() {
    let idx;
    if (state.dept) {
      const { own, joint } = deptLabs(state.dept);
      idx = own.concat(joint);
    } else idx = data.labs.map((_, i) => i);
    const q = state.q.trim().toLowerCase();
    let out = idx.map((i) => [i, data.labs[i]]).filter(([, l]) => hasPapers(l));
    if (state.filter === 'complete')
      out = out.filter(([i, l]) => l.papers.length && l.students.length && l.links.length);
    if (state.filter === 'nostudents') out = out.filter(([i, l]) => !l.students.length);
    if (q.length >= 2) out = out.map(([i, l]) => [i, l, matches(l, q)]).filter((x) => x[2] > 0);
    return out.sort((a, b) => a[1].pi.name.localeCompare(b[1].pi.name));
  }
  function renderRows() {
    const r = rows();
    $('csd-count').textContent =
      fmt(r.length) +
      ' lab' +
      (r.length === 1 ? '' : 's') +
      (state.dept ? ' in ' + state.dept : '') +
      (state.q.trim().length >= 2 ? ' matching “' + state.q.trim() + '”' : '');
    $('csd-rows').innerHTML =
      r
        .map(([i, l, m]) => {
          const joint = state.dept && l.dept !== state.dept;
          const z = (n) => (n ? fmt(n) : '<span class="zero">0</span>');
          return (
            '<tr data-i="' +
            i +
            '" tabindex="0" aria-selected="' +
            (state.lab === l.id) +
            '"><td><b>' +
            esc(l.name) +
            '</b>' +
            (joint ? '<span class="csd-tag">joint · ' + esc(l.dept) + '</span>' : '') +
            (state.dept ? '' : '<span class="csd-tag">' + esc(l.dept) + '</span>') +
            (!l.students.length ? '<span class="csd-tag warn">no students yet</span>' : '') +
            '<small>' +
            esc(l.pi.name) +
            (l.pi.title ? ' · ' + esc(l.pi.title) : '') +
            (m && state.q.trim().length >= 2 ? ' · ' + m + ' match' + (m === 1 ? '' : 'es') : '') +
            '</small></td><td class="num">' +
            z(l.papers.length) +
            '</td><td class="num">' +
            z(l.students.length) +
            '</td><td class="num">' +
            z(l.links.length) +
            '</td></tr>'
          );
        })
        .join('') || '<tr><td colspan="4" class="empty">No labs.</td></tr>';
    $('csd-rows')
      .querySelectorAll('tr[data-i]')
      .forEach((tr) => {
        const open = () => openLab(+tr.dataset.i);
        tr.onclick = open;
        tr.onkeydown = (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            open();
          }
        };
      });
  }
  function paperLink(p) {
    const u = p.doi ? 'https://doi.org/' + p.doi : p.u || p.oa;
    return (
      '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(p.t || '(untitled)') + '</a>'
    );
  }
  function openLab(i, scroll = true) {
    const l = data.labs[i];
    if (!l || !hasPapers(l)) {
      state.lab = null;
      setURL();
      $('csd-lab').hidden = true;
      return;
    }
    state.lab = l.id;
    setURL();
    $('csd-rows')
      .querySelectorAll('tr[data-i]')
      .forEach((tr) => tr.setAttribute('aria-selected', String(+tr.dataset.i === i)));
    const byPaper = new Map(),
      bySt = new Map();
    for (const [s, p, st] of l.links) {
      if (!byPaper.has(p)) byPaper.set(p, []);
      byPaper.get(p).push([s, st]);
      bySt.set(s, (bySt.get(s) || 0) + 1);
    }
    const listed = new Set(l.listings.map((x) => x.y));
    const periods = l.periods
      .map(
        (p) =>
          '<div><b>' +
          esc(p.start || '?') +
          '–' +
          esc(p.end || 'present') +
          '</b>' +
          (p.ev || [])
            .slice(0, 1)
            .map(
              (e) =>
                '<p class="csd-ev"><q>' +
                esc(e.quote) +
                '</q> · <a href="' +
                esc(e.url) +
                '" target="_blank" rel="noopener">source</a></p>',
            )
            .join('') +
          '</div>',
      )
      .join('');
    const years =
      '<div class="csd-years">' +
      YEARS.map((y) => {
        const x = l.listings.find((z) => z.y === y);
        return x
          ? '<a class="on" href="' +
              esc(x.url) +
              '" target="_blank" rel="noopener" title="' +
              esc(x.quote) +
              '"><span class="on">' +
              y +
              '</span></a>'
          : '<span>' + y + '</span>';
      }).join('') +
      '</div>';
    const studs = l.students
      .map(([s, rel, yrs, url]) => [s, rel, yrs, url, bySt.get(s) || 0])
      .sort((a, b) => b[4] - a[4] || data.students[a[0]].n.localeCompare(data.students[b[0]].n));
    let filterStudent = null,
      shown = 60;
    const sideHTML = () =>
      '<div class="csd-side"><h3 style="margin-top:0">PI</h3><p style="color:var(--ink);margin:0"><b>' +
      esc(l.pi.name) +
      '</b>' +
      (l.pi.title ? '<br>' + esc(l.pi.title) : '') +
      '</p>' +
      (l.otherDepts && l.otherDepts.length
        ? '<p class="csd-ev">Also in ' + esc(l.otherDepts.join(', ')) + '</p>'
        : '') +
      (l.pi.dblp && l.pi.dblp.length
        ? '<p class="csd-ev"><a href="' +
          esc(l.pi.dblp[0]) +
          '" target="_blank" rel="noopener">DBLP</a></p>'
        : '') +
      '<h3>Appointment</h3>' +
      (periods || '<p class="csd-ev">No reviewed faculty period.</p>') +
      '<p class="csd-ev">Department listings by year (each proves that year only):</p>' +
      years +
      // The CS atlas shows this PI lab (or says why not) under the same id (scripts/cs_scope.py atlas_lab_ids).
      '<p><a href="./?university=' +
      esc(data.school.uni) +
      '&amp;lab=' +
      encodeURIComponent(l.id) +
      '">Open in the CS atlas →</a></p>' +
      (l.url
        ? '<p><a href="' + esc(l.url) + '" target="_blank" rel="noopener">Lab page</a></p>'
        : '') +
      '<h3>Students and lab members (' +
      fmt(studs.length) +
      ')</h3>' +
      (studs.length
        ? '<table><thead><tr><th>Name</th><th>Role</th><th class="num">Papers</th></tr></thead><tbody>' +
          studs
            .map(([s, rel, yrs, url, n]) => {
              const st = data.students[s];
              return (
                '<tr><td><button type="button" class="text-button" style="margin:0;padding:0;text-align:left;font-size:12px;color:var(--ink)" data-st="' +
                s +
                '" aria-pressed="' +
                (filterStudent === s) +
                '">' +
                esc(st.n) +
                '</button><small>' +
                (rel === 'member' ? 'lab member' : 'advisee') +
                (yrs ? ' · ' + yrs[0] + (yrs[1] !== yrs[0] ? '–' + yrs[1] : '') : '') +
                (url
                  ? ' · <a href="' + esc(url) + '" target="_blank" rel="noopener">source</a>'
                  : '') +
                '</small></td><td>' +
                esc(st.r) +
                '</td><td class="num">' +
                (n ? fmt(n) : '<span class="zero">0</span>') +
                '</td></tr>'
              );
            })
            .join('') +
          '</tbody></table>'
        : '<p class="csd-ev">No stated advisees or members yet.</p>') +
      '</div>';
    const papersHTML = () => {
      let ps = l.papers
        .slice()
        .sort((a, b) =>
          String(data.papers[b[0]].d || data.papers[b[0]].y).localeCompare(
            String(data.papers[a[0]].d || data.papers[a[0]].y),
          ),
        );
      if (filterStudent !== null)
        ps = ps.filter((p) => (byPaper.get(p[0]) || []).some(([s]) => s === filterStudent));
      const total = ps.length;
      ps = ps.slice(0, shown);
      return (
        '<h3>Lab papers (' +
        fmt(total) +
        (filterStudent !== null
          ? ' with ' +
            esc(data.students[filterStudent].n) +
            ' · <button type="button" class="text-button" id="csd-clear" style="margin:0">show all</button>'
          : '') +
        ')</h3>' +
        (total
          ? '<ul class="csd-papers">' +
            ps
              .map(([pi, ident, ap]) => {
                const p = data.papers[pi];
                const st = byPaper.get(pi) || [];
                return (
                  '<li>' +
                  paperLink(p) +
                  '<small>' +
                  esc(p.y || '') +
                  (p.v ? ' · ' + esc(p.v) : '') +
                  ' · identity: ' +
                  esc(IDENT[ident] || ident) +
                  ' · appointment: ' +
                  (ap === 'P' ? 'faculty period' : 'listing ' + esc(ap.slice(1))) +
                  '</small><small>' +
                  esc((p.b || []).join(', ')) +
                  (p.nb > (p.b || []).length ? ' … (' + p.nb + ' authors)' : '') +
                  '</small>' +
                  st
                    .map(
                      ([s, k]) =>
                        '<span class="csd-chip' +
                        (k === 'c' ? ' c' : '') +
                        '" title="' +
                        (k === 'c'
                          ? 'candidate: supported name match on this lab paper’s byline'
                          : 'recorded authorship') +
                        '">' +
                        esc(data.students[s].n) +
                        '</span>',
                    )
                    .join('') +
                  '<div data-reader="' +
                  pi +
                  '"></div>' +
                  abstractDisclosure(p, pi) +
                  '</li>'
                );
              })
              .join('') +
            '</ul>' +
            (total > shown
              ? '<button type="button" class="csd-more" id="csd-more">Show ' +
                fmt(Math.min(100, total - shown)) +
                ' more of ' +
                fmt(total - shown) +
                '</button>'
              : '')
          : l.gapNote
            ? '<p class="csd-ev"><b>Researched:</b> ' + esc(l.gapNote) + '</p>'
            : '<p class="csd-ev">No lab papers yet: none of the PI’s school-affiliated papers falls in a reviewed faculty period or a year with a captured department listing.</p>')
      );
    };
    const draw = () => {
      $('csd-lab').innerHTML =
        '<p class="eyebrow">' +
        esc(data.school.name) +
        ' · ' +
        esc(l.dept) +
        '</p><h2>' +
        esc(l.name) +
        '</h2><p>' +
        fmt(l.papers.length) +
        ' lab papers · ' +
        fmt(l.students.length) +
        ' students and members · ' +
        fmt(l.links.length) +
        ' student–paper links</p><div class="csd-lab-grid"><div id="csd-lab-papers">' +
        papersHTML() +
        '</div>' +
        sideHTML() +
        '</div>';
      $('csd-lab')
        .querySelectorAll('[data-st]')
        .forEach(
          (b) =>
            (b.onclick = () => {
              const s = +b.dataset.st;
              filterStudent = filterStudent === s ? null : s;
              shown = 60;
              draw();
            }),
        );
      if (window.PaperReader)
        $('csd-lab')
          .querySelectorAll('[data-reader]')
          .forEach((box) => {
            const p = data.papers[+box.dataset.reader];
            PaperReader.append(box, {
              id: p.w || p.oa,
              aliases: [p.atlasId, p.oa].filter(Boolean),
              title: p.t,
              doi: p.doi,
            });
          });
      bindAbstracts();
      const more = $('csd-more');
      if (more)
        more.onclick = () => {
          shown += 100;
          draw();
        };
      const clr = $('csd-clear');
      if (clr)
        clr.onclick = () => {
          filterStudent = null;
          draw();
        };
    };
    $('csd-lab').hidden = false;
    draw();
    if (scroll) $('csd-lab').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  async function selectSchool(id) {
    const request = ++schoolRequest;
    if (state.school !== id) {
      state.dept = null;
      state.lab = null;
    }
    state.school = id;
    $('csd-lab').hidden = true;
    renderSchools();
    $('csd-count').textContent = 'Loading ' + id + '…';
    try {
      const next = await loadSchool(id);
      if (request !== schoolRequest) return;
      data = next;
    } catch (e) {
      if (request === schoolRequest) fail(e);
      return;
    }
    $('csd-error').hidden = true;
    if (state.dept && !listedDepts().some((d) => d.name === state.dept)) state.dept = null;
    setURL();
    renderStats();
    renderDepts();
    renderRows();
    $('csd-foot').textContent =
      'Built ' +
      data.builtAt.slice(0, 10) +
      ' from the school’s faculty census, OpenAlex works with a school-affiliated authorship (2016–2026, at most 100 authors), DBLP person pages and the collection’s advising and authorship records. Rosters and listings do not establish continuous membership.';
    if (state.lab) {
      const i = data.labs.findIndex((l) => l.id === state.lab && hasPapers(l));
      if (i >= 0) openLab(i, false);
      else {
        const h = data.labs.find((l) => l.id === state.lab);
        state.lab = null;
        setURL();
        if (h)
          $('csd-count').textContent += ' · ' + h.name + ' is not listed: it has no lab papers.';
      }
    }
  }
  (async () => {
    try {
      index = await readResearchJSON('data/cs-hierarchy/index.json');
      if (!index.schools.some((s) => s.id === state.school)) state.school = index.schools[0].id;
      $('csd-search').oninput = (e) => {
        state.q = e.target.value;
        renderRows();
      };
      $('csd-filter').onchange = (e) => {
        state.filter = e.target.value;
        renderRows();
      };
      const lab = state.lab;
      await selectSchool(state.school);
      if (lab && !state.lab) {
        state.lab = null;
      }
      window.CSDepartments = { getData: () => data, getIndex: () => index, openLab };
    } catch (e) {
      fail(e);
    }
  })();
})();
