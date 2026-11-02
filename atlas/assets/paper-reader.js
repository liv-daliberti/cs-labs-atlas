/* Release-approved hosted copies and verified links to the original source. */
'use strict';
window.PaperReader = (() => {
  let manifest,
    dialog,
    objectURL,
    request = 0;
  const make = (tag, text, cls) => {
    const e = document.createElement(tag);
    if (text) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };
  async function files() {
    if (!manifest)
      manifest = fetch('data/local-papers.json', { cache: 'no-cache' })
        .then((r) => {
          if (!r.ok) throw Error('Stored-paper index unavailable');
          return r.json();
        })
        .catch((e) => {
          manifest = null;
          throw e;
        });
    return manifest;
  }
  function fileFor(data, w) {
    const doi = String(w.doi || '')
      .replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '')
      .toLowerCase();
    const keys = [
      w.id,
      w.library?.id,
      w.canonicalGraphWorkId,
      ...(w.aliases || []),
      ...(w.library?.aliases || []),
      'doi:' + doi,
      w.arxiv ? 'arxiv:' + w.arxiv : null,
    ];
    for (const key of keys) {
      if (!key || !Object.hasOwn(data.works, key)) continue;
      const value = data.works[key],
        file = data.schema === 2 ? data.records[value] : value;
      if (file?.path || (file?.link && /^https?:\/\//i.test(file.sourceUrl))) return file;
    }
    return null;
  }
  async function verified(path, hash) {
    if (!/^papers\/[a-f0-9]{64}\.(?:pdf|txt|xml)$/.test(path)) throw Error('Invalid stored file');
    const r = await fetch(path, { cache: 'no-cache' });
    if (!r.ok) throw Error('Stored file could not load (' + r.status + ')');
    const bytes = await r.arrayBuffer();
    const digest = await crypto.subtle.digest('SHA-256', bytes),
      actual = [...new Uint8Array(digest)].map((n) => n.toString(16).padStart(2, '0')).join('');
    if (actual !== hash) throw Error('Stored file changed; reload this page');
    return bytes;
  }
  function close() {
    request++;
    dialog.close();
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = null;
    dialog.querySelectorAll('.reader-pages').forEach((x) => x.remove());
  }
  async function open(file, w) {
    if (!dialog) {
      dialog = make('dialog', null, 'paper-reader');
      dialog.setAttribute('aria-labelledby', 'paper-reader-title');
      document.body.append(dialog);
      dialog.addEventListener('cancel', (e) => {
        e.preventDefault();
        close();
      });
    }
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = null;
    const token = ++request;
    dialog.replaceChildren();
    const header = make('div', null, 'reader-header'),
      title = make('h2', w.title);
    title.id = 'paper-reader-title';
    const shut = make('button', 'Close reader ×');
    shut.onclick = close;
    header.append(title, shut);
    dialog.append(header);
    const provenance = make(
      'p',
      (file.version || 'Archived paper') +
        ' · ' +
        (file.pages ? file.pages + ' pages · ' : '') +
        'Stored full text',
    );
    const source = make('a', 'Original source ↗');
    if (/^https?:\/\//.test(file.sourceUrl)) {
      source.href = file.sourceUrl;
      source.target = '_blank';
      source.rel = 'noopener';
    }
    provenance.append(document.createTextNode(' · '), source);
    dialog.append(provenance);
    if (file.documentDoi) dialog.append(make('p', 'Stored document DOI: ' + file.documentDoi));
    if (file.versionNote) dialog.append(make('p', file.versionNote));
    if (file.license) dialog.append(make('p', 'License shown in the paper: ' + file.license));
    const toolbar = make('div', null, 'reader-toolbar'),
      pdfButton = make('button', 'Pages'),
      textButton = make('button', 'Text'),
      download = make('a', 'Download PDF');
    const zoom = make('select');
    zoom.setAttribute('aria-label', 'Page zoom');
    for (const [value, label] of [
      ['1', 'Fit page'],
      ['1.5', '150%'],
      ['2', '200%'],
      ['3', '300%'],
    ]) {
      const option = make('option', label);
      option.value = value;
      zoom.append(option);
    }
    toolbar.append(pdfButton, textButton, zoom, download);
    dialog.append(toolbar);
    const status = make('p', 'Loading stored paper…'),
      body = make('div', null, 'reader-body');
    status.setAttribute('role', 'status');
    dialog.append(status, body);
    dialog.showModal();
    shut.focus();
    try {
      const bytes = await verified(file.path, file.sha256);
      if (token !== request) return;
      if (new TextDecoder().decode(bytes.slice(0, 5)) !== '%PDF-')
        throw Error('Stored file is not a PDF');
      objectURL = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
      download.href = objectURL;
      download.download = (w.doi || 'paper').replace(/[^a-z0-9._-]/gi, '_') + '.pdf';
      const frame = make('div', null, 'reader-pages');
      frame.setAttribute('aria-label', 'Stored paper pages');
      for (const [i, page] of (file.pageImages || []).entries()) {
        if (!/^papers\/[a-f0-9]{64}\.jpg$/.test(page.path)) throw Error('Invalid paper page');
        const figure = make('figure', null, 'reader-page'),
          caption = make('figcaption', 'Page ' + (i + 1) + ' of ' + file.pages),
          img = make('img');
        img.alt = 'Page ' + (i + 1) + ' of ' + w.title;
        img.loading = i ? 'lazy' : 'eager';
        img.src = page.path;
        figure.append(caption, img);
        frame.append(figure);
      }
      const imagePages = !!file.pageImages?.length;
      if (!imagePages) {
        const embedded = make('iframe', null, 'reader-pdf-frame');
        embedded.title = 'Stored PDF: ' + w.title;
        embedded.src = objectURL;
        embedded.style.cssText = 'width:100%;height:72vh;border:0';
        frame.append(embedded);
      }
      body.append(frame);
      zoom.onchange = () =>
        frame.style.setProperty('--reader-page-width', Number(zoom.value) * 100 + '%');
      const text = make('pre', null, 'reader-text');
      text.hidden = true;
      body.append(text);
      let textLoaded = false;
      const show = async (mode) => {
        frame.hidden = mode !== 'pdf';
        zoom.hidden = mode !== 'pdf' || !imagePages;
        text.hidden = mode !== 'text';
        pdfButton.setAttribute('aria-pressed', String(mode === 'pdf'));
        textButton.setAttribute('aria-pressed', String(mode === 'text'));
        if (mode === 'text' && !textLoaded) {
          text.textContent = 'Loading extracted text…';
          try {
            const b = await verified(file.textPath, file.textSha256);
            if (token !== request) return;
            text.textContent = new TextDecoder().decode(b);
            textLoaded = true;
          } catch (e) {
            text.textContent = e.message;
          }
        }
      };
      pdfButton.onclick = () => show('pdf');
      textButton.onclick = () => show('text');
      textButton.disabled = !file.textPath;
      status.textContent = imagePages
        ? 'Zoom to enlarge the pages, or choose Text for easier reading on a small screen.'
        : 'Read the saved PDF below, or use Download PDF if this browser cannot display it.';
      await show('pdf');
    } catch (e) {
      if (token === request) {
        status.textContent = e.message;
        pdfButton.disabled = true;
        textButton.disabled = true;
        download.remove();
      }
    }
  }
  async function openXML(file, w) {
    if (!dialog) {
      dialog = make('dialog', null, 'paper-reader');
      dialog.setAttribute('aria-labelledby', 'paper-reader-title');
      document.body.append(dialog);
      dialog.addEventListener('cancel', (e) => {
        e.preventDefault();
        close();
      });
    }
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = null;
    const token = ++request;
    dialog.replaceChildren();
    const header = make('div', null, 'reader-header'),
      title = make('h2', w.title);
    title.id = 'paper-reader-title';
    const shut = make('button', 'Close reader ×');
    shut.onclick = close;
    header.append(title, shut);
    dialog.append(header);
    if (file.license) dialog.append(make('p', 'License: ' + file.license));
    const body = make('div', null, 'reader-body'),
      status = make('p', 'Loading stored full text…');
    status.setAttribute('role', 'status');
    dialog.append(status, body);
    dialog.showModal();
    shut.focus();
    try {
      const bytes = await verified(file.path, file.sha256);
      if (token !== request) return;
      const doc = new DOMParser().parseFromString(
        new TextDecoder().decode(bytes),
        'application/xml',
      );
      if (doc.querySelector('parsererror')) throw Error('Stored full text could not be parsed');
      const article = doc.querySelector('body') || doc.documentElement;
      for (const node of article.querySelectorAll('title,p')) {
        const text = node.textContent.trim();
        if (text) body.append(make(node.localName === 'title' ? 'h3' : 'p', text));
      }
      if (!body.childNodes.length) body.append(make('pre', article.textContent, 'reader-text'));
      status.textContent = 'Stored full text';
    } catch (e) {
      if (token === request) status.textContent = e.message;
    }
  }
  function append(box, w) {
    const holder = make('div', null, 'local-paper-access');
    box.append(holder);
    files()
      .then((data) => {
        if (!holder.isConnected) return;
        const file = fileFor(data, w);
        if (file?.link) {
          const b = make('a', 'Read at source ↗', 'aside-button read-local-paper');
          b.href = file.sourceUrl;
          b.target = '_blank';
          b.rel = 'noopener noreferrer';
          holder.append(b);
        } else if (file?.format === 'xml') {
          const b = make('button', 'Read here · stored full text', 'aside-button read-local-paper');
          b.onclick = () => openXML(file, w);
          holder.append(b);
        } else if (file) {
          const b = make('button', 'Read here · stored PDF', 'aside-button read-local-paper');
          b.onclick = () => open(file, w);
          holder.append(b);
        } else
          holder.append(
            make(
              'p',
              'No verified full-text link is available yet. Use the publication link below.',
            ),
          );
      })
      .catch(() => {
        if (holder.isConnected)
          holder.append(
            make('p', 'Paper availability could not load. The publication link remains available.'),
          );
      });
  }
  return { append, loadIndex: files, find: fileFor };
})();
