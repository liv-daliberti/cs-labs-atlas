"""Optional, source-bound certification of one existing member/PI/work link.

This is authorship evidence for ONE work, never a person identity anchor. No
membership, paper admission, source observation, date or edition is changed.
"""
import calendar
import copy
import datetime
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import atlas_paths as P
from schema_check import validate
from .common import ndoi

BASIS = 'reviewed_exact_member_paper'
PROJECTION = 'member-paper-semantic-v1'
ID_FIELDS = {'candidate': {'studentAtlasId', 'atlasWorkId', 'labId'},
             'member': {'atlasId', 'alsoPi'}, 'paper': {'atlasWorkId', '_bylines'}}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def semantic(value, kind):
    """Bind every persisted field, including future scientific fields, except named ID augmentation.

    _bylines is the builder's transient union, removed before publication. The
    complete persisted paper/edition group and exact source work bind its inputs.
    Only top-level fields are removed: nested source/edition fields stay bound.
    """
    return {k: copy.deepcopy(v) for k, v in value.items() if k not in ID_FIELDS[kind]}


def preimages(candidate, member, paper, source):
    return dict(candidate=digest(semantic(candidate, 'candidate')), member=digest(semantic(member, 'member')),
                paper=digest(semantic(paper, 'paper')), editions=digest(paper.get('editions') or []),
                source_work=digest(source))


def work_only(link):
    """Recognize either marker, so malformed scoped rows cannot lend an identity bridge."""
    return link.get('basis') == BASIS or 'workReview' in link


def _bounds(value):
    """All possible dates at the stated precision; never substitute an observation date."""
    if re.fullmatch(r'\d{4}', value):
        y = int(value)
        return datetime.date(y, 1, 1), datetime.date(y, 12, 31)
    if re.fullmatch(r'\d{4}-\d{2}', value):
        y, m = map(int, value.split('-'))
        return datetime.date(y, m, 1), datetime.date(y, m, calendar.monthrange(y, m)[1])
    day = datetime.date.fromisoformat(value)
    return day, day


def _norm(value):
    return ' '.join(value.split()).casefold().rstrip('.')


def _arxiv(value):
    m = re.fullmatch(r'(\d{4}\.\d{4,5})v([1-9]\d*)', value)
    return m.group(1) if m else None


def _proof_error(d, candidate, member, paper, source, school):
    """Validate cross-field meaning in addition to the closed input schema."""
    p, m = d['proof'], d['match']
    citation, pdf, period = p['citation'], p['pdf'], p['period']
    chain = p['chain']
    if [x['kind'] for x in chain] != ['official_pi', 'pi_person', 'person_identity', 'authored_citation']:
        return 'incomplete_owned_chain'
    if (chain[0]['form'] not in ('dom_anchor', 'literal_published_text_not_clickable_anchor')
            or chain[1]['form'] != 'dom_anchor' or chain[3]['form'] != 'dom_anchor'
            or chain[2]['form'] not in ('dom_anchor', 'same_owned_document')):
        return 'incorrect_source_link_form'
    used = set()
    for i, (left, right) in enumerate(zip(chain, chain[1:])):
        href = urljoin(left['url'], left['href'])  # resolve literal relative DOM hrefs only
        if left['form'] == 'same_owned_document' and not (left['url'] == left['href'] == right['url']):
            return 'disconnected_owned_chain'
        if href == right['url']:
            continue
        resolutions = [r for r in p['link_resolutions'] if r['index'] == i
                       and r['href'] == left['href'] and r['url'] == right['url']
                       and r['source_sha256'] == left['sha256'] and r['target_sha256'] == right['sha256']
                       and r['packet_sha256'] == p['packet_sha256'] and r['pi_name'] == p['adviser_name']
                       and r['pi_name'] in r['context_quote']]
        if len(resolutions) != 1:
            return 'disconnected_owned_chain'
        a, b = urlsplit(href), urlsplit(right['url'])
        if (a.hostname != b.hostname or a.path.rstrip('/') != b.path.rstrip('/')
                or a.query != b.query or a.fragment != b.fragment):
            return 'not_same_reviewed_personal_path'
        used.add(i)
    if len(used) != len(p['link_resolutions']) or chain[3]['url'] != citation['url']:
        return 'disconnected_owned_chain'
    if (p['member_name'] != member['name'] or p['pi'] != d['pi'] or p['school'] != school
            or p['member_name'] not in p['self_quote'] or p['adviser_name'] not in p['advisor_quote']
            or p['advisor_quote'] != chain[2]['quote']):
        return 'identity_or_role_quote_mismatch'
    if period['role'] not in member.get('roles', []) or not any(
            r.get('type') == period['relation'] for r in member.get('relations', [])):
        return 'unretained_role_or_relation'
    if (period['start'] not in period['quote'] or period['end'] not in period['quote']
            or period['role_label'] not in period['quote']):
        return 'undated_role_quote'
    if not (paper.get('identity') and paper.get('appointment')) or str(paper['identity']).startswith(('candidate', 'unknown', 'unverified')):
        return 'ineligible_accepted_paper'
    if (source.get('id') != m['oa'] or ndoi(source.get('doi')) != m['doi']
            or m['doi'] != ndoi(m['doi']) or not m['doi']):
        return 'source_identifier_mismatch'
    arxiv = _arxiv(m['arxiv_version'])
    if not arxiv or m['doi'] != '10.48550/arxiv.' + arxiv:
        return 'unbound_source_edition'
    if citation['href'] not in ('https://arxiv.org/abs/' + arxiv, 'https://arxiv.org/abs/' + m['arxiv_version']):
        return 'wrong_citation_identifier'
    if chain[3]['href'] != citation['href']:
        return 'citation_chain_identifier_mismatch'
    if pdf['url'] != 'https://arxiv.org/pdf/' + m['arxiv_version'] or pdf['arxiv_version'] != m['arxiv_version']:
        return 'wrong_pdf_edition'
    actual = [a.get('raw_author_name') or (a.get('author') or {}).get('display_name') for a in source.get('authorships') or []]
    bindings = p['authors']
    if len(bindings) != len(actual) or [a['native'] for a in bindings] != actual:
        return 'incomplete_or_changed_source_byline'
    printed = [a['printed'] for a in bindings]
    if (citation['authors'] != printed or pdf['authors'] != printed or len(set(actual)) != len(actual)
            or len(set(printed)) != len(printed)):
        return 'incomplete_or_ambiguous_printed_byline'
    i = p['author_index']
    if (not 0 <= i < len(actual) or actual[i] != candidate['byline'] or bindings[i]['member'] != member['person']
            or bindings[i]['printed'] != member['name']):
        return 'wrong_author_slot'
    if any(a['member'] is not None for j, a in enumerate(bindings) if j != i):
        return 'other_member_assertion'
    if not all(a['evidence_sha256'] == pdf['sha256'] for a in bindings):
        return 'unbound_spelling_map'
    if (not pdf['complete_body'] or pdf['parse_returncode'] != 0 or pdf['pages'] < 1 or pdf['bytes'] < 1
            or len(pdf['affiliations']) != len(actual)):
        return 'incomplete_primary_pdf'
    if any(a['index'] != j or a['name'] != printed[j] or not a['affiliations'] for j, a in enumerate(pdf['affiliations'])):
        return 'incomplete_affiliation_map'
    if (pdf['institution'] not in pdf['affiliations'][i]['affiliations'] or pdf['school'] != school
            or pdf['institution'] not in pdf['affiliation_quote']):
        return 'target_affiliation_unconfirmed'
    if (not _norm(citation['title']) or _norm(citation['title']) != _norm(pdf['title'])
            or _norm(citation['title']) != _norm(paper.get('title') or '')):
        return 'competing_title_or_edition'
    for obj in (citation, pdf):
        quote = obj['byline_quote']
        try:
            positions = [quote.index(n) for n in printed]
        except ValueError:
            return 'incomplete_byline_quote'
        if positions != sorted(positions) or _norm(obj['title']) not in _norm(obj['quote']):
            return 'citation_not_complete_authored_item'
    if citation['kind'] != 'authored_publication' or citation['sha256'] != chain[3]['sha256']:
        return 'not_owned_authored_citation'
    if _norm(citation['byline_quote']) not in _norm(citation['quote']):
        return 'citation_byline_outside_owned_item'
    try:
        lo, hi = _bounds(period['start'])[1], _bounds(period['end'])[0]
        source_lo, source_hi = _bounds(pdf['date'])
        native_lo, native_hi = _bounds(paper['date'])
        if paper['year'] != native_lo.year or native_lo.year != native_hi.year:
            return 'native_date_year_conflict'
    except (ValueError, TypeError, KeyError):
        return 'invalid_or_missing_typed_date'
    if lo > hi or not (lo <= source_lo <= source_hi <= hi and lo <= native_lo <= native_hi <= hi):
        return 'timing_not_proven_at_stated_precision'
    literal_dates = set()
    for fmt in ('%Y-%m-%d', '%d %b %Y', '%d %B %Y', '%Y'):
        try:
            literal_dates.add(datetime.datetime.strptime(pdf['publication_quote'], fmt).date().isoformat())
        except ValueError:
            pass
    if pdf['date'] not in literal_dates:
        return 'unquoted_source_date'
    return None


def _schema():
    return json.loads((Path(__file__).resolve().parents[2] / 'schemas' / 'member_paper_review.schema.json').read_text())


def prepare(ctx):
    path = P.data('member-paper-review.json', ctx.school, root=ctx.here)
    if not path.exists():
        return [], None
    raw = path.read_bytes()
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError('member paper review exceeds 5 MB')
    data = json.loads(raw)
    errors = validate(data, _schema())
    if errors or data['school'] != ctx.school:
        raise ValueError('invalid member paper review: ' + str(errors[:3]))
    ids = [d['id'] for d in data['reviews']]
    if len(set(ids)) != len(ids):
        raise ValueError('member paper review IDs must be unique')
    for d in data['reviews']:
        datetime.date.fromisoformat(d['reviewed_at'])
    return data['reviews'], dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), decisions=[])


def _target(d, row):
    return row.get('pi') == d['pi'] and row.get('oa') == d['match']['oa'] and row.get('work') == d['match']['work']


def apply(ctx):
    """Run after ordinary links and weak-member filtering. Plan all decisions before mutating links."""
    reviews, report = prepare(ctx)
    if report is None:
        return
    actions = {}
    for d in reviews:
        candidates = [(i, x) for i, x in enumerate(ctx.sp) if _target(d, x) and x.get('student') == d['member']]
        papers = [r for r in ctx.rows if _target(d, r) and ndoi(r.get('doi')) == d['match']['doi']]
        members = [r for r in ctx.stu.get(d['pi'], {}).values() if r.get('person') == d['member']]
        sources = {digest(h[1]): h[1] for h in ctx.hits if h[0] == d['pi'] and h[1].get('id') == d['match']['oa']}
        reason, result = None, None
        if any(len(x) != 1 for x in (candidates, papers, members, sources)):
            reason = 'missing_or_ambiguous_native_target'
        else:
            i, candidate = candidates[0]
            member, paper, source = members[0], papers[0], next(iter(sources.values()))
            if candidate.get('status') != 'candidate' or work_only(candidate) or not candidate.get('byline'):
                reason = 'not_original_candidate'
            elif d['projection'] != PROJECTION or d['preimages'] != preimages(candidate, member, paper, source):
                reason = 'stale_semantic_preimage'
            else:
                reason = _proof_error(d, candidate, member, paper, source, ctx.school)
            if reason is None:
                proof = dict(version=1, identity_scope='exact_work', school=ctx.school, input_sha256=report['sha256'],
                             review=copy.deepcopy(d), original=semantic(candidate, 'candidate'))
                result = dict(candidate, status='verified', basis=BASIS, workReview=proof)
        if len(candidates) == 1:
            actions.setdefault(candidates[0][0], []).append((d['id'], result))
        report['decisions'].append(dict(id=d['id'], pi=d['pi'], member=d['member'], oa=d['match']['oa'],
                                        status='held' if reason else 'verified', reason=reason))
    for i, plans in actions.items():
        # Even identical repeated reviews require independent resolution, never first-row wins.
        if len(plans) != 1:
            for decision in report['decisions']:
                if decision['id'] in {x[0] for x in plans}:
                    decision.update(status='held', reason='competing_reviews')
        elif plans[0][1] is not None:
            ctx.sp[i] = plans[0][1]
    ctx.member_paper_review = report
    for status in ('verified', 'held'):
        ctx.n['member_paper_review_' + status] = sum(x['status'] == status for x in report['decisions'])


def validate_scoped(school, members, papers, links):
    """Before any ID writes: validate proof and post-ID semantic invariance, or fail closed.

    Source bytes are not loaded here. Their complete digest was checked in the
    native build; the retained review, original candidate and complete member /
    accepted paper preimages must still agree. This does not repair old IDs.
    """
    for link in links:
        if not work_only(link):
            continue
        proof = link.get('workReview') or {}
        d = proof.get('review') or {}
        errors = validate(dict(version=1, school=school, reviews=[d]), _schema())
        if errors or proof.get('version') != 1 or proof.get('identity_scope') != 'exact_work' or proof.get('school') != school:
            raise ValueError('invalid exact-work member paper proof')
        original = proof.get('original') or {}
        current = semantic(link, 'candidate')
        current.pop('workReview', None)
        current.update(status=original.get('status'), basis=original.get('basis'))
        ms = [m for m in members.get(d['pi'], []) if m.get('person') == d['member']]
        ps = [r for r in papers if _target(d, r) and ndoi(r.get('doi')) == d['match']['doi']]
        ls = [r for r in links if _target(d, r) and r.get('student') == d['member']]
        if (link.get('status') != 'verified' or link.get('basis') != BASIS or original.get('status') != 'candidate'
                or work_only(original) or not _target(d, link) or link.get('student') != d['member']
                or current != original or len(ms) != 1 or len(ps) != 1 or len(ls) != 1
                or not re.fullmatch('[0-9a-f]{64}', str(proof.get('input_sha256') or ''))):
            raise ValueError('stale exact-work member paper target')
        expected = d['preimages']
        if (expected['candidate'] != digest(original) or expected['member'] != digest(semantic(ms[0], 'member'))
                or expected['paper'] != digest(semantic(ps[0], 'paper'))
                or expected['editions'] != digest(ps[0].get('editions') or [])):
            raise ValueError('stale exact-work member paper preimage')
        # Recheck all retained proof semantics as well as hashes. This synthetic
        # byline view is NOT an OpenAlex ownership assertion or a source reload.
        view = dict(id=d['match']['oa'], doi=d['match']['doi'],
                    authorships=[dict(raw_author_name=a['native']) for a in d['proof']['authors']])
        if _proof_error(d, original, ms[0], ps[0], view, school):
            raise ValueError('invalid retained exact-work source proof')


def export_fields(link):
    """Optional proof travels with exports; no changes to exports without certified links."""
    if work_only(link):
        return dict(identity_scope='exact_work', work_review=copy.deepcopy(link['workReview']))
    return {}
