"""WashU engineering Bulletin PDFs -> dated department faculty-listing entries (WashU deep dive, 2026-11-09).

The Bulletin's "Engineering & Applied Science" PDFs (bulletin.wustl.edu/about/prior/, robots-allowed path, already cached by school_web in the
`live` table of school-captures.sqlite and reviewed by tools/washu_bulletin_review.py) print each department's faculty section: a rank heading
(12 pt bold: "Professors", "Associate Professors", "Lecturers", "Professors Emeriti"), then one bold name per person, the endowed title, the
degree line ("PhD, University") and research interests. The document prints its own date "(10/04/16)", which is the observation date of the listing.

parse_pdf(raw) -> {dept: [entry]}; entry = name, section (the rank heading), titles, degree, profile (the printed engineering.wustl.edu profile
URL), quote (the lines from the name through the degree, a substring of the whitespace-collapsed section text) and the document's printed date.
Used by tools/listing_rows.py (bulletin-listing-sources.json), never by itself.
"""
import datetime as dt
import re

DEPARTMENTS = {'Computer Science & Engineering': 'CSE', 'Electrical & Systems Engineering': 'ESE', 'Biomedical Engineering': 'BME',
               'Mechanical Engineering & Materials Science': 'MEMS', 'Energy, Environmental & Chemical Engineering': 'EECE'}
DEGREE = re.compile(r'^(?:PhD|DSc|ScD|MD|MS|MA|MBA|MFA|JD|DPhil|DEng|PharmD|DrIng|Dr\.? ?rer\.? ?nat|BS|BA|MSc|MPH|DPT|DVM)\b')
TITLE_WORDS = re.compile(r'Professor|Chair|Dean|Director|Lecturer|Practice|Fellow|Head|Provost|Vice|Scientist', re.I)
URL_PART = re.compile(r'^\(?https?://|\.aspx\)?$|^Pages/|^\(?https?:')
FURNITURE = re.compile(r'^Bulletin \d{4}-\d\d\b|\(\d\d/\d\d/\d\d\)\s*$|^\d{1,3}$|^(?:Engineering & Applied Science|McKelvey School of Engineering)\b')
PRINTED = re.compile(r'\((\d\d/\d\d/\d\d)\)')


def heading_rank(h):
    """The rank a section heading gives (census rank vocabulary), and the singular title to attach."""
    t = h.lower()
    if 'emerit' in t:
        return 'emeritus', 'Professor Emeritus'
    if t.startswith('research') or 'research ' in t:
        return 'research', 'Research ' + re.sub(r'^research\s+', '', h).rstrip('s')
    if 'lecturer' in t:
        return 'lecturer', re.sub(r's$', '', h)
    if 'practice' in t or t.startswith('teaching'):
        return 'teaching', re.sub(r'^(Professors) of', 'Professor of', h)
    if t.startswith('senior professor') or t.startswith('senior and'):
        return 'other', 'Senior Professor'
    if 'professor' in t:
        return 'ladder', re.sub(r's$', '', h)
    if t in ('chair', 'associate chair'):
        return 'chair', h
    return 'other', h


def _lines(doc, first_page):
    """(text, size, bold) of every line from the page of the department's bookmark on, until the next large heading after 'Faculty'."""
    on = False
    for pno in range(first_page - 1, min(first_page + 7, len(doc))):
        for b in doc[pno].get_text('dict')['blocks']:
            for ln in b.get('lines', []):
                sp = ln['spans']
                text = ''.join(s['text'] for s in sp).strip()
                if not text:
                    continue
                size, bold = round(sp[0]['size']), bool(sp[0]['flags'] & 16)
                if not on:
                    on = text == 'Faculty' and size >= 14
                    continue
                if bold and size >= 14:
                    return
                yield text, size, bold, ''.join(s['text'] for s in sp if s['flags'] & 16).strip()


def parse_pdf(raw):
    import pymupdf
    out = {}
    with pymupdf.open(stream=raw, filetype='pdf') as doc:
        pages = [p.get_text() for p in doc]
        printed = {m for p in pages for m in PRINTED.findall(p[:300])}
        if len(printed) != 1:
            raise ValueError(f'expected one printed date, found {sorted(printed)}')
        printed = dt.datetime.strptime(printed.pop(), '%m/%d/%y').date().isoformat()
        for _, name, page in doc.get_toc():
            if name not in DEPARTMENTS:
                continue
            section = ' '.join('\n'.join(pages[page - 1:page + 7]).split())
            entries, heading, cur = [], None, None

            def close():
                nonlocal cur
                if cur and cur['degree']:
                    entries.append(cur)
                cur = None
            for text, size, bold, boldtext in _lines(doc, page):
                if FURNITURE.search(text) and (bold or re.match(r'^\d{1,3}$', text)):
                    continue
                if bold and size >= 12:
                    close()
                    heading = text
                    continue
                if bold and cur is None:
                    cur = dict(name=boldtext, section=heading, lines=[text], titles=[], degree=None, profile=text[len(boldtext):].strip().strip('()'))
                    continue
                if bold and cur is not None and cur['degree'] is None and len(cur['lines']) == 1 and not cur['titles']:
                    cur['name'] += ' ' + boldtext   # a long name wrapped onto a second bold line
                    cur['lines'].append(text)
                    continue
                if bold:
                    close()
                    cur = dict(name=boldtext, section=heading, lines=[text], titles=[], degree=None, profile=text[len(boldtext):].strip().strip('()'))
                    continue
                if cur is None or cur['degree'] is not None:
                    continue
                cur['lines'].append(text)
                if URL_PART.search(text):
                    cur['profile'] += text.strip('()')
                elif DEGREE.match(text):
                    cur['degree'] = text
                elif TITLE_WORDS.search(text) or (cur['titles'] and not cur['degree'] and len(cur['titles']) < 3 and not DEGREE.match(text)):
                    cur['titles'].append(text)
            close()
            res = []
            for e in entries:
                quote = ' '.join(' '.join(e['lines']).split())
                if quote not in section:
                    continue
                prof = re.sub(r'\s+', '', e['profile'])
                nm = re.sub(r'\s*\(?https?://.*$', '', ' '.join(e['name'].split()))
                if nm != ' '.join(e['name'].split()):   # the URL was set in the bold run: it is the profile, not the name
                    prof = re.sub(r'\s+', '', ' '.join(e['name'].split())[len(nm):] + e['profile']).strip('()')
                nm = re.sub(r'\s*\([^()]*\)$', '', nm)   # a joint-faculty entry names its home unit in brackets: 'Kenneth F. Kelton (Physics)'
                if len(nm.split()) < 2 or re.search(r'[)/0-9:.]\w*$|^\W', nm) and not re.search(r'\b[A-Z]\.$', nm):
                    continue   # a name broken by a wrapped profile URL ('Axelbaum.html)') is not a person
                res.append(dict(name=nm, section=e['section'], titles=[' '.join(t.split()) for t in e['titles']],
                                degree=e['degree'], profile=prof if prof.startswith('http') else '', quote=quote, printed=printed))
            out[DEPARTMENTS[name]] = res
    return out
