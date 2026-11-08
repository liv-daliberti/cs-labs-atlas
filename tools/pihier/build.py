"""The build of one school's package, stage by stage (the module docstring of tools/pi_hierarchy.py says what each holds):
census -> periods (inside the PI records) -> students -> identity -> papers -> links -> weak students -> the package.
-> hierarchy/<school>/pis.json, lab_papers.jsonl.gz, students.json, student_papers.jsonl.gz, report.json
(PI_HIERARCHY_OUT=<dir> writes <dir>/<school>/ instead; the inputs stay where they are)."""
import collections, datetime, json, os, tempfile
from pathlib import Path

import atlas_paths as P  # data paths (DATA_FILES)
import provenance  # report.json -> provenance
from .common import HERE, Ctx
from . import census, identity, links, member_paper_reviews, papers, reviewed_claims, students


def atomic_json(path, value):
    """Publish complete JSON via same-directory rename; a failed write preserves the prior file."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=1, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write(ctx):
    """The package files and report.json."""
    school, out, n, pis, rows, stu, sp = ctx.school, ctx.out, ctx.n, ctx.pis, ctx.rows, ctx.stu, ctx.sp
    anchored, funnel, dblp_title, dblp_doi, verified = ctx.anchored, ctx.funnel, ctx.dblp_title, ctx.dblp_doi, ctx.verified
    excluded, nick_merges, weak_dropped, self_listed = ctx.excluded, ctx.nick_merges, ctx.weak_dropped, ctx.self_listed
    guard_samples, guard_kept_samples = ctx.guard_samples, ctx.guard_kept_samples
    not_paper_samples, page1_samples = ctx.not_paper_samples, ctx.page1_samples
    per_pi = collections.Counter(r['pi'] for r in rows)
    for p in pis:
        p['oaAuthorIds'] = [a for a, _ in anchored[p['pi']].most_common()]
        p['funnel'] = dict(funnel[p['pi']], dblpTitles=len(dblp_title[p['pi']]), dblpDois=len(dblp_doi[p['pi']]), verifiedWorks=len(verified[p['pi']]))
        p['counts'] = dict(verifiedWorks=len(verified[p['pi']]), labPapers=per_pi[p['pi']], students=len(stu[p['pi']]),
                           studentPaperLinks=sum(1 for x in sp if x['pi'] == p['pi']))
    n['pis_with_lab_papers'] = sum(bool(per_pi[p['pi']]) for p in pis)
    n['pis_complete_chain'] = sum(bool(p['counts']['labPapers'] and p['counts']['students'] and p['counts']['studentPaperLinks']) for p in pis)
    atomic_json(out / 'pis.json', pis)
    atomic_json(out / 'students.json', {k: list(v.values()) for k, v in stu.items()})
    for r in rows:
        r.pop('_bylines', None)
    for name, data in (('lab_papers', rows), ('student_papers', sp)):
        with P.gzip_text(out / f'{name}.jsonl.gz') as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    rep = dict(school=school, builtAt=datetime.datetime.utcnow().isoformat() + 'Z', counts=dict(n), excluded=excluded,
               pisWithoutPapers=sorted(p['pi'] for p in pis if not per_pi[p['pi']]),
               pisWithoutStudents=sorted(p['pi'] for p in pis if not stu[p['pi']]), censusNicknameMerges=nick_merges,
               droppedProgramOrReaderOnly=weak_dropped, pisListedAsOwnStudent=self_listed, linkGuardSamples=guard_samples,
               linkGuardKeptVariantSamples=guard_kept_samples, notPaperSamples=dict(not_paper_samples),
               page1ElsewhereSamples=page1_samples, staleListingReview=ctx.listing_review, droppedWithoutHashedSource=ctx.unevidenced, labpageAdditionsSetAside=ctx.labpage_set_aside,
               provenance=provenance.block(school),
               studentInitialsMerges=ctx.initials_merges, studentSurnameTypoCandidates=students.typo_candidate_rows(ctx), labpageStudentsCorroborated=getattr(ctx, 'corroborated', []))  # what this package was built from (tools/provenance.py; make_release requires it)
    if getattr(ctx, 'member_paper_review', None) is not None:
        rep['memberPaperReview'] = ctx.member_paper_review
    if getattr(ctx, 'paper_title_review', None) is not None:
        rep['paperTitleReview'] = ctx.paper_title_review
    if getattr(ctx, 'paper_claim_review', None) is not None:
        rep['paperClaimReview'] = ctx.paper_claim_review
    if getattr(ctx, 'primary_affiliation_reviews', None):
        rep['primaryPDFAffiliationReviews'] = [value[1] for _, value in sorted(ctx.primary_affiliation_reviews.items())]
    atomic_json(out / 'report.json', rep)
    print(json.dumps(dict(school=school, **n)))


def build(school):
    out = P.data('pis.json', school, root=HERE).parent  # the package directory (derived)
    if os.environ.get('PI_HIERARCHY_OUT'):  # a trial build elsewhere (tests, rule measurements); the inputs stay where they are
        out = Path(os.environ['PI_HIERARCHY_OUT']) / school; out.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(school, out=out)
    census.load(ctx)
    census.reviewed_inputs(ctx)
    census.pi_records(ctx)
    census.index_pis(ctx)
    students.gather(ctx)
    identity.anchors(ctx)
    identity.hits(ctx)
    papers.lab_papers(ctx)
    reviewed_claims.apply(ctx)
    students.add_corroborated(ctx)  # R-STU-20
    links.link_students(ctx)
    students.drop_weak(ctx, ctx.sp)
    member_paper_reviews.apply(ctx)
    n, pis, stu, sp = ctx.n, ctx.pis, ctx.stu, ctx.sp
    # recount after the drops: the counts taken when the students were gathered still held the dropped pairs
    n['pis_with_students'] = sum(bool(stu[p['pi']]) for p in pis); n['students'] = len({s for v in stu.values() for s in v})
    n['lab_student_pairs'] = sum(len(v) for v in stu.values())
    n['student_paper_links'] = len(sp); n['labs_with_student_papers'] = len({x['pi'] for x in sp})
    n.update({'student_link:' + k: v for k, v in collections.Counter(x['basis'] for x in sp).items()})
    write(ctx)
