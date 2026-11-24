"""Optional exact-work primary-PDF authorship proofs for source-specific members.

A university-issued account identifies the author of one accepted work. It never
changes a member, infers a PI advising start, or creates a global author anchor.
"""
import calendar
import collections
import copy
import datetime
import hashlib
import json
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit, parse_qs

from bs4 import BeautifulSoup
from pathlib import Path

import atlas_paths as P
from schema_check import validate
from .common import ndoi
from .member_paper_reviews import digest, native_pi as base_native_pi, semantic

BASIS = 'reviewed_institutional_member_paper'
MARKER = 'institutionalAuthorshipReview'


def schema():
    return json.loads((Path(__file__).resolve().parents[2] / 'schemas' / 'student_authorship_review.schema.json').read_text())


def native_pi(ctx, pi):
    """Anticipate the same scientific PI augmentation as build.write, on a copy."""
    from . import census, match_ids
    result = base_native_pi(ctx, pi)
    match_ids.add([result], census.reviewed_name_pairs(ctx.school))
    return result


def scoped(row):
    return row.get('basis') == BASIS or MARKER in row


def norm(value):
    # Preserve the literal hyphen; only an actual PDF line break may join it.
    value = re.sub(r'(?<=\w)-[ \t]*\r?\n\s*(?=\w)', '-', unicodedata.normalize('NFKC', str(value)))
    return ' '.join(value.split()).casefold()


def bounds(value):
    if re.fullmatch(r'\d{4}', value):
        y = int(value)
        return datetime.date(y, 1, 1), datetime.date(y, 12, 31)
    if re.fullmatch(r'\d{4}-\d{2}', value):
        y, m = map(int, value.split('-'))
        return datetime.date(y, m, 1), datetime.date(y, m, calendar.monthrange(y, m)[1])
    day = datetime.date.fromisoformat(value)
    return day, day



def evidence_bytes(school, sha256, *, root=None):
    """Content-addressed original bytes, never an input-supplied filesystem path."""
    path = P.data('school-captures.sqlite', school, root=root).parent / 'source-evidence' / (sha256 + '.bin')
    return path.read_bytes() if path.exists() else None


def pi_identifier(pi, crsid):
    values = [(pi.get('lab') or {}).get('url') or '', (pi.get('piBasis') or {}).get('url') or '']
    return any(urlsplit(x).hostname in {'www.cl.cam.ac.uk', 'www.cst.cam.ac.uk'}
               and re.search(r'(?:/people/|/~)' + re.escape(crsid) + r'(?:/|$)', urlsplit(x).path) for x in values)



def has_name(quote, name):
    return bool(re.search(r"(?<![\w'-])" + re.escape(norm(name)) + r"(?![\w'-])", norm(quote)))


def starts_name(quote, name):
    return bool(re.match(re.escape(norm(name)) + r"(?![\w'-])", norm(quote)))


def mailbox_tokens(quote):
    local = r"A-Za-z0-9.!#$%&'*+/=?^_`{|}~\-"
    return [(m.group(1), m.start(1), m.end(1)) for m in re.finditer(
        r'(?<![' + local + r'])([' + local + r']+@(?:cl\.)?cam\.ac\.uk)(?![A-Za-z0-9.-])', quote)]


def mailboxes(quote):
    return [v for v, _, _ in mailbox_tokens(quote)]


def all_mailboxes(quote):
    local = r"A-Za-z0-9.!#$%&'*+/=?^_`{|}~\-"
    return re.findall(r'(?<![' + local + r'])([' + local + r']+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)', quote)


def named_author_clause(binding, original):
    """A whole semicolon-delimited clause in the actual publisher address block."""
    block = re.search(r"(?i)\bAuthors[’'] (?:addresses|Contact Information):", original)
    if not block:
        return False
    clauses = []
    for part in original[block.end():].split(';')[:-1]:
        if clauses and re.match(r'(?i)^\s*e-?mail\s*:', part):
            clauses[-1] += ';' + part
        else:
            clauses.append(part)
    return ' '.join(binding.split()) in [' '.join(c.split()) for c in clauses]


def doi_tokens(quote):
    out = []
    for match in re.finditer(r"(?i)(?<![A-Za-z0-9])10\.\d{4,9}/[^\s<>\"']+", quote):
        token = match[0].rstrip('.,;')
        for left, right in [('(',')'),('[',']'),('{','}')]:
            while token.endswith(right) and token.count(right) > token.count(left):
                token = token[:-1]
        out.append((token.casefold(), match.start(), match.start() + len(token)))
    return out


def printed_dois(quote):
    return {v for v, _, _ in doi_tokens(quote)}


def literal_occurrences(quote, original):
    """Replay complete edge words, not a clipped prefix of a different assertion."""
    quote = ' '.join(quote.split())
    if not quote:
        return []
    return [m.span() for m in re.finditer(re.escape(quote), original)
            if not (quote[0].isalnum() and m.start() and re.match(r"[\w'-]", original[m.start()-1]))
            and not (quote[-1].isalnum() and m.end() < len(original) and re.match(r"[\w'-]", original[m.end()]))]


def token_in_original(quote, original, wanted, lexer):
    """The whole actual-source token must lie inside the literal quoted occurrence."""
    return any(value == wanted and a <= start <= end <= b
               for a, b in literal_occurrences(quote, original)
               for value, start, end in lexer(original))


def stated_dates(quote):
    """Do not manufacture month/day precision from a year-only publisher assertion."""
    out = set(re.findall(r'(?<!\d)\d{4}(?:-\d{2}(?:-\d{2})?)?(?![\d-])', quote))
    for raw in re.findall(r'\b\d{1,2} [A-Za-z]{3,9} \d{4}\b', quote):
        for fmt in ['%d %b %Y','%d %B %Y']:
            try:
                out.add(datetime.datetime.strptime(raw, fmt).date().isoformat())
            except ValueError:
                pass
    for raw in re.findall(r'\b[A-Za-z]{3,9} \d{4}\b', quote):
        for fmt in ['%b %Y','%B %Y']:
            try:
                out.add(datetime.datetime.strptime(raw, fmt).strftime('%Y-%m'))
            except ValueError:
                pass
    return out


_PDF_TEXT = {}
_PDF_BOXES = {}

def original_pdf_text(school, pdf, *, root=None):
    raw = evidence_bytes(school, pdf['sha256'], root=root)
    if raw is None or len(raw) != pdf['bytes'] or hashlib.sha256(raw).hexdigest() != pdf['sha256']:
        return None
    if pdf['sha256'] not in _PDF_TEXT:
        try:
            parsed = subprocess.run(['pdftotext','-layout','-','-'], input=raw, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if parsed.returncode:
            return None
        _PDF_TEXT[pdf['sha256']] = parsed.stdout
    body = _PDF_TEXT[pdf['sha256']]
    if hashlib.sha256(body).hexdigest() != pdf['text_sha256']:
        return None
    text = body.decode('utf-8')
    return text if text.count('\f') == pdf['pages'] else None


def name_variant_ok(member_name, printed_name, kind='exact'):
    """Closed existing-rule spellings, backed independently by the exact own account."""
    from .names import given_conflict, initials_optional, one_edit
    if kind == 'exact':
        return norm(member_name) == norm(printed_name)
    def tokens(value):
        value = re.sub(r'\([^)]*\)', ' ', value)
        value = ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))
        return re.findall(r"[^\W_]+", value.casefold())
    a, b = tokens(member_name), tokens(printed_name)
    if min(len(a), len(b)) < 2 or min(len(a[0]), len(b[0]), len(a[-1]), len(b[-1])) < 2:
        return False
    if given_conflict([member_name], printed_name):
        return False
    if kind == 'latin_diacritics':
        return a == b
    if kind == 'single_edit_given':
        return a[1:] == b[1:] and min(len(a[0]), len(b[0])) >= 4 and one_edit(a[0], b[0])
    if kind == 'second_surname_omission':
        return a[0] == b[0] and initials_optional(member_name, printed_name)
    if kind == 'middle_names':
        if a[0] != b[0] or a[-1] != b[-1]:
            return False
        am, bm = a[1:-1], b[1:-1]
        ai, bi = {x for x in am if len(x)==1}, {x for x in bm if len(x)==1}
        af, bf = [x for x in am if len(x)>1], [x for x in bm if len(x)>1]
        if ai and bi and not (ai <= bi or bi <= ai):
            return False
        if ai and bf and not ai <= {x[0] for x in bf} or bi and af and not bi <= {x[0] for x in af}:
            return False
        def subsequence(short, long):
            it=iter(long)
            return all(any(x==y for y in it) for x in short)
        return subsequence(af,bf) or subsequence(bf,af)
    return False


def title_ok(proof, paper, actual_before_references):
    pdf=proof['pdf']
    if norm(pdf['title']) == norm(paper.get('title')):
        return proof.get('title_mapping','exact') == 'exact'
    short=norm(paper.get('title'))
    return (proof.get('title_mapping') == 'subtitle_expansion'
            and re.fullmatch(r'[a-z][a-z0-9-]{2,39}',short) is not None
            and norm(pdf['title']).startswith(short+': ')
            and printed_dois(actual_before_references) == {ndoi(paper.get('doi'))})


def article_page_text(proof, full_text):
    """Only the first article page, optionally after an explicit same-work ACM cover."""
    pdf=proof['pdf'];page=pdf.get('article_page',1);pages=full_text.split('\f')
    if page not in (1,2) or page>pdf['pages']:
        return None
    if page==2:
        cover=pdf.get('cover') or {};first=' '.join(pages[0].split())
        if (cover.get('kind')!='publisher_download_cover'
                or not all(literal_occurrences(cover.get(k,'x-not-a-cover'),first) for k in ['title_quote','identifier_quote','publisher_quote'])
                or norm(cover.get('title_quote'))!=norm(pdf['title'])
                or not token_in_original(cover.get('identifier_quote',''),first,pdf['doi'],doi_tokens)
                or not re.search(r'(?i)\bACM\b|dl\.acm\.org|Association for Computing Machinery',cover.get('publisher_quote',''))):
            return None
    return pages[page-1]


def original_pdf_boxes(school, pdf, *, root=None):
    """Coordinates are reparsed from hashed original PDF bytes, never supplied by input."""
    raw = evidence_bytes(school, pdf['sha256'], root=root)
    if raw is None or hashlib.sha256(raw).hexdigest() != pdf['sha256']:
        return None
    if pdf['sha256'] not in _PDF_BOXES:
        try:
            parsed = subprocess.run(['pdftotext', '-bbox', '-', '-'], input=raw, capture_output=True, timeout=60)
            if parsed.returncode:
                return None
            tree = ET.fromstring(parsed.stdout)
            _PDF_BOXES[pdf['sha256']] = [[dict(text=w.text or '', **{k:float(w.attrib[k]) for k in ['xMin','xMax','yMin','yMax']})
                                        for w in page.iter() if w.tag.rsplit('}',1)[-1]=='word']
                                       for page in tree.iter() if page.tag.rsplit('}',1)[-1]=='page']
        except (OSError, subprocess.TimeoutExpired, ET.ParseError, ValueError, KeyError):
            return None
    return _PDF_BOXES[pdf['sha256']]


def coordinate_columns(words, printed):
    """Complete same-row author columns, with boundaries derived from original words."""
    for top in sorted({w['yMin'] for w in words}):
        row = sorted([w for w in words if abs(w['yMin']-top)<3], key=lambda w:w['xMin'])
        spans=[]
        for name in printed:
            matches=[]
            for a in range(len(row)):
                for b in range(a+1,min(a+8,len(row))+1):
                    if norm(' '.join(w['text'] for w in row[a:b])).rstrip('*∗†‡,')==norm(name):
                        matches.append((row[a]['xMin'],row[b-1]['xMax']))
            if len(matches)!=1:break
            spans.append(matches[0])
        if len(spans)!=len(printed):continue
        if any(a[1]>=b[0] for a,b in zip(spans,spans[1:])):return None
        abstract=[w['yMin'] for w in words if norm(w['text'])=='abstract' and w['yMin']>top+3]
        emails=[w['yMax'] for w in words if all_mailboxes(w['text']) and top<w['yMin']<top+150]
        stop=min(abstract) if abstract else max(emails,default=top)+2
        if not top+5<stop<=top+150:return None
        centers=[(a+b)/2 for a,b in spans]
        cuts=[0]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[float('inf')]
        region=[w for w in words if top-1<=w['yMin'] and w['yMax']<stop]
        if any(any(w['xMin']<cut<w['xMax'] for cut in cuts[1:-1]) for w in region):return None
        columns=[' '.join(w['text'] for w in sorted(region,key=lambda w:(round(w['yMin']/3),w['xMin']))
                 if cuts[i]<=w['xMin'] and w['xMax']<=cuts[i+1]) for i in range(len(printed))]
        return columns if all(has_name(c,n) for c,n in zip(columns,printed)) else None
    return None


def author_columns(original, printed, words):
    """Bind the literal complete header and replay its independently parsed coordinates."""
    lines=original.splitlines()
    for row,line in enumerate(lines[:40]):
        matches=[re.search(r"(?<![\w'-])"+r'\s+'.join(map(re.escape,n.split()))+r"(?![\w'-])",line,re.I) for n in printed]
        if not all(matches):continue
        centers=[(m.start()+m.end())/2 for m in matches]
        if centers!=sorted(centers) or any(matches[i].end()>matches[i+1].start() for i in range(len(matches)-1)):return None
        stop=next((i for i in range(row+1,min(row+25,len(lines))) if re.match(r'(?i)^\s*(?:ABSTRACT\b|1[. ]+INTRODUCTION\b)',lines[i])),None)
        if stop is None:
            mailrows=[i for i in range(row+1,min(row+20,len(lines))) if all_mailboxes(lines[i])]
            if not mailrows:continue
            stop=max(mailrows)+1
        region='\n'.join(lines[row:stop]).strip()
        if len(region)>2500:return None
        columns=coordinate_columns(words,printed)
        if columns is None:return None
        if any(not has_name(col,n) for col,n in zip(columns,printed)):return None
        return region,columns
    return None


def indexed_correspondence_error(proof, original, author_index):
    """Literal numbered affiliations plus a complete named correspondence block."""
    pdf=proof['pdf'];authors=proof['authors'];blocks=proof.get('affiliation_blocks') or []
    bymarker={b['marker']:b for b in blocks}
    if not blocks or len(bymarker)!=len(blocks):return 'ambiguous_indexed_affiliations'
    plain=' '.join(original.split())
    for marker,b in bymarker.items():
        other_markers = [m for m in bymarker if m != marker]
        crosses_definition = bool(other_markers and re.search(
            r'(?:\n|,)\s*(?:' + '|'.join(map(re.escape, other_markers)) + r')\s+\D', b['quote']))
        if (not literal_occurrences(b['quote'],plain) or not re.match(r'^'+re.escape(marker)+r'(?!\d)',b['quote'].strip())
                or any(not has_name(b['quote'],a) for a in b['affiliations'])
                or crosses_definition):
            return 'unbound_affiliation_definition'
    for a in authors:
        q=a.get('marker_quote','');marks=a.get('affiliation_markers') or []
        if not q or not marks or not literal_occurrences(q,plain) or not starts_name(q,a['printed']):return 'unbound_author_affiliation_marker'
        tail=norm(q)[len(norm(a['printed'])):]
        if (re.findall(r'\d+',tail)!=marks or any(m not in bymarker for m in marks)
                or re.search(r'[^\d\s,*†‡]',tail)):
            return 'unbound_author_affiliation_marker'
        expected=list(dict.fromkeys(f for m in marks for f in bymarker[m]['affiliations']))
        if a['affiliations']!=expected:return 'different_indexed_affiliation_map'
    # A whole publisher block ends at the next labelled sidebar item. Within it,
    # author-name and email events must strictly alternate, never a clipped matrix.
    start=re.search(r'(?i)\*?\s*Correspondence\s*:',plain)
    if not start:return 'missing_named_correspondence_block'
    end=re.search(r'(?i)\b(?:Specialty section|Received|Accepted|Published|Citation|Edited by|Reviewed by)\s*:',plain[start.end():])
    if not end:return 'unbounded_named_correspondence_block'
    block=plain[start.start():start.end()+end.start()].strip()
    if not pdf.get('correspondence_quote') or ' '.join(pdf['correspondence_quote'].split())!=block:return 'different_complete_correspondence_block'
    events=[]
    for i,a in enumerate(authors):
        for m in re.finditer(r"(?<![\w'-])"+re.escape(norm(a['printed']))+r"(?![\w'-])",norm(block)):
            events.append((m.start(),'author',i))
    # Locate literal all-domain addresses without deriving or expanding one.
    local=r"A-Za-z0-9.!#$%&'*+/=?^_`{|}~\-"
    for m in re.finditer(r'(?<!['+local+r'])(['+local+r']+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)',norm(block)):
        events.append((m.start(),'mail',m[1]))
    events.sort()
    if not events or len(events)%2 or any(events[j][1]!='author' or events[j+1][1]!='mail' for j in range(0,len(events),2)):
        return 'ambiguous_named_correspondence_order'
    selected=[events[j+1][2] for j in range(0,len(events),2) if events[j][2]==author_index]
    if selected!=[proof['mailbox']]:return 'different_named_correspondence_mailbox'
    return None


def preimages(member, paper, pi, source):
    return {kind: digest(semantic(value, kind)) for kind, value in
            [('member', member), ('paper', paper), ('pi', pi)]} | {'source_work': digest(source)}


def proof_error(d, member, paper, pi, school, *, source=None, directory_raw=None, policy_raw=None, pdf_text=None, root=None):
    """Check typed assertions as well as the independently reviewed scientific preimages."""
    if school != 'cambridge' or d['school'] != school:
        return 'unsupported_or_changed_school'
    if source is None:
        return 'missing_native_source'
    if d['preimages'] != preimages(member, paper, pi, source):
        return 'stale_scientific_preimage'
    p = d['proof']
    directory, policy, pdf, period = (p[k] for k in ['directory', 'mail_policy', 'pdf', 'student_period'])
    native_names = [a.get('raw_author_name') or (a.get('author') or {}).get('display_name') for a in source.get('authorships', [])]
    if (source.get('id') != d['match']['oa'] or ndoi(source.get('doi')) != ndoi(paper.get('doi'))
            or native_names != [a['native'] for a in p['authors']]):
        return 'different_native_source_byline'
    raw = directory_raw if directory_raw is not None else evidence_bytes(school, directory['sha256'], root=root)
    if raw is None or hashlib.sha256(raw).hexdigest() != directory['sha256']:
        return 'missing_or_changed_original_directory'
    original = BeautifulSoup(raw, 'html.parser')
    entries = original.find_all('li', id=directory['record_id'])
    if len(entries) != 1 or len(original.find_all('h2', id=directory['supervisor_id'])) != 1:
        return 'competing_original_directory_records'
    entry = entries[0]
    if entry.find('li') or len(entry.find_all('b')) != 1:
        return 'competing_original_directory_records'
    owner = entry.find_previous('h2') if entry else None
    name_bold = entry.find('b')
    name_anchor = name_bold.find('a') if name_bold else None
    identifier_kind = directory.get('identifier_binding', 'owned_profile')
    if (not owner or owner.get('id') != directory['supervisor_id'] or not name_bold
            or ' '.join(name_bold.get_text(' ', strip=True).split()) != member['name']):
        return 'different_original_directory_person'
    if identifier_kind == 'owned_profile':
        if (not name_anchor or urljoin('https://www.cl.cam.ac.uk/lists/phd/supervisor.html', name_anchor.get('href', '')) != directory['profile_url']):
            return 'different_original_directory_person'
    elif identifier_kind == 'owned_thesis_identifiers':
        crsid = directory['crsid']
        links = [urljoin('https://www.cl.cam.ac.uk/lists/phd/supervisor.html', a.get('href', '')) for a in entry.find_all('a')]
        apollo = [v for v in links if urlsplit(v).hostname == 'www.repository.cam.ac.uk'
                  and urlsplit(v).path == '/search' and parse_qs(urlsplit(v).query).get('query') == ['pubs.staff-id:' + crsid]]
        local = 'https://www.cl.cam.ac.uk/lists/phd/files/' + crsid + '-thesis.pdf'
        if directory.get('profile_url') is not None or len(apollo) != 1 or links.count(local) != 1:
            return 'unbound_owned_thesis_identifiers'
    else:
        return 'unsupported_directory_identifier_binding'
    if not pi_identifier(pi, directory['supervisor_id']):
        return 'unbound_canonical_pi_identifier'
    actual_entry = ' '.join(entry.get_text(' ', strip=True).split())
    if period['quote'] not in actual_entry:
        return 'different_original_student_period'
    raw_policy = policy_raw if policy_raw is not None else evidence_bytes(school, policy['sha256'], root=root)
    if (raw_policy is None or hashlib.sha256(raw_policy).hexdigest() != policy['sha256']
            or norm(policy['quote']) not in norm(BeautifulSoup(raw_policy, 'html.parser').get_text(' ', strip=True))
            or not re.fullmatch(r'https://(?:[a-z0-9-]+\.)+cam\.ac\.uk/[^\s]*', policy['url'])):
        return 'unbound_original_university_mail_policy'
    if pdf_text is None:
        pdf_text = original_pdf_text(school, pdf, root=root)
    if pdf_text is None:
        return 'missing_or_changed_primary_pdf'
    first_page = article_page_text(p, pdf_text)
    if first_page is None:
        return 'unbound_primary_article_page_or_cover'
    first_plain = ' '.join(first_page.split())
    before_abstract = re.split(r'(?i)\bAbstract\b', first_plain, maxsplit=1)[0]
    header_lines = [norm(x) for x in first_page.splitlines() if x.strip()]
    title = norm(pdf['title'])
    marker = '' if pdf['title_footnote_marker'] == 'none' else pdf['title_footnote_marker']
    primary_title = title + marker
    def title_text(q):
        return norm(q).replace(' ' + marker, marker) if marker else norm(q)
    if title_text(pdf['title_quote']) != primary_title or not any(
            title_text(' '.join(header_lines[i:j])) == primary_title
            for i in range(len(header_lines)) for j in range(i + 1, min(i + 12, len(header_lines)) + 1)):
        return 'different_complete_primary_title'
    before_references = re.split(r'(?i)\b(?:References|Bibliography)\b', first_plain, maxsplit=1)[0]
    for field in ['title_quote', 'byline_quote']:

        if not literal_occurrences(pdf[field], before_abstract):
            return 'publication_identity_outside_first_page_header'
    for field in ['identifier_quote','date_quote','author_binding_quote','affiliation_quote']:
        q = ' '.join(pdf[field].split())
        if not literal_occurrences(q, before_references) or re.search(r'(?i)^\s*(References|Bibliography|Related work)\b', q):
            return 'primary_proof_outside_publication_header'
    for author in p['authors']:
        if not literal_occurrences(author['source_quote'], first_plain):
            return 'unbound_primary_affiliation_quote'
    if pdf['date'] not in stated_dates(pdf['date_quote']):
        return 'unsupported_publication_date_precision'
    if paper.get('editions'):
        return 'edition_group_requires_separate_proof'
    if not paper.get('identity') or not paper.get('appointment'):
        return 'ineligible_lab_paper'
    if str(paper['identity']).startswith(('candidate', 'unknown', 'unverified')):
        return 'ineligible_lab_paper'
    if member.get('sourceRecordKey') != directory['source_record_key']:
        return 'different_source_person'
    expected_key = 'cambridge-phd-directory:' + directory['supervisor_id'] + ':' + directory['record_id']
    crsid = directory['crsid']
    if (directory['source_record_key'] != expected_key or directory['record_id'] != 's-' + crsid
            or not re.fullmatch('[a-z][a-z0-9]{1,12}', crsid)):
        return 'unbound_university_identifier'
    if (directory['student_name'] != member['name'] or directory['pi'] != d['pi']
            or directory['student_name'] not in directory['quote']):
        return 'different_source_person'
    allowed_profiles = ['https://www.cl.cam.ac.uk/~' + crsid + '/',
                        'https://www.cst.cam.ac.uk/people/' + crsid]
    if identifier_kind == 'owned_profile' and directory['profile_url'] not in allowed_profiles:
        return 'unbound_owned_profile'
    source_matches = [q for rel in member.get('relations', []) for q in rel.get('sources', [])
                      if q.get('url') == directory['url'] and q.get('sha256') == directory['sha256']
                      and q.get('quote') == directory['quote']]
    if len(source_matches) != 1:
        return 'unretained_directory_source'
    if period['role'] != 'phd' or 'phd' not in member.get('roles', []):
        return 'unretained_student_role'
    if (period['source_sha256'] != directory['sha256'] or period['quote'] not in directory['quote']
            or period['start'] not in period['quote']):
        return 'unbound_student_period'
    own = list(re.finditer(re.escape(member['name']) + r'\s*\((\d{4}-\d{2}-\d{2})\s*[–-]\s*([^)]*)\)', directory['quote']))
    if len(own) != 1 or own[0].group(1) != period['start'] or period['quote'] != own[0].group(0):
        return 'different_student_period'
    if period['end_basis'] == 'stated_end':
        if own[0].group(2) != period['end']:

            return 'unbound_student_period'
    elif period['end_basis'] == 'current_capture':
        cap = re.search(r'/web/(\d{4})(\d{2})(\d{2})\d{6}', directory['url'])
        if (not cap or period['end'] != '-'.join(cap.groups())
                or not any('– ' + status in period['quote'] for status in ['active', 'prelim', 'submitted'])):
            return 'unbound_current_observation'
    else:
        return 'unbound_student_period'
    mailbox = p['mailbox']
    if mailbox != crsid + '@' + policy['domain']:
        return 'unbound_literal_mailbox'
    if (policy['domain'] != 'cam.ac.uk' or 'crsid' not in policy['quote'].casefold()
            or '@cam.ac.uk' not in policy['quote']):
        return 'unsupported_mailbox_convention'
    if not name_variant_ok(member['name'],pdf['member_name'],p.get('name_variant','exact')) or pdf['mailbox'] != mailbox:
        return 'wrong_primary_author'
    if not (pdf['complete_body'] and pdf['parse_returncode'] == 0 and pdf['pages'] > 0 and pdf['bytes'] > 0):
        return 'incomplete_primary_pdf'
    if (not ndoi(paper.get('doi')) or pdf['doi'] != ndoi(paper['doi'])
            or not title_ok(p,paper,before_references)):
        return 'different_work_or_edition'
    if norm(pdf['title']) not in norm(pdf['title_quote']) or (printed_dois(pdf['identifier_quote']) != {pdf['doi'].casefold()}
            or not token_in_original(pdf['identifier_quote'], before_references, pdf['doi'].casefold(), doi_tokens)):
        return 'unquoted_publication_identity'
    authors = p['authors']
    if [a['native'] for a in authors] != paper.get('byline') or len({a['native'] for a in authors}) != len(authors):
        return 'incomplete_or_ambiguous_native_byline'
    printed = [a['printed'] for a in authors]
    for a in authors:
        if (not has_name(a['source_quote'], a['printed'])
                or (pdf['mapping'] != 'indexed_correspondence'
                    and any(norm(f) not in norm(a['source_quote']) for f in a['affiliations']))):
            return 'unbound_complete_affiliation_map'
    if len(set(printed)) != len(printed) or len(authors) != len(pdf['authors']) or printed != pdf['authors']:
        return 'incomplete_primary_byline'
    try:
        positions = [norm(pdf['byline_quote']).index(norm(name)) for name in printed]
    except ValueError:
        return 'incomplete_primary_byline'
    if positions != sorted(positions):
        return 'different_primary_byline_order'
    i = pdf['author_index']
    if (i >= len(authors) or authors[i]['member'] != member['person'] or authors[i]['printed'] != pdf['member_name']
            or any(a['member'] is not None for j, a in enumerate(authors) if j != i)):
        return 'wrong_primary_author_slot'
    if authors[i]['mailbox'] != mailbox or 'University of Cambridge' not in authors[i]['affiliations']:
        return 'wrong_primary_author_affiliation'
    binding = pdf['author_binding_quote']
    if len(binding) > 2500 or re.search(r'(?i)\b(abstract|introduction|references|acknowledg)', binding):
        return 'author_binding_outside_byline_block'
    if pdf['mapping'] == 'named_author_address':
        if not named_author_clause(binding, first_page) or set(all_mailboxes(binding)) != {mailbox}:
            return 'unbound_complete_named_address_clause'
        if not starts_name(binding, pdf['member_name']):
            return 'wrong_named_author_block'
        if any(has_name(binding, a['printed']) for j,a in enumerate(authors) if j != i):
            return 'competing_named_author_block'
    elif pdf['mapping'] == 'shared_campus_block':
        if any(a['affiliations'] != ['University of Cambridge'] for a in authors):
            return 'mixed_affiliation_shared_block'
        if any(not has_name(binding, n) for n in printed):
            return 'incomplete_shared_author_block'
        if re.search(r'(?i)\b(?:correspondence|contact|corresponding author|electronic address)\b', binding):
            return 'competing_named_contacts_in_shared_block'
        name_positions = [list(re.finditer(r"(?<![\w'-])" + re.escape(norm(n)) + r"(?![\w'-])", norm(binding))) for n in printed]
        if any(len(v) != 1 for v in name_positions) or [v[0].start() for v in name_positions] != sorted(v[0].start() for v in name_positions):
            return 'unbound_shared_author_order'
        addresses = all_mailboxes(binding)
        if addresses != [a['mailbox'] for a in authors] or len(set(addresses)) != len(authors):
            return 'unbound_shared_email_order'
        if any(not address for address in addresses):
            return 'incomplete_shared_email_map'
    elif pdf['mapping'] == 'author_columns':
        boxes=original_pdf_boxes(school,pdf,root=root)
        page=pdf.get('article_page',1)-1
        parsed=author_columns(first_page,printed,boxes[page]) if boxes and page<len(boxes) else None
        if not parsed or ' '.join(binding.split())!=' '.join(parsed[0].split()):return 'unbound_complete_author_columns'
        for a,col in zip(authors,parsed[1]):
            if any(not has_name(col,f) for f in a['affiliations']):return 'different_primary_column_affiliation'
        if set(all_mailboxes(parsed[1][i]))!={mailbox}:return 'different_primary_column_mailbox'
    elif pdf['mapping'] == 'indexed_correspondence':
        reason=indexed_correspondence_error(p,first_page,i)
        if reason:return reason
    else:
        return 'unsupported_author_mapping'
    if (not has_name(pdf['author_binding_quote'], pdf['member_name'])
            or mailbox not in mailboxes(pdf['author_binding_quote'])
            or not token_in_original(pdf['author_binding_quote'], first_plain, mailbox, mailbox_tokens)
            or (pdf['mapping'] != 'indexed_correspondence' and not has_name(pdf['author_binding_quote'],'University of Cambridge'))
            or 'University of Cambridge' not in pdf['affiliation_quote']):
        return 'unbound_author_mailbox_affiliation'
    try:
        start, end = bounds(period['start'])[1], bounds(period['end'])[0]
        plo, phi = bounds(pdf['date'])
        nlo, nhi = bounds(paper['date'])
        if paper['year'] != nlo.year or nlo.year != nhi.year or nlo.year != plo.year or phi.year != plo.year:
            return 'publication_date_conflict'
        if start > end:
            return 'invalid_student_period'
        if p['timing'] == 'within_stated_student_period':
            if not (start <= plo <= phi <= end and start <= nlo <= nhi <= end):
                return 'publication_outside_student_period'
        elif p['timing'] == 'recorded_student_publication_window':
            # R-LNK-01/03: recorded student years, not publication-time enrollment.
            owned = [rel for rel in member.get('relations', []) if rel.get('role') == 'phd'
                     and any(q.get('url') == directory['url'] and q.get('sha256') == directory['sha256']
                             and q.get('quote') == directory['quote'] for q in rel.get('sources', []))]
            years = owned[0].get('years') if len(owned) == 1 else None
            if (not isinstance(years, list) or not years
                    or any(type(y) is not int and not (isinstance(y, str) and re.fullmatch(r'\d{4}', y)) for y in years)
                    or {int(y) for y in years} != {int(period['end'][:4])}):
                return 'unbound_recorded_student_years'
            lo, hi = datetime.date(min(map(int, years)) - 2, 1, 1), datetime.date(max(map(int, years)) + 6, 12, 31)
            if not (lo <= plo <= phi <= hi and lo <= nlo <= nhi <= hi):
                return 'outside_recorded_student_publication_window'
        elif p['timing'] == 'historical_student_publication':
            # R-LNK-01's explicit alumni semantics: no publication-time enrollment claim.
            limit = datetime.date(end.year + 6, end.month, min(end.day, calendar.monthrange(end.year + 6, end.month)[1]))
            if period['end_basis'] != 'stated_end' or not (end < plo <= phi <= limit and end < nlo <= nhi <= limit):
                return 'outside_historical_student_window'
        else:
            return 'unsupported_temporal_claim'
    except (ValueError, TypeError, KeyError):
        return 'invalid_publication_or_student_date'
    if pdf['date'][:4] not in pdf['date_quote']:
        return 'unquoted_publication_date'
    return None


def apply(ctx):
    path = P.data('student-authorship-review.json', ctx.school, root=ctx.here)
    if not path.exists():
        return
    raw = path.read_bytes()
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError('student authorship review exceeds 5 MB')
    data = json.loads(raw)
    if validate(data, schema()) or data['school'] != ctx.school:
        raise ValueError('invalid student authorship review')
    if len({d['id'] for d in data['reviews']}) != len(data['reviews']):
        raise ValueError('duplicate student authorship review IDs')
    report = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), decisions=[])
    targets = collections.Counter((d['pi'], d['member'], d['match']['oa'], d['match']['work']) for d in data['reviews'])
    exclusion_file = P.data('student-link-exclusions.json', ctx.school, root=ctx.here)
    exclusions = set()
    if exclusion_file.exists():
        doc = json.loads(exclusion_file.read_text())
        if doc.get('version') != 1 or doc.get('school') != ctx.school:
            raise ValueError('invalid active student link exclusions')
        exclusions = {(x['pi'], x['student'], x['oa']) for x in doc.get('exclusions', [])}
    planned = []
    for d in data['reviews']:
        datetime.date.fromisoformat(d['reviewed_at'])
        target = (d['pi'], d['member'], d['match']['oa'], d['match']['work'])
        members = [m for m in ctx.stu.get(d['pi'], {}).values() if m['person'] == d['member']]
        papers = [p for p in ctx.rows if p['pi'] == d['pi'] and p.get('oa') == d['match']['oa'] and p.get('work') == d['match']['work']]
        pis = [p for p in ctx.pis if p['pi'] == d['pi']]
        sources = {digest(h[1]):h[1] for h in getattr(ctx, 'hits', []) if h[0] == d['pi'] and h[1].get('id') == d['match']['oa']}
        reason = None
        if targets[target] != 1:
            reason = 'competing_reviews'
        elif any(len(x) != 1 for x in [members, papers, pis]) or len(sources) != 1:
            reason = 'missing_or_ambiguous_native_target'
        elif (d['pi'], members[0]['name'], d['match']['oa']) in exclusions:
            reason = 'active_link_exclusion'
        elif any(x['pi'] == target[0] and x['student'] == target[1] and x.get('oa') == target[2] and x.get('work') == target[3] for x in ctx.sp):
            reason = 'existing_link_retained'
        else:
            reason = proof_error(d, members[0], papers[0], native_pi(ctx, pis[0]), ctx.school, source=next(iter(sources.values())), root=ctx.here)
        report['decisions'].append(dict(id=d['id'], pi=d['pi'], member=d['member'], oa=d['match']['oa'], status='held' if reason else 'verified', reason=reason))
        if reason is None:
            planned.append(dict(pi=d['pi'], student=d['member'], name=members[0]['name'], work=d['match']['work'], oa=d['match']['oa'],
                                status='verified', basis=BASIS, byline=d['proof']['pdf']['member_name'],
                                relation_source=dict(relation='researched_advising', **{k:d['proof']['directory'][k] for k in ['url','sha256','quote']}),
                                **{MARKER:dict(version=1, identity_scope='exact_work', school=ctx.school,
                                             input_sha256=report['sha256'], review=copy.deepcopy(d), native_source=copy.deepcopy(next(iter(sources.values()))))}))
    ctx.sp.extend(planned)
    ctx.student_authorship_review = report
    ctx.n['student_authorship_verified'] = len(planned)
    ctx.n['student_authorship_held'] = len(report['decisions']) - len(planned)


def validate_scoped(school, members, papers, links, *, pis):
    for link in links:
        if not scoped(link):
            continue
        proof = link.get(MARKER) or {}
        d = proof.get('review') or {}
        if (validate(dict(version=1, school=school, reviews=[d]), schema()) or proof.get('version') != 1
                or proof.get('school') != school or proof.get('identity_scope') != 'exact_work'
                or not re.fullmatch('[0-9a-f]{64}', str(proof.get('input_sha256') or ''))):
            raise ValueError('invalid institutional member paper proof')
        ms = [m for m in members.get(d['pi'], []) if m['person'] == d['member']]
        ps = [p for p in papers if p['pi'] == d['pi'] and p.get('oa') == d['match']['oa'] and p.get('work') == d['match']['work']]
        pp = [p for p in pis if p['pi'] == d['pi']]
        ls = [l for l in links if l['pi'] == d['pi'] and l.get('oa') == d['match']['oa'] and l.get('work') == d['match']['work'] and l['student'] == d['member']]
        if (link.get('basis') != BASIS or link.get('status') != 'verified' or link['pi'] != d['pi'] or link['student'] != d['member']
                or link.get('oa') != d['match']['oa'] or link.get('work') != d['match']['work']
                or any(len(x) != 1 for x in [ms, ps, pp, ls])):
            raise ValueError('stale institutional member paper target')
        expected_link = dict(pi=d['pi'], student=d['member'], name=ms[0]['name'], work=d['match']['work'], oa=d['match']['oa'],
                             status='verified', basis=BASIS, byline=d['proof']['pdf']['member_name'],
                             relation_source=dict(relation='researched_advising', **{k:d['proof']['directory'][k] for k in ['url','sha256','quote']}))
        actual_link = semantic(link, 'candidate')
        actual_link.pop(MARKER, None)
        if actual_link != expected_link:
            raise ValueError('changed institutional member paper scientific link')
        if proof_error(d, ms[0], ps[0], pp[0], school, source=proof.get('native_source')):
            raise ValueError('stale institutional member paper preimage or proof')
