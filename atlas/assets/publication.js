/* Shared release provenance; this optional label never blocks the atlas. */
(() => {
  const target = document.querySelector('[data-publication]');
  if (!target) return;
  fetch('data/publication.json', { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error('Release label unavailable'); return r.json(); }).then(data => {
    const label = document.createElement('span');
    label.textContent = 'Release ' + data.release + ' · ' + data.coverage;
    target.append(label);
    const evidence = document.createElement('a'); evidence.href = 'data/publication.json'; evidence.textContent = 'Release details'; target.append(evidence);
  }).catch(() => { target.textContent = 'Incomplete research inventory · source evidence is shown with each record.'; });
})();
