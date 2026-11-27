"""Reviewed uncertainty policy for derived coauthor school flags, never paper admission."""
import copy
import datetime
import re

from . import primary_affiliations

MODE = 'hold_unmapped_large_collaboration_flags'
SCOPE = 'derived_school_flags_only'


def _sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def prepare(ctx, data, path, input_sha256):
    ctx.school_flag_policy = None
    ctx.school_flag_policy_summary = None
    ctx._school_flag_policy_candidates = {}
    ctx._school_flag_policy_primary_sources = {}
    policy = data.get('derived_school_flags_policy')
    if policy is None:
        return
    fields = {'version', 'school', 'mode', 'scope', 'min_authorships', 'min_institution_ids',
              'why', 'reviewed_by', 'reviewed_at', 'evidence'}
    if not isinstance(policy, dict) or set(policy) != fields or type(policy['version']) is not int or policy['version'] != 1 \
            or policy['school'] != ctx.school or policy['mode'] != MODE or policy['scope'] != SCOPE:
        raise ValueError('invalid reviewed derived school flag uncertainty policy')
    for key in ('min_authorships', 'min_institution_ids'):
        if type(policy[key]) is not int or not 2 <= policy[key] <= 1000000:
            raise ValueError('school flag uncertainty thresholds must be reviewed positive integer counts')
    if any(not isinstance(policy[key], str) or not policy[key].strip() for key in ('why', 'reviewed_by', 'reviewed_at')):
        raise ValueError('school flag uncertainty policy needs reason and reviewer/date')
    datetime.date.fromisoformat(policy['reviewed_at'])
    evidence = policy['evidence']
    if not isinstance(evidence, list) or not evidence or any(
            not isinstance(e, dict) or not re.fullmatch(r'https?://[^\s]+', str(e.get('url') or ''))
            or not _sha(e.get('sha256')) or not isinstance(e.get('quote'), str) or not e['quote'].strip()
            or e.get('source_kind') not in ('primary_pdf', 'partial_fulltext_jats') for e in evidence):
        raise ValueError('school flag uncertainty policy needs typed primary example evidence')
    ctx.school_flag_policy = copy.deepcopy(policy)
    ctx.school_flag_policy_summary = dict(input_path=str(path), input_sha256=input_sha256,
                                         policy=copy.deepcopy(policy), held_claims=[], accepted_primary_claims_preserved=[])


def observe(ctx, work):
    """Retain only stable raw count/digest observations. No row or eligibility changes here."""
    policy = getattr(ctx, 'school_flag_policy', None)
    if policy is None:
        return
    authorships = work.get('authorships') or []
    if len(authorships) < policy['min_authorships']:
        return
    institutions = {i['id'] for a in authorships for i in a.get('institutions') or []
                    if isinstance(i.get('id'), str) and i['id'].strip()}
    if len(institutions) < policy['min_institution_ids']:
        return
    record = dict(work=work['id'], source_work_sha256=primary_affiliations.digest(work),
                  source_authorships_sha256=primary_affiliations.digest(authorships),
                  raw_authorships=len(authorships), distinct_source_institution_ids=len(institutions))
    ctx._school_flag_policy_candidates.setdefault(work['id'], {})[record['source_work_sha256']] = record


def record_primary(ctx, work, review, school_names):
    """Called only after the complete primary resolver actually returns corrected flags.

    Bind its entire evidence, raw lead byline, corrected flags and both actual
    source digests; accepted-looking row metadata alone grants no exception.
    """
    if getattr(ctx, 'school_flag_policy', None) is None:
        return
    if review.get('status') != 'accepted' or review.get('work') != work.get('id') \
            or review.get('source_work_sha256') != primary_affiliations.digest(work) \
            or review.get('source_authorships_sha256') != primary_affiliations.digest(work.get('authorships') or []) \
            or not (_sha(review.get('pdf_sha256')) or _sha(review.get('source_xml_sha256'))) \
            or not review.get('author_blocks'):
        return
    authors = work.get('authorships') or []
    if not authors:
        return
    names = [a.get('raw_author_name') or (a.get('author') or {}).get('display_name') for a in authors]
    if not isinstance(school_names, list) or any(not isinstance(n, str) or n not in names for n in school_names):
        return
    source = dict(work=work['id'], source_work_sha256=review['source_work_sha256'],
                  source_authorships_sha256=review['source_authorships_sha256'], raw_authorships=len(authors),
                  distinct_source_institution_ids=len({i['id'] for a in authors for i in a.get('institutions') or []
                                                      if isinstance(i.get('id'), str) and i['id'].strip()}))
    proof = dict(source=source, review_sha256=primary_affiliations.digest(review),
                 byline=names,
                 school_names=copy.deepcopy(school_names))
    ctx._school_flag_policy_primary_sources.setdefault(work['id'], {})[proof['review_sha256']] = proof


def _accepted_primary(ctx, row):
    review = row.get('byline_affiliation_review') or {}
    proof = ctx._school_flag_policy_primary_sources.get(row.get('oa'), {}).get(primary_affiliations.digest(review))
    return proof if proof and proof['byline'] == row.get('byline') and proof['school_names'] == row.get('byline_school') else None


def apply(ctx, rows):
    """After ordinary admission and folding: hold whole related claim, retain complete primary lead mappings."""
    summary = getattr(ctx, 'school_flag_policy_summary', None)
    if summary is None:
        return
    candidates = ctx._school_flag_policy_candidates
    for row in rows.values():
        identifiers = {r.get('oa') for r in [row] + list(row.get('editions') or [])}
        matched = [v for wid in sorted(i for i in identifiers if i) for _, v in sorted(candidates.get(wid, {}).items())]
        if not matched:
            continue
        receipt = dict(pi=row['pi'], oa=row.get('oa'), matched_sources=copy.deepcopy(matched))
        primary = _accepted_primary(ctx, row)
        if primary:
            receipt['validated_primary_source'] = copy.deepcopy(primary['source'])
            receipt['primary_review_sha256'] = primary['review_sha256']
            # Other eligible edition bylines remain present but cannot restore
            # unreviewed positives alongside the complete primary lead mapping.
            if '_bylines' in row:
                row['_bylines'] = [(names, []) for names, _ in row['_bylines']]
                row['_bylines'].append((copy.deepcopy(row['byline']), copy.deepcopy(row['byline_school'])))
            summary['accepted_primary_claims_preserved'].append(receipt)
            continue
        prior = row.get('byline_affiliation_review')
        row['byline_school'] = []
        if '_bylines' in row:
            row['_bylines'] = [(names, []) for names, _ in row['_bylines']]
        evidence = dict(status='held', scope=SCOPE, mode=MODE,
                        reason='unmapped_large_multi_institution_collaboration',
                        input_sha256=summary['input_sha256'], policy=copy.deepcopy(ctx.school_flag_policy),
                        matched_sources=copy.deepcopy(matched),
                        qualification='Entire derived school list withheld/unknown; not verified absence of school authors. '
                                      'No per-person affiliation or ordinary PI/paper eligibility is certified by this policy.')
        if prior is not None:
            evidence['prior_derivation'] = copy.deepcopy(prior)
        row['byline_affiliation_review'] = evidence
        summary['held_claims'].append(receipt)
    ctx.n['derived_school_flag_policy_claims_held'] = len(summary['held_claims'])
    ctx.n['derived_school_flag_policy_primary_mappings_preserved'] = len(summary['accepted_primary_claims_preserved'])
