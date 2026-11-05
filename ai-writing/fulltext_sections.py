"""Main body / references / appendix split of a stored paper copy (PDF or XML), for the two-condition full-text study.

Today's ai-writing/fulltext.sqlite body (vendored fulltext_store.sections) runs from the Introduction to the LAST References
heading of the first 60 pages: the appendix is dropped only when it follows the last References heading. This module
splits every copy the same way regardless of where the appendix sits:

  main        Introduction (else the abstract's end, else the start) -> the first of {appendix start, references start}
  references  the reference list (up to the next appendix heading, else to the end)
  appendix    all appendix material, before or after the references (several pieces are joined)

flags: appendix_found, appendix_position (before_refs | after_refs | split | None), appendix_rule (which heading rule
fired first), refs_found, intro_found, truncated (page / size cap hit), chars / words per part.

pdf: pdftotext without the 60-page cap (MAX_PAGES, 5-minute limit); xml: JATS <body>, <back><app-group>/<app>, <ref-list>;
TEI <body>, <div type="annex">, <div type="references"> / <listBibl>.

passages(): main passages are exactly what diversity/common.passages gives today for the main text (cap 100); appendix
passages are cut and capped separately, so the "main" condition is a subset of "main+appendix" (nothing rescored).

usage (pilot): fulltext_sections.py split <file> [pdf|xml]   prints the flags and the first words of each part
"""
import html
import re
import subprocess
import sys
from pathlib import Path

MAX_PAGES = 400
PDF_TIMEOUT = 300
MAIN_MAX = 300_000       # today's body cap, so main paragraphs stay comparable
APPX_MAX = 1_000_000

INTRO = re.compile(r'^[ \t]*(?:(?:1|I)[.:]?[ \t]+)?(?:INTRODUCTION|Introduction|I NTRODUCTION)[ \t]*$', re.M)
TOC = re.compile(r'(?:\. ){4,}|\.{6,}')
REFS = re.compile(r'^[ \t]*(?:\d+[.:]?[ \t]+)?(?:REFERENCES|References|BIBLIOGRAPHY|Bibliography|Literature Cited|LITERATURE CITED|'
                  r'Works Cited|WORKS CITED|References and Notes|REFERENCES AND NOTES|Reference List|R EFERENCES|B IBLIOGRAPHY)[ \t]*$', re.M)
ABS_END = re.compile(r'^[ \t]*(?:Keywords|KEYWORDS|Index Terms|CCS Concepts|ACM Reference Format)\b', re.M)
YEAR = re.compile(r'\b(?:19|20)\d\d\b')

# explicit appendix headings: the line is the heading (short, no sentence continuation)
_APPX_WORD = r'(?:APPENDI(?:X|CES)|Appendi(?:x|ces)|A PPENDI(?:X|CES))'
_SUPP = (r'(?:(?:S UPPLEMENTARY|ONLINE|TECHNICAL|SUPPLEMENTARY|SUPPLEMENTAL|ELECTRONIC SUPPLEMENTARY|Online|Technical|Supplementary|Supplemental|Electronic Supplementary)'
         r' (?:APPENDIX|APPENDICES|MATERIALS?|INFORMATION|DATA|FIGURES|TABLES|TEXT|NOTES|Appendix|Appendices|Materials?|Information|Data|Figures|Tables|Text|Notes):?(?: (?:for|to|of|FOR|TO|OF) [^\n.,;)]{3,80})?'
         r')')
APPX_WORDS = re.compile(
    r'^[ \t]*(?:(?:\d+|[A-Z])[.:]?[ \t]+)?(?:' + _APPX_WORD + r'(?:[ \t]+(?:[A-Z]|[IVX]{1,4}|\d{1,2}))?(?:[ \t]*[.:–—\-][ \t]*[A-Z][^\n.]{0,90}|[ \t]+[A-Z][A-Z0-9 ,\x27\-:]{3,90}|[ \t]*)'
    r'|' + _SUPP + r'(?:[ \t]*[:\u2013\u2014][ \t]*[A-Z][^\n.]{0,90})?)[ \t]*$', re.M)
# lettered top-level headings: "A  Proof of ...", "A. Additional results", "A" alone on a line + title line, "A.1 ..." subsections.
# A title is heading-like when it has <= 12 words and no comma or sentence end (reference entries have both).
_TITLE = r'[A-Z][A-Za-z0-9,;:\'\u2019()\-\u2013 /&+$\u2212]{3,85}'
HEAD_A = re.compile(r'^[ \t]*A(?:[.:][ \t]+|[ \t]{1,4})(' + _TITLE + r')[ \t]*$', re.M)
HEAD_A_ALONE = re.compile(r'^[ \t]*A[.:]?[ \t]*\n+[ \t]*(' + _TITLE + r')[ \t]*$', re.M)
HEAD_A1 = re.compile(r'^[ \t]*A\.1[.:]?(?:[ \t]+[A-Z][^\n]{2,85})?[ \t]*$', re.M)
HEAD_B = re.compile(r'^[ \t]*B(?:[.:][ \t]+|[ \t]{1,4}|[ \t]*\n+[ \t]*)(' + _TITLE + r')[ \t]*$', re.M)
HEAD_B1 = re.compile(r'^[ \t]*B\.1[.:]?(?:[ \t]+[A-Z]|[ \t]*$)', re.M)
HEAD_A2 = re.compile(r'^[ \t]*A\.2[.:]?(?:[ \t]+[A-Z]|[ \t]*$)', re.M)
CONCL = re.compile(r'^[ \t]*(?:(?:\d+|[IVX]{1,4})[.:]?[ \t]+)?(?:CONCLUSIONS?|C ONCLUSIONS?|D ISCUSSION|A CKNOWLEDG[A-Z ]*|Conclusions?|DISCUSSION|Discussion|CONCLUDING REMARKS|Concluding [Rr]emarks|'
                   r'ACKNOWLEDG(?:E)?MENTS?|Acknowledg(?:e)?ments?|Limitations|LIMITATIONS|Broader [Ii]mpacts?|Ethics [Ss]tatement|'
                   r'(?:CONCLUSIONS?|Conclusions?) (?:AND|and) [A-Za-z]+(?: [A-Za-z]+)?|Summary and [A-Z][a-z]+(?: [A-Za-z]+)?|'
                   r'(?:Conclusions?|CONCLUSIONS?),? (?:Limitations|Future)[^\n]{0,40})[ \t]*$', re.M)


_SENTENCE = re.compile(r'\b(?:shows?|is|are|was|were|we|can|that|which|has|have|provides?|presents?|describes?|gives?|contains?)\b|^(?:P ?REPRINT|PREPRINT)')


def _strict_title(title):
    """Heading-like: <= 12 words, no sentence end, at most two commas, no author initials ('J. Smith'), fewer than two numbers,
    no verb of running prose and not a running header ('A PREPRINT')."""
    return (len(title.split()) <= 12 and len(re.findall(r'(?<![A-Za-z])\d+(?![A-Za-z])', title)) < 2 and title.count(',') <= 2
            and not re.search(r'\.\s*$', title) and not re.search(r'\b[A-Z]\.|\.\s+[A-Z]', title) and not _SENTENCE.search(title))


def clean(t):
    t = t.replace('ﬁ', 'fi').replace('ﬂ', 'fl').replace('ﬀ', 'ff').replace('ﬃ', 'ffi').replace('ﬄ', 'ffl').replace('\x0c', '\n')
    return re.sub(r'-\n(?=[a-z])', '', t)


def flat(t):
    return ' '.join(t.split())


def _intro_start(t):
    m = next((x for x in INTRO.finditer(t, 0, min(len(t), 60000)) if not TOC.search(t, x.end(), x.end() + 400)), None)
    if m:
        return m.end(), True
    a = ABS_END.search(t, 0, min(len(t), 8000))
    return (a.start() if a else 0), False


def _refs_start(t, start):
    """First References heading after the Introduction whose next 2,500 characters look like a reference list (years, numbers
    or author-initial patterns); else today's rule (the last heading in the second half)."""
    cands = [x for x in REFS.finditer(t) if x.start() > start + 2000]
    for x in cands:
        seg = t[x.end():x.end() + 2500]
        if len(YEAR.findall(seg)) >= 4 or len(re.findall(r'^\s*\[\d+\]', seg, re.M)) >= 3 or len(re.findall(r'^\s*\d{1,3}\.\s+[A-Z]', seg, re.M)) >= 3:
            return x.start()
    late = [x for x in REFS.finditer(t) if x.start() > len(t) * 0.5]
    return late[-1].start() if late else None


_PROSE = re.compile(r'\b(?:the|of|and|to|we|is|in|for|that|this|are|with)\b')


def _lettered_appendix(t, start, refs):
    """Offset of a lettered top-level appendix ('A  Proof of ...', 'A' + title line, or the first 'A.1 ...' subsection) that follows
    the conclusion / acknowledgements or the references, with evidence of a sequence (a 'B ...' heading, 'B.1' or 'A.2')."""
    cl = [m.start() for m in CONCL.finditer(t, start + 2000) if refs is None or m.start() < refs]
    base = (cl[-1] if cl else None)
    if refs is not None:
        base = refs if base is None else min(base, refs)
    if base is None:
        return None
    cands = []
    for m in HEAD_A.finditer(t, base):
        if _strict_title(m.group(1)):
            cands.append(m.start())
    for m in HEAD_A_ALONE.finditer(t, base):
        if _strict_title(m.group(1)):
            cands.append(m.start())
    for m in HEAD_A1.finditer(t, base):
        prior = [c for c in cands if 0 < m.start() - c < 800]
        cands.append(prior[0] if prior else m.start())
    for c in sorted(set(cands)):
        if len(_PROSE.findall(t[c:c + 2000])) < 10:  # figure-panel labels and table cells are not followed by prose
            continue
        after = t[c + 120:c + 90000]  # a real section has text before the next lettered heading (figure panels A, B do not)
        seq = any(_strict_title(x.group(1)) for x in HEAD_B.finditer(after)) or HEAD_B1.search(after) or HEAD_A2.search(after)
        if seq:
            return c
    return None


def find_appendix_starts(t, start, refs):
    """[(offset, rule)] of the appendix heading(s) after `start`, earliest first (de-duplicated by 2,000 characters)."""
    hits = []
    for m in APPX_WORDS.finditer(t, start + 1500):
        line = m.group(0).strip()
        if TOC.search(line):
            continue
        # a table of contents or the running header: a heading directly followed by a dot leader or a page number only
        nxt = t[m.end():m.end() + 200]
        if TOC.search(nxt[:120]):
            continue
        if re.search(r'(?i)supplement', line) and re.search(r'(?i)online version contains|refer to web version|is available (?:online|free)|see supplementary|for supporting content|for this article can be found online|available (?:at|from) [^\n.]{0,40}online',
                                                         t[m.end():m.end() + 150]):
            continue  # a pointer to files hosted elsewhere, not material in this copy
        title = re.sub(r'^(?:(?:\d+|[A-Z])[.:]?\s+(?=[A-Za-z]))?[^A-Za-z]*(?:A PPENDI(?:X|CES)|APPENDI(?:X|CES)|Appendi(?:x|ces))\s*', '', line)
        title = re.sub(r'^(?:[A-Z]|[IVX]{1,4}|\d{1,2})(?:[.:]\s*|\s+|$)', '', title)  # the appendix letter
        if not _strict_title(title or 'Appendix'):
            continue
        hits.append((m.start(), 'supplementary' if re.search(r'(?i)supplement', line) and not re.search(r'(?i)appendi', line) else 'appendix'))
    lt = _lettered_appendix(t, start, refs)
    if lt is not None:
        hits.append((lt, 'lettered'))
    if any(h[1] == 'appendix' for h in hits):
        hits = [h for h in hits if h[1] != 'lettered']
    hits.sort()
    out = []
    for h in hits:
        if not out or h[0] - out[-1][0] > 2000:
            out.append(h)
    return out


_REFLIKE = re.compile(r'\b(?:19|20)\d\d\b')
_REFCUE = re.compile(r'et al\.?|pp?\.|doi|arXiv|Proc\.|Proceedings|Journal|Conference|vol\.|In:|IEEE|ACM', re.I)


def trim_ref_tail(text, chunk=500, min_run=4000):
    """No References heading: cut the trailing run of reference-like chunks (a year and a bibliographic cue in each) off `text`.
    Returns (text without the tail, tail)."""
    n = len(text)
    i, cut = n, n
    while i - chunk > n * 0.25:
        c = text[i - chunk:i]
        if _REFLIKE.search(c) and _REFCUE.search(c):
            cut = i - chunk
            i -= chunk
        else:
            break
    return (text[:cut], text[cut:]) if n - cut >= min_run else (text, '')


def split_text(t, kind='pdf'):
    """t: the document text (headings on their own lines). Returns dict(main, references, appendix, flags)."""
    t = clean(t)
    start, intro_found = _intro_start(t)
    refs = _refs_start(t, start)
    # an Appendix heading is only real when it is not inside the first stretch and not in the reference list proper; the
    # reference list may itself contain a line 'Appendix' only in odd cases, which the earliest-heading rule tolerates.
    app = find_appendix_starts(t, start, refs)
    # the lettered-heading rule is only trusted after a conclusion/reference; the word rule anywhere past the Introduction
    main_end = len(t)
    if refs is not None:
        main_end = refs
    pieces_app = []
    position = None
    ref_text = ''
    if app:
        a0 = app[0][0]
        if refs is None or a0 < refs:
            main_end = a0
            if refs is None:
                pieces_app.append(t[a0:])
                position = 'after_refs'  # no reference list found: everything after the heading is appendix
            else:
                pieces_app.append(t[a0:refs])
                position = 'before_refs'
                ref_end = len(t)
                later = [h for h in app if h[0] > refs]
                if later:
                    ref_end = later[0][0]
                    pieces_app.append(t[ref_end:])
                    position = 'split'
                ref_text = t[refs:ref_end]
        else:
            ref_text = t[refs:a0]
            pieces_app.append(t[a0:])
            position = 'after_refs'
    elif refs is not None:
        ref_text = t[refs:]
    main = t[start:main_end]
    appendix = '\n'.join(pieces_app)
    if refs is None:
        main, ref_text = trim_ref_tail(main)
        flags_extra = dict(refs_heuristic=bool(ref_text))
    else:
        flags_extra = {}
    flags = dict(appendix_found=bool(app), appendix_position=position, appendix_rule=app[0][1] if app else None,
                 refs_found=refs is not None or bool(ref_text), intro_found=intro_found, **flags_extra)
    return _finish(main, ref_text, appendix, flags)


MIN_APPX_WORDS = 100  # a heading with a pointer to files ('Supplementary Material' + a link) is a stub, not an appendix


def _finish(main, refs, appendix, flags):
    main_f, app_f = flat(main), flat(appendix)
    if flags.get('appendix_found') and len(app_f.split()) < MIN_APPX_WORDS:
        flags.update(appendix_found=False, appendix_position=None, appendix_stub=True)
        app_f = ''
    flags['truncated'] = bool(flags.get('truncated')) or len(main_f) > MAIN_MAX or len(app_f) > APPX_MAX
    out = dict(main=main_f[:MAIN_MAX], references=flat(refs), appendix=app_f[:APPX_MAX], flags=flags)
    flags['main_chars'], flags['appendix_chars'], flags['references_chars'] = len(out['main']), len(out['appendix']), len(out['references'])
    flags['main_words'], flags['appendix_words'] = len(out['main'].split()), len(out['appendix'].split())
    return out


# ---------------------------------------------------------------- XML

def _xml_text(x):
    x = re.sub(r'<(?:title|head|label)[^>]*>(.*?)</(?:title|head|label)>', lambda m: '\n' + re.sub(r'<[^>]+>', '', m.group(1)).strip() + '\n', x, flags=re.S)
    x = re.sub(r'</(?:p|sec|div|app|ref|bibl|biblStruct)>', '\n', x)
    return html.unescape(re.sub(r'<[^>]+>', ' ', x))


def _grab(raw, tag, attr=None):
    """All top-level-ish <tag ...>...</tag> blocks (non-nested use: app, app-group)."""
    pat = rf'<{tag}\b[^>]*{attr or ""}[^>]*>.*?</{tag}>'
    return [m.group(0) for m in re.finditer(pat, raw, re.S)]


def split_xml(raw):
    b = re.search(r'<body[^>]*>(.*?)</body>', raw, re.S)
    body = b.group(1) if b else ''
    back = re.search(r'<back[^>]*>(.*)</back>', raw, re.S)
    back_raw = back.group(1) if back else ''
    app_blocks = _grab(back_raw, 'app-group') or _grab(back_raw, 'app') or _grab(back_raw, 'div', r'type="(?:annex|appendix)"')
    if not app_blocks:
        app_blocks = _grab(raw, 'app-group') or _grab(raw, 'div', r'type="(?:annex|appendix)"')
    # supplementary-material sections inside <body> or <back><sec>
    refs_blocks = _grab(back_raw, 'ref-list') or _grab(raw, 'ref-list') or _grab(back_raw, 'div', r'type="references"') or _grab(raw, 'listBibl')
    body_t = clean(_xml_text(body))
    start, intro_found = _intro_start(body_t)
    app = find_appendix_starts(body_t, start, None)
    appendix_parts, flags_pos = [], None
    main_t = body_t[start:]
    if app:
        main_t = body_t[start:app[0][0]]
        appendix_parts.append(body_t[app[0][0]:])
        flags_pos = 'before_refs'
    for blk in app_blocks:
        appendix_parts.append(clean(_xml_text(blk)))
    if app_blocks:
        i_app, i_ref = raw.find(app_blocks[0]), (raw.find(refs_blocks[0]) if refs_blocks else -1)
        pos = 'after_refs' if (i_ref >= 0 and i_app > i_ref) else 'before_refs'
        flags_pos = 'split' if (app and pos == 'after_refs') else (flags_pos or pos)
    ref_t = '\n'.join(clean(_xml_text(r)) for r in refs_blocks)
    flags = dict(appendix_found=bool(appendix_parts), appendix_position=flags_pos,
                 appendix_rule=('xml_back' if app_blocks else (app[0][1] if app else None)), refs_found=bool(refs_blocks),
                 intro_found=intro_found)
    return _finish(main_t, ref_t, '\n'.join(appendix_parts), flags)


# ---------------------------------------------------------------- driver

def read_pdf(path, max_pages=MAX_PAGES):
    r = subprocess.run(['pdftotext', '-q', '-l', str(max_pages), '-enc', 'UTF-8', str(path), '-'], capture_output=True, timeout=PDF_TIMEOUT)
    t = r.stdout.decode('utf-8', 'ignore')
    return t, t.count('\x0c')


def split_file(path, kind=None, max_pages=MAX_PAGES):
    """dict(main, references, appendix, flags) or dict(error=...). Never raises on a bad file."""
    path = Path(path)
    if not path.exists():
        return dict(error='missing')
    kind = kind or ('xml' if path.suffix.lower() in ('.xml', '.tei', '.nxml') else 'pdf')
    try:
        if kind == 'pdf':
            t, pages = read_pdf(path, max_pages)
            if len(t.strip()) < 500:
                return dict(error='no_text')
            s = split_text(t, 'pdf')
            s['flags']['pages'] = pages
            if pages >= max_pages:
                s['flags']['truncated'] = True
        else:
            raw = path.read_text('utf-8', 'ignore')
            s = split_xml(raw)
            if s['flags']['main_chars'] < 500 and not s['appendix']:
                return dict(error='no_text')
        s['flags']['kind'] = kind
        return s
    except subprocess.TimeoutExpired:
        return dict(error='timeout')
    except Exception as e:  # noqa: BLE001
        return dict(error=type(e).__name__)


# ---------------------------------------------------------------- passages (the same rule as diversity/common.passages)

def passages_tagged(main, appendix, passages, cap_main=100, cap_appendix=100):
    """[(section, passage)]: `passages` is diversity.common.passages (injected, numpy-only import in the caller)."""
    return [('main', p) for p in passages(main, cap=cap_main)] + [('appendix', p) for p in passages(appendix, cap=cap_appendix)]


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'split':
        r = split_file(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(r.get('flags') or r)
        for k in ('main', 'references', 'appendix'):
            print(k, '|', (r.get(k) or '')[:200].replace('\n', ' '))
