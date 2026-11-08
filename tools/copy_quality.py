"""Local asset eligibility, independent of work identity, research scope and redistribution.

No network or store writes. XML must contain article text, not merely metadata or a
PMC availability notice. PDF checks reject positive document-type evidence; they
do not classify the underlying work. Results are cached only for unchanged files
within this process, never by catalog status or pathname alone.
"""
import hashlib, re, sqlite3, subprocess
from pathlib import Path

from lxml import etree as ET

PENDING = 'provider_link_only_review_pending'
_CACHE = {}


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


def file_quality(path, kind):
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
    try:
        if kind == 'xml':
            data = path.read_bytes()
            result = dict(xml_quality(data), actual_sha256=hashlib.sha256(data).hexdigest(), actual_bytes=len(data))
        elif kind == 'pdf':
            info = subprocess.run(['pdfinfo', str(path)], capture_output=True, text=True, timeout=60)
            text = subprocess.run(['pdftotext', '-f', '1', '-l', '3', str(path), '-'], capture_output=True, text=True, timeout=60)
            reason = pdf_nonpaper_reason(text.stdout, info.stdout)
            result = dict(ok=not reason and info.returncode == 0 and text.returncode == 0,
                          reason=reason or ('pdf_parse_unconfirmed' if info.returncode or text.returncode else None))
        else:
            result = dict(ok=False, reason='unsupported_asset_format')
    except (OSError, subprocess.TimeoutExpired):
        result = dict(ok=False, reason='asset_parse_unconfirmed')
    _CACHE[key] = result
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
        q = file_quality(path, a['kind'])
        if a['kind'] == 'xml' and q.get('ok') and (q['actual_sha256'] != a['sha256'] or q['actual_bytes'] != a.get('bytes')):
            q = dict(ok=False, reason='xml_asset_integrity_mismatch')
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
