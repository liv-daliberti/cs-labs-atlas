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
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pathlib import Path

import atlas_paths as P
from schema_check import validate
from .common import ndoi
from .member_paper_reviews import digest, native_pi, semantic

BASIS = 'reviewed_institutional_member_paper'
MARKER = 'institutionalAuthorshipReview'


def schema():
    return json.loads((Path(__file__).resolve().parents[2] / 'schemas' / 'student_authorship_review.schema.json').read_text())


def scoped(row):
    return row.get('basis') == BASIS or MARKER in row


def norm(value):
    return ' '.join(str(value).split()).casefold()


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
    return any(re.search(r'(?:/people/|/~)' + re.escape(crsid) + r'(?:/|$)', x) for x in values)



def has_name(quote, name):
    return bool(re.search(r"(?<![\w'-])" + re.escape(norm(name)) + r"(?![\w'-])", norm(quote)))


def starts_name(quote, name):
    return bool(re.match(re.escape(norm(name)) + r"(?![\w'-])", norm(quote)))


def mailboxes(quote):
    local = r"A-Za-z0-9.!#$%&'*+/=?^_`{|}~\-"
    return re.findall(r'(?<![' + local + r'])([' + local + r']+@(?:cl\.)?cam\.ac\.uk)(?![A-Za-z0-9.-])', quote)



def stated_dates(quote):
    """Do not manufacture month/day precision from a year-only publisher assertion."""
    out = set(re.findall(r'(?<!\d)\d{4}(?:-\d{2}(?:-\d{2})?)?(?![\d-])', quote))
    for raw in re.findall(r'\b\d{1,2} [A-Za-z]{3,9} \d{4}\b', quote):
        for fmt in ['%d %b %Y','%d %B %Y']:
            try:
                out.add(datetime.datetime.strptime(raw, fmt).date().isoformat())
            except ValueError:
                pass
    return out


_PDF_TEXT = {}

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
    owner = entry.find_previous('h2') if entry else None
    name_anchor = entry.find('b').find('a') if entry and entry.find('b') else None
    if (not owner or owner.get('id') != directory['supervisor_id'] or not name_anchor
            or ' '.join(name_anchor.get_text(' ', strip=True).split()) != member['name']
            or urljoin('https://www.cl.cam.ac.uk/lists/phd/supervisor.html', name_anchor.get('href', '')) != directory['profile_url']):
        return 'different_original_directory_person'
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
    first_page = pdf_text.split('\f')[0]
    first_plain = ' '.join(first_page.split())
    before_abstract = re.split(r'(?i)\bAbstract\b', first_plain, maxsplit=1)[0]
    header_lines = [norm(x) for x in first_page.splitlines() if x.strip()]
    title = norm(pdf['title'])
    if norm(pdf['title_quote']) != title or not any(
            ' '.join(header_lines[i:j]) == title
            for i in range(len(header_lines)) for j in range(i + 1, min(i + 12, len(header_lines)) + 1)):
        return 'different_complete_primary_title'
    before_references = re.split(r'(?i)\b(?:References|Bibliography)\b', first_plain, maxsplit=1)[0]
    for field in ['title_quote', 'byline_quote']:

        if ' '.join(pdf[field].split()) not in before_abstract:
            return 'publication_identity_outside_first_page_header'
    for field in ['identifier_quote','date_quote','author_binding_quote','affiliation_quote']:
        q = ' '.join(pdf[field].split())
        if q not in before_references or re.search(r'(?i)^\s*(References|Bibliography|Related work)\b', q):
            return 'primary_proof_outside_publication_header'
    for author in p['authors']:
        if ' '.join(author['source_quote'].split()) not in first_plain:
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
    if directory['profile_url'] not in allowed_profiles:
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
    if pdf['member_name'] != member['name'] or pdf['mailbox'] != mailbox:
        return 'wrong_primary_author'
    if not (pdf['complete_body'] and pdf['parse_returncode'] == 0 and pdf['pages'] > 0 and pdf['bytes'] > 0):
        return 'incomplete_primary_pdf'
    if (not ndoi(paper.get('doi')) or pdf['doi'] != ndoi(paper['doi'])
            or norm(pdf['title']) != norm(paper.get('title'))):
        return 'different_work_or_edition'
    if norm(pdf['title']) not in norm(pdf['title_quote']) or pdf['doi'].casefold() not in pdf['identifier_quote'].casefold():
        return 'unquoted_publication_identity'
    authors = p['authors']
    if [a['native'] for a in authors] != paper.get('byline') or len({a['native'] for a in authors}) != len(authors):
        return 'incomplete_or_ambiguous_native_byline'
    printed = [a['printed'] for a in authors]
    for a in authors:
        if (not has_name(a['source_quote'], a['printed'])
                or any(norm(f) not in norm(a['source_quote']) for f in a['affiliations'])):
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
    if (i >= len(authors) or authors[i]['member'] != member['person'] or authors[i]['printed'] != member['name']
            or any(a['member'] is not None for j, a in enumerate(authors) if j != i)):
        return 'wrong_primary_author_slot'
    if authors[i]['mailbox'] != mailbox or 'University of Cambridge' not in authors[i]['affiliations']:
        return 'wrong_primary_author_affiliation'
    binding = pdf['author_binding_quote']
    if len(binding) > 2500 or re.search(r'(?i)\b(abstract|introduction|references|acknowledg)', binding):
        return 'author_binding_outside_byline_block'
    if pdf['mapping'] == 'named_author_address':
        if not starts_name(binding, member['name']):
            return 'wrong_named_author_block'
        if any(has_name(binding, a['printed']) for j,a in enumerate(authors) if j != i):
            return 'competing_named_author_block'
    elif pdf['mapping'] == 'shared_campus_block':
        if any(a['affiliations'] != ['University of Cambridge'] for a in authors):
            return 'mixed_affiliation_shared_block'
        if any(not has_name(binding, n) for n in printed):
            return 'incomplete_shared_author_block'
        if re.search(r'(?i)\b(?:correspondence|contact)\b|:', binding):
            return 'competing_named_contacts_in_shared_block'
        name_positions = [list(re.finditer(r"(?<![\w'-])" + re.escape(norm(n)) + r"(?![\w'-])", norm(binding))) for n in printed]
        if any(len(v) != 1 for v in name_positions) or [v[0].start() for v in name_positions] != sorted(v[0].start() for v in name_positions):
            return 'unbound_shared_author_order'
        addresses = mailboxes(binding)
        if addresses != [a['mailbox'] for a in authors] or len(set(addresses)) != len(authors):
            return 'unbound_shared_email_order'
        if any(not address for address in addresses):
            return 'incomplete_shared_email_map'
    else:
        return 'unsupported_author_mapping'
    if (not has_name(pdf['author_binding_quote'], member['name'])
            or mailbox not in mailboxes(pdf['author_binding_quote']) or 'University of Cambridge' not in pdf['author_binding_quote']
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
