"""Local asset eligibility, independent of work identity, research scope and redistribution.

No network or store writes. XML must contain article text, not merely metadata or a
PMC availability notice. PDF checks reject positive document-type evidence; they
do not classify the underlying work. Results are cached only for unchanged files
(same path, size and mtime in nanoseconds), never by catalog status or pathname alone: in memory for this process
and, when the caller passes the store, in <store>/.copy-quality-cache.jsonl (2026-11-10: every loop restart re-hashed and
re-parsed every downloaded PDF - pdfinfo + pdftotext per work - and needed ~37 min before its first download; the cache makes a
restart read file metadata only). A cache line that does not parse or does not match is ignored; the file is never trusted
for a changed file. COPY_QUALITY_CACHE_DIR redirects the cache file (measurements in a throwaway directory).
"""
import hashlib, json, os, re, sqlite3, subprocess
from pathlib import Path

from lxml import etree as ET

PENDING = 'provider_link_only_review_pending'
_CACHE = {}
CACHE_NAME = '.copy-quality-cache.jsonl'
_TRANSIENT = {'pdf_parse_unconfirmed', 'asset_parse_unconfirmed', 'asset_changed_during_check'}   # never persisted: a retry may succeed
_PERSIST = {}   # cache file -> {key string: result}


def _cache_file(store):
    d = os.environ.get('COPY_QUALITY_CACHE_DIR') or store
    return Path(d) / CACHE_NAME if d else None


def _persist_key(path, st, kind):
    return json.dumps([str(path), st.st_size, st.st_mtime_ns, kind])


def _persist_get(store, key):
    f = _cache_file(store)
    if f is None:
        return None
    if f not in _PERSIST:
        got = {}
        try:
            with open(f, encoding='utf-8') as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                        got[d['k']] = d['v']
                    except (ValueError, KeyError, TypeError):
                        continue   # a torn or foreign line
        except OSError:
            pass
        _PERSIST[f] = got
    v = _PERSIST[f].get(key)
    return v if isinstance(v, dict) and 'ok' in v else None


def _persist_put(store, key, result):
    f = _cache_file(store)
    if f is None or result.get('reason') in _TRANSIENT:
        return
    _PERSIST.setdefault(f, {})[key] = result
    try:
        with open(f, 'a', encoding='utf-8') as fh:   # one short line; O_APPEND, so a reader never sees a half-written key
            fh.write(json.dumps(dict(k=key, v=result)) + '\n')
    except OSError:
        pass   # a read-only store: the in-process cache still works


def _local(e):
    return ET.QName(e).localname if isinstance(e.tag, str) else ''


def xml_quality(data):
    """JATS/TEI body evidence. A short complete letter can have a single paragraph."""
    try:
        root = ET.fromstring(data, ET.XMLParser(resolve_entities=False, no_network=True, load_dtd=False))
    except (ET.XMLSyntaxError, ValueError):
        return dict(ok=False, reason='xml_unparseable')
    if _local(root) not in {'article', 'TEI'}:
        return dict(ok=False, reason='xml_not_article')
    bodies = [e for e in root.iter() if _local(e) == 'body']
    if not bodies:
        return dict(ok=False, reason='xml_no_article_body')
    body = bodies[0]
    paragraphs = []
    notice = False
    for e in body.iter():
        if _local(e) not in {'p', 'paragraph'}:
            continue
        if any(_local(a) in {'abstract', 'ref-list', 'back'} for a in e.iterancestors()):
            continue
        text = ' '.join(' '.join(e.itertext()).split())
        if re.search(r'(?i)do not permit archiving in PMC|full text is available from the preprint server', text):
            notice = True
            continue
        if any(_local(a) == 'sec' and any(_local(t) == 'title' and ''.join(t.itertext()).strip().lower() in
                                        {'abstract', 'full text availability'} for t in a) for a in e.iterancestors()):
            continue
        if text:
            paragraphs.append(text)
    chars = sum(len(t) for t in paragraphs)
    return dict(ok=chars >= 200, reason=None if chars >= 200 else 'xml_rights_notice_only' if notice else 'xml_no_substantive_body',
                body_characters=chars, body_paragraphs=len(paragraphs), notice_present=notice)


def pdf_nonpaper_reason(frontmatter, metadata=''):
    """Positive asset-type evidence; never infer work eligibility from a failed asset."""
    slide_label = re.search(r'(?im)^Title:\s*(?:slides(?:\.[a-z]+)?|.*powerpoint presentation)\s*$', metadata)
    bullets = len(re.findall(r'(?m)^\s*[•●✔-]\s*\S', frontmatter))
    narrative = re.search(r'(?im)^\s*(?:abstract|(?:\d+\.?\s+)?introduction)\b', frontmatter)
    if not narrative and re.search(r'(?i)do not permit archiving in PMC', frontmatter):
        return 'pdf_rights_notice_only'
    if slide_label and bullets >= 2 and not narrative:
        return 'pdf_slide_deck'
    head = frontmatter[:1200]
    if re.search(r'(?im)^\s*(?:panel session\s*:|CHI\s+20\d\d\s+(?:Panel(?:\s*&\s*Roundtable Discussion)?|SIG)\b)', head):
        return 'pdf_event_description'
    if re.search(r'(?im)^\s*Panel\s*\n', head) and re.search(r'(?i)\b(?:CSCW|CHI|SIGCSE)\b', head):
        return 'pdf_event_description'
    return None


def file_quality(path, kind, store=None):
    """Check actual local bytes. No minimum PDF pagecount or length rejects short papers."""
    path = Path(path)
    if 'quarantine' in path.parts:
        return dict(ok=False, reason='asset_quarantined')
    try:
        st = path.stat()
        key = (str(path.resolve()), st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, kind)
    except OSError:
        return dict(ok=False, reason='asset_missing')
    if key in _CACHE:
        return _CACHE[key]
    pkey = _persist_key(path.resolve(), st, kind) if store or os.environ.get('COPY_QUALITY_CACHE_DIR') else None
    if pkey and (hit := _persist_get(store, pkey)) is not None:
        _CACHE[key] = hit
        return hit
    try:
        if kind == 'xml':
            data = path.read_bytes()
            result = dict(xml_quality(data), actual_sha256=hashlib.sha256(data).hexdigest(), actual_bytes=len(data))
        elif kind == 'pdf':
            digest = hashlib.sha256(); size = 0
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1048576), b''):
                    digest.update(block); size += len(block)
            info = subprocess.run(['pdfinfo', str(path)], capture_output=True, text=True, timeout=60)
            text = subprocess.run(['pdftotext', '-f', '1', '-l', '3', str(path), '-'], capture_output=True, text=True, timeout=60)
            reason = pdf_nonpaper_reason(text.stdout, info.stdout)
            if not reason and info.returncode == 0 and text.returncode == 0 and len(text.stdout.strip()) < 200:
                reason = 'pdf_no_substantive_text'
            result = dict(ok=not reason and info.returncode == 0 and text.returncode == 0,
                          reason=reason or ('pdf_parse_unconfirmed' if info.returncode or text.returncode else None),
                          actual_sha256=digest.hexdigest(), actual_bytes=size)
        else:
            result = dict(ok=False, reason='unsupported_asset_format')
    except (OSError, subprocess.TimeoutExpired):
        result = dict(ok=False, reason='asset_parse_unconfirmed')
    try:
        after = path.stat()
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns):
            return dict(ok=False, reason='asset_changed_during_check')
    except OSError:
        return dict(ok=False, reason='asset_changed_during_check')
    _CACHE[key] = result
    if pkey:
        _persist_put(store, pkey, result)
    return result


def catalog_copy(store, work, assets):
    """Return a qualifying asset and evidence; XML always uses its OWN fields.

    A stale PDF work row must neither hide a real XML asset nor qualify its stub.
    Identity and licensing are separate caller checks. Invalid assets do not hide
    a valid same-work alternative of the appropriate format.
    """
    kind = 'xml' if work.get('status') == 'fulltext_xml' else 'pdf'
    choices = [dict(a) for a in assets if a.get('kind') in {'xml', 'pdf'} and a.get('sha256') and a.get('identity_check') != PENDING]
    if work.get('sha256') and work.get('file_path') and work.get('identity_check') != PENDING:
        choices.append(dict(kind='pdf', path=work['file_path'], sha256=work['sha256'], bytes=work.get('byte_count'),
                            url=work.get('download_url'), identity_check=work.get('identity_check')))
    choices.sort(key=lambda a: a['kind'] != kind)
    failures = []
    for a in choices:
        if not a.get('path'):
            continue
        path = Path(a['path']); path = path if path.is_absolute() else Path(store) / path
        if not path.resolve().is_relative_to(Path(store).resolve()):
            failures.append('asset_outside_store'); continue
        q = file_quality(path, a['kind'], store)
        if q.get('ok') and (q['actual_sha256'] != a['sha256'] or q['actual_bytes'] != a.get('bytes')):
            q = dict(ok=False, reason='asset_integrity_mismatch')
        if q['ok']:
            return a, q
        failures.append(q['reason'])
    return None, dict(ok=False, reason=failures[0] if failures else 'asset_missing_or_identity_pending')


def catalog_status(db, store, wid, status):
    """Lazy accepted-candidate quality check; read-only indexed source lookups."""
    if status not in {'downloaded', 'fulltext_xml'}:
        return status, None
    cols = ('id', 'status', 'file_path', 'sha256', 'byte_count', 'download_url', 'identity_check')
    try:
        row = db.execute('select ' + ','.join(cols) + ' from works where id=?', (wid,)).fetchone()
    except sqlite3.OperationalError:
        return 'copy_quality_unconfirmed', 'asset_metadata_incomplete'
    if not row:
        return 'copy_quality_unconfirmed', 'asset_missing'
    work = dict(zip(cols, row))
    try:
        cols = ('kind', 'path', 'sha256', 'bytes', 'identity_check', 'url', 'version', 'license')
        assets = [dict(zip(cols, r)) for r in db.execute('select ' + ','.join(cols) + ' from assets where work_id=?', (wid,)).fetchall()]
    except sqlite3.OperationalError:
        # Old fixture/catalog schemas without assets still permit the PDF works row.
        assets = []
    asset, evidence = catalog_copy(store, work, assets)
    return (('fulltext_xml' if asset['kind'] == 'xml' else 'downloaded'), None) if asset else ('copy_quality_unconfirmed', evidence['reason'])
