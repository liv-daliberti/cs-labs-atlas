"""Per-PI filtering of the school-wide derived files of a partial release (Q-0340, owner 2026-11-18; docs/PER-PI-ADMISSION.md).

A per-PI release (tools/pi_release.py) filters the five package files to the included PIs. Every other file a release copies is
built for the whole school and still names the held PIs. This module restricts them to the included PIs, deterministically, so
`make_release --per-pi` no longer needs --allow-derived-unfiltered:

  report.json                    per-PI lists (excluded, pisWithoutPapers, samples, reviews ...) lose the held PIs; counts stay the school-wide build
                                 counts (make_release recounts the release counts for the included PIs); `scope` says so
  unavailable.jsonl.gz / -summary.json   rows of the included PIs' papers; the summary is recounted from them
  link-diagnosis.json            students of held PIs dropped; the summary recounted by category
  reader/<school>.jsonl.gz       rows of the included PIs' papers; hosted-files.tsv keeps a file only while a kept row hosts it; upload.tsv,
                                 unpublish.tsv, link-check-requests.tsv and SUMMARY.json follow
  home-departments.json, zero-paper-labs.json, school-profiles.json (+ SCHOOL-PROFILES.md), missing-papers-audit.json, chain-audit.json
  (+ CHAIN-AUDIT.md), student-audit.json     the partial school's entry loses every record that names a held PI; school-profiles is the
                                 school_profiles.profile of the filtered package

A record names a held PI when it is that name, a dict whose `pi` (or `key`, `<pi> | <student>`) is that name, or a list that holds that name. A name that is
also an included PI of the school is never treated as held. `leaks()` re-applies the test to the output and must find nothing. Only the school's own
entry is touched: another school's PI of the same name stays.

  filter_release_files(per, sources) -> {release path: bytes} for the files that must be rewritten (empty when no school is partial)
"""
import collections
import gzip
import io
import json
import shutil
import tempfile
from pathlib import Path

import atlas_paths as P  # noqa: E402

SCOPE = 'partial release: per-PI lists restricted to the included PIs; other figures are school-wide'


def held_names(plan):
    return set(plan['held']) - set(plan['included'])


def named(item, held):
    """True when `item` (a record) names a held PI."""
    if isinstance(item, str):
        return item in held
    if isinstance(item, dict):
        pi = item.get('pi')
        if isinstance(pi, str) and pi in held:
            return True
        k = item.get('key')
        return isinstance(k, str) and (k in held or k.split(' | ')[0] in held)
    if isinstance(item, (list, tuple)):
        return any(isinstance(x, str) and x in held for x in item)
    return False


def drop(obj, held):
    """`obj` without the records that name a held PI (lists, dict values, dict keys), recursively; `n_unexplained` follows its list."""
    if isinstance(obj, list):
        return [drop(x, held) for x in obj if not named(x, held)]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and k in held:
                continue
            if isinstance(v, dict) and named(v, held):
                continue
            out[k] = drop(v, held)
        if isinstance(out.get('unexplained'), list) and 'n_unexplained' in out:
            out['n_unexplained'] = len(out['unexplained'])
        return out
    return obj


def leaks(obj, held):
    """Records of `obj` that still name a held PI (the check of the output; empty when the filter is complete)."""
    found = []

    def walk(o):
        if isinstance(o, list):
            for x in o:
                found.append(x) if named(x, held) else walk(x)
        elif isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str) and k in held or (isinstance(v, dict) and named(v, held)):
                    found.append({k: v})
                else:
                    walk(v)
    walk(obj)
    return found


def dumps(o):
    return (json.dumps(o, indent=1, ensure_ascii=False) + '\n').encode()


def gz_lines(rows):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0) as g:
        for r in rows:
            g.write((json.dumps(r, ensure_ascii=False) + '\n').encode())
    return buf.getvalue()


def read_gz_lines(path_or_bytes):
    f = gzip.open(path_or_bytes, 'rt') if not isinstance(path_or_bytes, bytes) else gzip.open(io.BytesIO(path_or_bytes), 'rt')
    with f:
        return [json.loads(l) for l in f if l.strip()]


# --- one school -----------------------------------------------------------------------------------------------------------------------------

def paper_keys(school, included):
    """The OpenAlex ids of the included PIs' lab papers."""
    import pi_release as PR
    return {r['oa'] for r in PR.filtered_rows_and_json(school, 'lab_papers.jsonl.gz', included)}


def filter_report(rep, held):
    keep = {k: rep[k] for k in ('provenance', 'counts') if k in rep}
    out = drop({k: v for k, v in rep.items() if k not in keep}, held)
    out = {k: (keep[k] if k in keep else out[k]) for k in rep if k in keep or k in out}
    out['scope'] = SCOPE
    return out


def ledger_summary(summ, rows):
    """The unavailability summary recounted from the kept rows exactly as fulltext-push/unavailable_ledger.py writes it (top 40 publishers,
    top 15 per reason); inputs, built_at and the other keys stay."""
    by_r = collections.Counter(r['reason_code'] for r in rows)
    by_p = collections.Counter(r['publisher'] for r in rows)
    by_rp = collections.defaultdict(collections.Counter)
    for r in rows:
        by_rp[r['reason_code']][r['publisher']] += 1
    out = dict(summ)
    out.update(papers=len(rows), by_reason=dict(by_r.most_common()), by_publisher=dict(by_p.most_common(40)),
               by_reason_publisher={k: dict(v.most_common(15)) for k, v in by_rp.items()},
               final=sum(1 for r in rows if r['final']), not_final=sum(1 for r in rows if not r['final']),
               missing_checks=dict(collections.Counter(m for r in rows for m in r['missing_checks']).most_common()), scope=SCOPE)
    return out


def filter_link_diagnosis(ld, held):
    out = drop(ld, held)
    cats = collections.Counter(v.get('category') for v in (out.get('students') or {}).values())
    summ = dict(out.get('summary') or {})
    for k in list(summ):
        if k in cats or isinstance(summ[k], int) and k in {v.get('category') for v in (ld.get('students') or {}).values()}:
            summ[k] = cats.get(k, 0)
    out['summary'] = summ
    return out


# --- the shared files ------------------------------------------------------------------------------------------------------------------------

def per_school(entries, per, key='school'):
    """Apply `drop` to the entries of the partial schools only (a list of dicts with a `school`)."""
    out = []
    for e in entries:
        pl = (per.get(e.get(key)) or {}).get('plan') if isinstance(e, dict) else None
        out.append(dict(drop(e, held_names(pl)), scope=SCOPE) if pl and pl['partial'] else e)
    return out


def filter_home_departments(rows, per):
    out = []
    for r in rows:
        pl = (per.get(r.get('school')) or {}).get('plan')
        if pl and pl['partial'] and r.get('name') in held_names(pl):
            continue
        out.append(r)
    return out


def filter_zero_paper_labs(z, per):
    out = dict(z)
    partial = {s: held_names(v['plan']) for s, v in per.items() if v['plan']['partial']}
    out['zero_papers'] = [r for r in z['zero_papers'] if r['pi'] not in partial.get(r['school'], ())]
    out['zero_students'] = [r for r in z['zero_students'] if r['pi'] not in partial.get(r['school'], ())]
    counts = {k: v for k, v in (z.get('counts') or {}).items() if k.split(':')[0] not in partial}
    for s in partial:
        for r in out['zero_papers']:
            if r['school'] == s:
                counts[f"{s}:zero_papers:{r['verdict']}"] = counts.get(f"{s}:zero_papers:{r['verdict']}", 0) + 1
        n = sum(1 for r in out['zero_students'] if r['school'] == s)
        if n:
            counts[f'{s}:zero_students'] = n
    out['counts'] = dict(sorted(counts.items()))
    return out


def filtered_profile(school, per, homes, audit, zero):
    """school_profiles.profile of the filtered package (a flat copy of the five files, the report counts recounted for the included PIs)."""
    import pi_release as PR
    import school_profiles as SP
    inc = per[school]['plan']['included']
    tmp = Path(tempfile.mkdtemp(prefix=f'pi-profile-{school}-'))
    try:
        d = tmp / 'hierarchy' / school
        d.mkdir(parents=True)
        for f in ('pis.json', 'students.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz', 'copies.json'):
            (d / f).write_bytes(PR.filtered_bytes(school, f, inc, held=PR.held_set(per[school]['plan'])))
        rep = json.loads(P.data('report.json', school).read_text())
        pis = json.loads((d / 'pis.json').read_text())
        stu = json.loads((d / 'students.json').read_text())
        lp = {r['pi'] for r in read_gz_lines(d / 'lab_papers.jsonl.gz')}
        sp = {r['pi'] for r in read_gz_lines(d / 'student_papers.jsonl.gz')}
        c = dict(rep.get('counts') or {})
        c.update(pis=len(pis), pis_with_students=sum(1 for p in pis if stu.get(p['pi'])), pis_with_lab_papers=len(lp),
                 pis_complete_chain=sum(1 for p in pis if p['pi'] in lp and stu.get(p['pi']) and p['pi'] in sp))
        (d / 'report.json').write_text(json.dumps(dict(counts=c)))
        add = P.data('census-additions.json', school)
        if add.exists():
            (tmp / 'census').mkdir()
            shutil.copy(add, tmp / 'census' / f'{school}-additions.json')
        old_h, SP.H = SP.H, tmp / 'hierarchy'
        try:
            return SP.profile(school, homes, audit, zero)
        finally:
            SP.H = old_h
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- reader ----------------------------------------------------------------------------------------------------------------------------------

def _tsv(text):
    lines = text.rstrip('\n').split('\n')
    return lines[0], [l.split('\t') for l in lines[1:] if l]


def _tsv_out(head, rows):
    return ('\n'.join([head] + ['\t'.join(r) for r in rows]) + '\n').encode()


def filter_reader(per, sources, read_bytes):
    """{reader/<name>: bytes} for the reader export restricted to the partial schools' included PIs."""
    partial = {s: v for s, v in per.items() if v['plan']['partial']}
    out, rows_kept, rows_all = {}, {}, {}
    schools = [s for s in per if f'reader/{s}.jsonl.gz' in sources]
    for s in schools:
        rows = read_gz_lines(read_bytes(f'reader/{s}.jsonl.gz'))
        rows_all[s] = rows
        if s in partial:
            oas = paper_keys(s, partial[s]['plan']['included'])
            rows = [r for r in rows if r.get('oa') in oas or r.get('key') in oas]
            out[f'reader/{s}.jsonl.gz'] = gz_lines(rows)
        rows_kept[s] = rows
    needed = {r['sha256'] for rows in rows_kept.values() for r in rows if r.get('decision') == 'host' and r.get('sha256')}
    all_hosted = {r['sha256']: r for rows in rows_all.values() for r in rows if r.get('decision') == 'host' and r.get('sha256')}
    removed = set()
    if 'reader/hosted-files.tsv' in sources:
        head, rows = _tsv(read_bytes('reader/hosted-files.tsv').decode())
        keep = [r for r in rows if r[0] in needed or (r[2] not in partial)]
        removed = {r[0] for r in rows} - {r[0] for r in keep}
        out['reader/hosted-files.tsv'] = _tsv_out(head, keep)
    hosted_n = None
    if 'reader/hosted-files.tsv' in out:
        hosted_n = len(_tsv(out['reader/hosted-files.tsv'].decode())[1])
    upload_removed = set()
    if 'reader/upload.tsv' in sources:
        head, rows = _tsv(read_bytes('reader/upload.tsv').decode())
        keep = [r for r in rows if r[0] not in removed]
        upload_removed = {r[0] for r in rows} - {r[0] for r in keep}
        out['reader/upload.tsv'] = _tsv_out(head, keep)
    if 'reader/unpublish.tsv' in sources:
        head, rows = _tsv(read_bytes('reader/unpublish.tsv').decode())
        have = {r[0] for r in rows}
        for sha in sorted(removed - upload_removed - have):   # the site hosts it today and the filtered release no longer carries it
            r = all_hosted.get(sha) or {}
            rows.append([sha, str(r.get('bytes') or ''), r.get('path') or '', 'outside_release', str(r.get('license')), str(r.get('license_basis')),
                         str(r.get('school') or ''), str(r.get('catalog_work') or '')])
        out['reader/unpublish.tsv'] = _tsv_out(head, rows)
    lc = None
    if 'reader/link-check-requests.tsv' in sources:
        head, rows = _tsv(read_bytes('reader/link-check-requests.tsv').decode())
        keys = {s: paper_keys(s, v['plan']['included']) for s, v in partial.items()}
        rows = [r for r in rows if r[1] not in keys or r[2] in keys[r[1]]]
        lc = rows
        out['reader/link-check-requests.tsv'] = _tsv_out(head, rows)
    if 'reader/SUMMARY.json' in sources:
        summ = json.loads(read_bytes('reader/SUMMARY.json'))
        for s in partial:
            if s not in summ.get('schools', {}):
                continue
            rows = rows_kept[s]
            n_lab = len(paper_keys(s, partial[s]['plan']['included']))
            sc = dict(summ['schools'][s])
            by = collections.Counter(f"{r['decision']}:{r.get('license')}" for r in rows)
            sc.update(lab_papers=n_lab, readable=len(rows), not_readable=n_lab - len(rows), host=sum(1 for r in rows if r['decision'] == 'host'),
                      link=sum(1 for r in rows if r['decision'] == 'link'), confirmed_copies=sum(1 for r in rows if r.get('stored_copy')),
                      by_license=dict(sorted(by.items())), by_license_basis=dict(sorted(collections.Counter(r.get('license_basis') for r in rows).items())),
                      link_by_basis=dict(sorted(collections.Counter(r.get('link_basis') for r in rows if r['decision'] == 'link').items())),
                      newly_readable_from_candidates=sum(1 for r in rows if r.get('link_basis') in ('arxiv_id_doi', 'openalex_location', 'arxiv_metadata', 'landing_page_metadata')),
                      link_check_requests=sum(1 for r in (lc or []) if r[1] == s), not_readable_with_open_candidate=None, scope=SCOPE)
            summ['schools'][s] = sc
        tot = collections.Counter()
        for sc in summ['schools'].values():
            for k in ('confirmed_copies', 'host', 'lab_papers', 'link', 'not_readable', 'readable'):
                tot[k] += sc.get(k) or 0
        summ['totals'] = dict(tot)
        if hosted_n is not None:
            summ['hosted_files'] = hosted_n
        if lc is not None:
            summ['link_check_request_urls'] = len(lc)
            summ['link_check_request_hosts'] = dict(sorted(collections.Counter(r[0] for r in lc).items()))
        up = _tsv(out['reader/upload.tsv'].decode())[1] if 'reader/upload.tsv' in out else None
        un = _tsv(out['reader/unpublish.tsv'].decode())[1] if 'reader/unpublish.tsv' in out else None
        if up is not None and un is not None and 'site_sync' in summ:
            ss = dict(summ['site_sync'])
            ss.update(upload=len(up), unpublish=len(un), unpublish_by_reason=dict(sorted(collections.Counter(r[3] for r in un).items())),
                      keep=max((hosted_n or 0) - len(up), 0))
            summ['site_sync'] = ss
        out['reader/SUMMARY.json'] = (json.dumps(summ, indent=1, sort_keys=True) + '\n').encode()
    return out


# --- the release ------------------------------------------------------------------------------------------------------------------------------

def filter_release_files(per, sources, read_bytes=None):
    """{release path: bytes} of every school-wide file of a partial per-PI release, restricted to the included PIs. `per` is
    make_release.per_pi_plans; `sources` {release path: source file} (make_release.release_sources). {} when no school is partial."""
    partial = {s: v for s, v in per.items() if v['plan']['partial']}
    if not partial:
        return {}
    rb = read_bytes or (lambda rel: Path(sources[rel]).read_bytes())
    out = {}
    for s, v in partial.items():
        held, inc = held_names(v['plan']), v['plan']['included']
        rel = lambda name: PR_rel(name, s)   # noqa: E731
        p = rel('report.json')
        out[p] = dumps(filter_report(json.loads(rb(p)), held))
        oas = paper_keys(s, inc)
        lp, ls = rel('unavailable.jsonl.gz'), rel('unavailable-summary.json')
        if lp in sources:
            rows = [r for r in read_gz_lines(rb(lp)) if r.get('key') in oas]
            out[lp] = gz_lines(rows)
            if ls in sources:
                out[ls] = dumps(ledger_summary(json.loads(rb(ls)), rows))
        ld = rel('link-diagnosis.json')
        if ld in sources:
            out[ld] = dumps(filter_link_diagnosis(json.loads(rb(ld)), held))
    out.update(filter_reader(per, sources, rb))
    jh = PR_rel('home-departments.json')
    if jh in sources:
        out[jh] = dumps(filter_home_departments(json.loads(rb(jh)), per))
    zl = PR_rel('zero-paper-labs.json')
    zero = filter_zero_paper_labs(json.loads(rb(zl)), per) if zl in sources else None
    if zero is not None:
        out[zl] = dumps(zero)
    for name in ('missing-papers-audit.json', 'student-audit.json'):
        f = PR_rel(name)
        if f in sources:
            out[f] = dumps(per_school(json.loads(rb(f)), per))
    ca = PR_rel('chain-audit.json')
    if ca in sources:
        doc = json.loads(rb(ca))
        doc['schools'] = per_school(doc['schools'], per)
        out[ca] = dumps(doc)
        import chain_audit as CA
        if PR_rel('CHAIN-AUDIT.md') in sources:
            out[PR_rel('CHAIN-AUDIT.md')] = CA.md(doc).encode()
    sp = PR_rel('school-profiles.json')
    if sp in sources:
        homes = collections.defaultdict(dict)
        for r in json.loads(out.get(jh) or rb(jh)):
            if r.get('status') == 'accepted' and r.get('home_department'):
                homes[r['school']][r['name']] = r
        audit = json.loads(out.get(PR_rel('missing-papers-audit.json')) or rb(PR_rel('missing-papers-audit.json')))
        profs = json.loads(rb(sp))
        profs = [dict(filtered_profile(e['school'], per, homes, audit, zero), scope=SCOPE) if e['school'] in partial else e for e in profs]
        out[sp] = dumps(profs)
        if PR_rel('SCHOOL-PROFILES.md') in sources:
            import school_profiles as SP
            out[PR_rel('SCHOOL-PROFILES.md')] = SP.md(profs).encode()
    shared = {PR_rel(n) for n in ('home-departments.json', 'zero-paper-labs.json', 'chain-audit.json', 'student-audit.json', 'school-profiles.json', 'missing-papers-audit.json')}
    for path, data in out.items():
        if not path.endswith('.json') or path.startswith('reader/'):
            continue
        doc = json.loads(data)
        for s, v in partial.items():
            held = held_names(v['plan'])
            if path in shared:   # one entry per school (or rows with a `school`): only the partial school's own records are tested
                rows = doc['schools'] if isinstance(doc, dict) and 'schools' in doc else doc
                if isinstance(doc, dict) and 'zero_papers' in doc:
                    rows = doc['zero_papers'] + doc['zero_students']
                doc_s = [e for e in rows if isinstance(e, dict) and e.get('school') == s]
            else:
                doc_s = doc if f'/{s}/' in '/' + path else None
            if doc_s is not None and path.startswith('hierarchy/') and f'/{s}/' not in '/' + path and path not in shared:
                continue
            if doc_s is not None:
                assert not leaks(doc_s, held), f'{path}: still names a held PI of {s}'
    return out


def PR_rel(name, school=None):
    """The release-relative (flat) path of a data file (make_release.rel_of)."""
    head, _, rest = name.partition('/')
    return (P.data(head, school, root=Path('.'), layout='flat') / rest).as_posix()
