# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/epfl_infoscience_review.py (sha256 abb82e7af9893fc3919f64366f393ba03ea52b84f3ae463c711506b74bdb580b); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""EPFL publication identities and DOI candidates from Infoscience, replayed offline.

Chain for every identity: the reviewed EPFL unit-API head record (exact directory acronym,
explicit head object, direct scientific membership) gives the head's SCIPER, EPFL's
institutional person number. Infoscience, EPFL's institutional repository, must return
exactly one Person entity carrying that SCIPER and a compatible full name. Then either:

  epfl_infoscience_person_orcid_v1   the Person entity asserts one ORCID; the free OpenAlex
                                     authors/orcid: singleton must carry that ORCID, a
                                     compatible full name and EPFL in its history.
  epfl_infoscience_unit_anchor_v1    the Person entity asserts no ORCID. The unit's
                                     Infoscience publication listing anchors the author
                                     exactly as bibliography_anchor does for lab pages:
                                     every non-thesis DOI listed is resolved, and one
                                     full-name author must sit on at least half of them
                                     (and at least five), with no competing full-name
                                     profile above 20%. When the Person entity asserts
                                     OpenAlex author IDs, the anchored author must be
                                     one of them.

Infoscience assigns works to units through their authors' current units (the cris.virtual
fields), not the unit at publication time, and lists members' pre-EPFL works
(epfl.writtenAt OTHER). A unit listing therefore anchors an identity and supplies DOI
candidates for the strict PI-last-author view, but it is not a lab bibliography for the
broader reviewed view and not dated evidence that the unit existed. Current heads do not
establish historical tenure.

Infoscience captures stay in the EPFL unipapers stage (gzip, hashed as served). Person
records and OpenAlex singletons are seeded into the shared cache by the merge step.

CLI:  python scripts/epfl_infoscience_review.py fetch-directors
      python scripts/epfl_infoscience_review.py propose [LAB_ID ...]
"""
import csv, gzip, hashlib, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publications import ROOT, CUTOFF, Client, author_name_evidence, institution_ids, normalize_doi, sid
from author_name_matching import name_tokens

UID = 'swiss-federal-institute-of-technology-lausanne'
STAGE = ROOT / 'data/reviews/unipapers' / UID
INSTITUTION = 'https://openalex.org/I5124864'
PERSON_FORMAT = 'epfl_infoscience_person_orcid_v1'
ANCHOR_FORMAT = 'epfl_infoscience_unit_anchor_v1'
PERSON_URL = 'https://infoscience.epfl.ch/server/api/discover/search/objects?query=epfl.sciperId:{}&configuration=person'
LISTING_CONFIGURATION = 'RELATION.OrgUnit.publications'
PLACEHOLDER = '#PLACEHOLDER_PARENT_METADATA_VALUE#'
MIN_WORKS, MIN_SHARE, COMPETITOR_MAX_SHARE = 5, 0.5, 0.2


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stage_bytes(snapshot_path, sha256, gz=False):
    data = (ROOT / snapshot_path).read_bytes()
    if gz:
        data = gzip.decompress(data)
    require(hashlib.sha256(data).hexdigest() == sha256, 'Infoscience capture changed: ' + snapshot_path)
    return data


def values(item, key):
    return [v['value'] for v in item['metadata'].get(key, []) if v['value'] != PLACEHOLDER]


def search_objects(payload):
    result = payload['_embedded']['searchResult']
    return [o['_embedded']['indexableObject'] for o in result.get('_embedded', {}).get('objects', [])]


# ------------------------------------------------------------------ evidence readers

def person_entity(text, sciper, pi_name, uuid=''):
    """The single Infoscience Person with this exact SCIPER (search) or UUID (core item), and its identifiers."""
    payload = json.loads(text)
    if uuid:
        people = [payload] if payload.get('uuid') == uuid else []
    else:
        people = [p for p in search_objects(payload) if values(p, 'epfl.sciperId') == [str(sciper)]]
    require(len(people) == 1, 'Infoscience Person is not unique')
    person = people[0]
    require(person.get('entityType') == 'Person', 'Infoscience record is not a Person')
    heading = ' '.join(values(person, 'person.givenName') + values(person, 'person.familyName'))
    require(set(name_tokens(pi_name)) <= set(name_tokens(heading)), 'Infoscience Person name differs from the unit head')
    orcids = sorted({v.rsplit('/', 1)[-1].upper() for v in values(person, 'person.identifier.orcid')})
    openalex = sorted({'https://openalex.org/' + v.rsplit('/', 1)[-1].upper() for v in values(person, 'person.identifier.openalex')})
    return dict(uuid=person['uuid'], heading=heading, orcids=orcids, openalex=openalex,
                units=values(person, 'person.affiliation.name'), sciper=(values(person, 'epfl.sciperId') or [''])[0])


def listing_items(page, orgunit_uuid):
    """Items on one hash-pinned unit publication page, checked to be that unit's listing."""
    payload = json.loads(stage_bytes(page['snapshot_path'], page['sha256'], gz=True))
    href = payload['_links']['self']['href']
    require(f'scope={orgunit_uuid}' in href and f'configuration={LISTING_CONFIGURATION}' in href,
            'Capture is not this unit\'s Infoscience publication listing')
    return search_objects(payload)


def listed_dois(items, exclude_theses=False):
    found = {}
    for item in items:
        kind = (values(item, 'dc.type') or [''])[0]
        if exclude_theses and kind.startswith('thesis'):
            continue
        doi = normalize_doi((values(item, 'dc.identifier.doi') or [''])[0])
        if doi:
            found.setdefault(doi, item)
    return found


def leadership_head(lab_id, pi_name, leadership):
    rows = [r for r in leadership if r['lab_id'] == lab_id and r['evidence_format'] == 'epfl_unit_json_head'
            and name_tokens(r['person_name']) == name_tokens(pi_name)]
    require(len(rows) == 1, 'Reviewed EPFL unit-API head missing for ' + pi_name)
    return rows[0], json.loads(rows[0]['structured_evidence'])


ITEM_URL = 'https://infoscience.epfl.ch/server/api/core/items/{}'


def orgunit_director(page, orgunit_uuid):
    """The director (name + Person UUID) the pinned Infoscience OrgUnit record names."""
    payload = json.loads(stage_bytes(page['snapshot_path'], page['sha256'], gz=True))
    require('configuration=orgunit' in payload['_links']['self']['href'], 'Capture is not the OrgUnit listing')
    units = [u for u in search_objects(payload) if u['uuid'] == orgunit_uuid]
    require(len(units) == 1, 'OrgUnit absent from the pinned page')
    directors = [d for d in units[0]['metadata'].get('crisou.director', []) if d['value'] != PLACEHOLDER]
    require(len(directors) == 1 and directors[0].get('authority'), 'OrgUnit has no single linked director')
    return directors[0]['value'], directors[0]['authority']


def same_person_name(a, b):
    return sorted(name_tokens(a)) == sorted(name_tokens(b))


# ------------------------------------------------------------------ replay (pipeline hooks)

def check_head(review, lab, lab_evidence, client):
    """Tie the Infoscience Person to the reviewed leader: exact unit-API SCIPER, or the matched
    OrgUnit's linked director carrying exactly the reviewed leader's full name."""
    from publications import read_csv
    if review.get('head_link', 'unit_api_sciper') == 'unit_api_sciper':
        row, head = leadership_head(lab['lab_id'], review['pi_name'], read_csv(ROOT / 'data/processed/leadership_evidence.csv'))
        require(lab_evidence['pi_lab_evidence_source_id'] == row['source_id'], 'Identity is not tied to the unit-API head record')
        require(str(head['head_sciper']) == str(review['head_sciper']), 'Head SCIPER differs from the review')
        require(review['identity_evidence_url'] == PERSON_URL.format(review['head_sciper']), 'Person lookup is not by exact SCIPER')
        uuid = ''
    else:
        require(review['head_link'] == 'infoscience_orgunit_director', 'Unknown leader link')
        name, uuid = orgunit_director(review['orgunit_page'], review['orgunit_uuid'])
        require(uuid == review['infoscience_person_uuid'] and same_person_name(name, review['pi_name']),
                'OrgUnit director is not the reviewed leader')
        require(review['identity_evidence_url'] == ITEM_URL.format(uuid), 'Person lookup is not the linked director')
    text, meta = client.fetch(review['identity_evidence_url'])
    require(meta['sha256'] == review['identity_profile_sha256'], 'Infoscience Person record changed')
    return person_entity(text, review.get('head_sciper', ''), review['pi_name'], uuid), meta


def verify_author(author, review):
    names = author_name_evidence(author, review['profile_name_tokens'])
    require(names, 'OpenAlex author name incompatible with the unit head')
    require(review['openalex_institution_id'] in institution_ids(author), 'EPFL absent from OpenAlex author history')
    return names


def anchor(review, client):
    """Re-derive the anchored author from the pinned unit listing; raise on weak or changed evidence."""
    listed = {}
    for page in review['listing_pages']:
        listed.update(listed_dois(listing_items(page, review['orgunit_uuid']), exclude_theses=True))
    require(set(review['anchor_dois']) | set(review['unresolved_dois']) == set(listed), 'Anchor set is not the full non-thesis listing')
    require(not set(review['anchor_dois']) & set(review['unresolved_dois']), 'Anchor and unresolved sets overlap')
    from bibliography_anchor import work_by_doi, unique_works, tally
    works = unique_works([work_by_doi(client, doi)[0] for doi in review['anchor_dois']])
    ranked = tally(works, review['profile_name_tokens'])
    require(ranked, 'No full-name byline on the listed works')
    primary, hits = ranked[0]
    require(hits >= MIN_WORKS and hits / len(works) >= MIN_SHARE, f'Anchor too weak: {hits} of {len(works)} listed works')
    require(all(n / len(works) < COMPETITOR_MAX_SHARE for _, n in ranked[1:]), 'A competing full-name author profile appears on the listed works')
    return primary, hits, len(works), ranked[1:4]


def identity_row(review, lab, lab_evidence, client):
    fmt = review.get('identity_evidence_format')
    require(fmt in {PERSON_FORMAT, ANCHOR_FORMAT} and review.get('review_status') == 'accepted', 'Not an accepted Infoscience review')
    require(lab['university_id'] == UID == review['university_id'] and review['openalex_institution_id'] == INSTITUTION, 'Not an EPFL review')
    person, person_meta = check_head(review, lab, lab_evidence, client)
    if fmt == PERSON_FORMAT:
        require(person['orcids'] == [review['orcid']], 'Infoscience Person does not assert exactly this ORCID')
        author, source = client.api('authors/orcid:' + review['orcid'])
        require((author.get('orcid') or '').rsplit('/', 1)[-1] == review['orcid'], 'ORCID singleton returned another ORCID')
        require(not person['openalex'] or author['id'] in person['openalex'], 'ORCID profile differs from the OpenAlex ID Infoscience asserts')
        scope, status = 'single_profile_only_alias_review_pending', 'verified_institutional_repository_orcid'
        method = 'reviewed_EPFL_unit_head_SCIPER_to_Infoscience_Person_ORCID_matches_OpenAlex'
        note = 'Infoscience Person (exact SCIPER of the reviewed unit head) asserts this ORCID.'
    else:
        require(not person['orcids'], 'Person asserts an ORCID; the ORCID route applies')
        primary, hits, total, competitors = anchor(review, client)
        require(primary == review['openalex_author_id'], 'Anchored author differs from the review')
        require(person['openalex'] == review['infoscience_openalex_ids'], 'Infoscience OpenAlex assertion changed')
        require(not person['openalex'] or primary in person['openalex'], 'Anchored author differs from the OpenAlex ID Infoscience asserts')
        author, source = client.api('authors/' + primary.rsplit('/', 1)[-1])
        require(author['id'] == primary, 'Author lookup returned a different profile')
        require((author.get('orcid') or '').rsplit('/', 1)[-1] == review.get('orcid', ''), 'OpenAlex ORCID differs from the review')
        scope, status = 'bibliography_anchor_primary_profile_only', 'verified_official_repository_unit_bibliography_anchor'
        method = 'reviewed_EPFL_unit_head_SCIPER_Infoscience_Person_and_unit_publication_list_anchor_matches_OpenAlex'
        note = (f'Anchor: {hits} of {total} works on the unit\'s Infoscience list'
                + (' ; matches the OpenAlex ID Infoscience asserts.' if person['openalex'] else '; Infoscience asserts no OpenAlex ID.'))
    require(author['id'] == review['openalex_author_id'], 'OpenAlex author differs from the review')
    names = verify_author(author, review)
    orcid = review.get('orcid', '')
    return dict(identity_id=sid('pi', lab['lab_id'] + '|' + (orcid or author['id'])), lab_id=lab['lab_id'],
                university_id=lab['university_id'], pi_name=review['pi_name'], openalex_author_id=author['id'],
                orcid='https://orcid.org/' + orcid if orcid else '', openalex_author_aliases=json.dumps([author['id']]),
                author_alias_review_scope=scope, openalex_name_evidence=json.dumps({author['id']: names}, ensure_ascii=False),
                openalex_institution_id=review['openalex_institution_id'], identity_status=status, identity_method=method,
                **lab_evidence, identity_evidence_url=review['identity_evidence_url'],
                identity_evidence_snapshot=person_meta['snapshot_path'], identity_registry_url='', identity_registry_snapshot='',
                identity_registry_sha256='', author_evidence_snapshot=source['snapshot_path'], observed_on=CUTOFF,
                notes=review.get('notes') or note)




# ------------------------------------------------------------------ proposal building

def stage_captures():
    out = {}
    for line in (STAGE / 'sources.jsonl').open():
        meta = json.loads(line)
        out[meta['requested_url']] = meta
    return out


def listing_pages(orgunit_uuid, captures):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import epfl_infoscience as E
    metas = E.listing_metas(orgunit_uuid, captures)
    return None if metas is None else [dict(url=m['requested_url'], sha256=m['sha256'], snapshot_path=m['snapshot_path']) for m in metas]


def orgunit_page(orgunit_uuid, pages):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import epfl_infoscience as E
    for meta in pages:
        if any(u['uuid'] == orgunit_uuid for u in E.objects(meta)):
            return dict(url=meta['requested_url'], sha256=meta['sha256'], snapshot_path=meta['snapshot_path'])
    return None


def head_link(lab_id, leadership, match, orgunit_pages):
    """How the reviewed leader reaches an Infoscience Person, or the reason it cannot."""
    heads = [r for r in leadership if r['lab_id'] == lab_id and r['evidence_format'] == 'epfl_unit_json_head']
    if len(heads) > 1:
        return 'multiple_unit_heads'
    if heads:
        sciper = str(json.loads(heads[0]['structured_evidence'])['head_sciper'])
        return dict(head_link='unit_api_sciper', pi_name=heads[0]['person_name'], head_sciper=sciper,
                    identity_evidence_url=PERSON_URL.format(sciper), pi_lab_evidence_source_id=heads[0]['source_id'])
    reviewed = [r for r in leadership if r['lab_id'] == lab_id]
    if not reviewed:
        return 'no_reviewed_leader'
    if match.get('status') != 'matched':
        return 'reviewed_leader_but_unit_not_in_infoscience'
    page = orgunit_page(match['orgunit_uuid'], orgunit_pages)
    try:
        name, uuid = orgunit_director(page, match['orgunit_uuid'])
    except (ValueError, TypeError):
        return 'reviewed_leader_but_orgunit_has_no_linked_director'
    same = [r for r in reviewed if same_person_name(r['person_name'], name)]
    if len(same) != 1:
        return 'orgunit_director_is_not_a_reviewed_leader'
    return dict(head_link='infoscience_orgunit_director', pi_name=same[0]['person_name'], orgunit_uuid=match['orgunit_uuid'],
                orgunit_page=page, infoscience_person_uuid=uuid, identity_evidence_url=ITEM_URL.format(uuid),
                pi_lab_evidence_source_id=same[0]['source_id'])


def fetch_directors():
    """Capture the Person record for every director link propose() will need."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import epfl_infoscience as E
    import unipapers_lib as U
    from publications import read_csv
    leadership = read_csv(ROOT / 'data/processed/leadership_evidence.csv')
    matches = {r['lab_id']: r for r in json.loads((E.OUT / 'unit_matches.json').read_text())}
    pages = [m for u, m in E.captured().items() if 'configuration=orgunit' in u]
    have = stage_captures()
    for lab_id, match in sorted(matches.items()):
        link = head_link(lab_id, leadership, match, pages)
        if isinstance(link, dict) and link['head_link'] == 'infoscience_orgunit_director' and link['identity_evidence_url'] not in have:
            r = U.fetch(UID, link['identity_evidence_url'])
            print(lab_id, link['pi_name'], r.get('status'), flush=True)


class StageClient(Client):
    """Stage cache client that reads the person capture made by unipapers_lib.fetch."""
    def __init__(self, person_captures):
        super().__init__(out=STAGE)
        self.person_captures = person_captures

    def fetch(self, url, params=None):
        if url in self.person_captures and not params:
            meta = self.person_captures[url]
            return (ROOT / meta['snapshot_path']).read_bytes().decode('utf-8'), meta
        return super().fetch(url, params)


def propose(only=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import epfl_infoscience as E
    from bibliography_anchor import work_by_doi
    from publications import read_csv, lab_identity_evidence
    labs = {r['lab_id']: r for r in read_csv(ROOT / 'data/processed/labs.csv') if r['university_id'] == UID}
    leadership = read_csv(ROOT / 'data/processed/leadership_evidence.csv')
    sources = {r['source_id']: r for r in read_csv(ROOT / 'data/processed/sources.csv')}
    verified = {r['lab_id'] for r in read_csv(ROOT / 'data/publications/pi_identities.csv')}
    matches = {r['lab_id']: r for r in json.loads((E.OUT / 'unit_matches.json').read_text())}
    listing_captures = E.captured()
    orgunit_pages = [m for u, m in listing_captures.items() if 'configuration=orgunit' in u]
    person_captures = stage_captures()
    client = StageClient(person_captures)
    identities, gaps = [], []
    for lab_id, lab in sorted(labs.items()):
        if only and lab_id not in only:
            continue
        match = matches.get(lab_id, {})
        pages = listing_pages(match['orgunit_uuid'], listing_captures) if match.get('status') == 'matched' else None
        if lab_id in verified:
            continue
        link = head_link(lab_id, leadership, match, orgunit_pages)
        if isinstance(link, str):
            gaps.append(dict(lab_id=lab_id, reason=link)); continue
        pi_name, url = link['pi_name'], link['identity_evidence_url']
        if url not in person_captures:
            gaps.append(dict(lab_id=lab_id, pi_name=pi_name, reason='infoscience_person_not_captured')); continue
        meta = person_captures[url]
        try:
            person = person_entity(stage_bytes(meta['snapshot_path'], meta['sha256']).decode('utf-8'),
                                   link.get('head_sciper', ''), pi_name, link.get('infoscience_person_uuid', ''))
        except ValueError as e:
            gaps.append(dict(lab_id=lab_id, pi_name=pi_name, reason='infoscience_person: ' + str(e))); continue
        base = dict(link, lab_id=lab_id, university_id=UID, profile_name_tokens=pi_name.split(),
                    identity_profile_sha256=meta['sha256'], openalex_institution_id=INSTITUTION,
                    infoscience_person_uuid=person['uuid'], review_status='accepted', reviewed_on=CUTOFF)
        try:
            if len(person['orcids']) > 1:
                raise ValueError('Infoscience Person asserts several ORCIDs')
            if person['orcids']:
                review = dict(base, identity_evidence_format=PERSON_FORMAT, orcid=person['orcids'][0])
                author, _ = client.api('authors/orcid:' + review['orcid'])
                review['openalex_author_id'] = author['id']
                if person['openalex'] and author['id'] not in person['openalex']:
                    raise ValueError('ORCID profile differs from the OpenAlex ID Infoscience asserts (possible split profile)')
            else:
                if not pages:
                    raise ValueError('No captured Infoscience unit listing to anchor on')
                listed = {}
                for p in pages:
                    listed.update(listed_dois(listing_items(p, match['orgunit_uuid']), exclude_theses=True))
                resolved, unresolved = [], []
                for doi in sorted(listed):
                    try:
                        work_by_doi(client, doi); resolved.append(doi)
                    except (RuntimeError, ValueError, FileNotFoundError):
                        unresolved.append(doi)
                review = dict(base, identity_evidence_format=ANCHOR_FORMAT, orgunit_uuid=match['orgunit_uuid'],
                              listing_pages=pages, anchor_dois=resolved, unresolved_dois=unresolved,
                              infoscience_openalex_ids=person['openalex'],
                              anchor_thresholds=dict(min_works=MIN_WORKS, min_share=MIN_SHARE, competitor_max_share=COMPETITOR_MAX_SHARE))
                primary, hits, total, competitors = anchor(review, client)
                author, _ = client.api('authors/' + primary.rsplit('/', 1)[-1])
                review.update(openalex_author_id=primary, orcid=(author.get('orcid') or '').rsplit('/', 1)[-1],
                              anchor_stats=dict(hits=hits, works=total, competitors=competitors))
            lab_evidence = lab_identity_evidence(review, lab, sources, leadership)
            row = identity_row(review, lab, lab_evidence, client)
            review['notes'] = row['notes']
            identities.append(review)
        except (ValueError, RuntimeError, FileNotFoundError, KeyError) as e:
            gaps.append(dict(lab_id=lab_id, pi_name=pi_name, reason=str(e)[:200]))
    # DOI candidates for the strict view: every DOI on the unit listing of a proposed identity.
    proposed = {r['lab_id'] for r in identities}
    discovery = [dict(lab_id=r['lab_id'], doi=r['doi'], item_uuid=r['item_uuid'], issued=r['issued'],
                      source_id=r['source_id'], source_sha256=r['source_sha256'])
                 for r in E.publication_rows() if r['lab_id'] in proposed and r['doi']]
    out = dict(identities=identities, discovery=discovery, gaps=gaps)
    if only:
        for r in identities:
            print('ID', r['lab_id'], r['pi_name'], r['identity_evidence_format'], r.get('orcid') or '-', r['openalex_author_id'], '|', r['notes'][:110])
        for g in gaps:
            print('GAP', g['lab_id'], g.get('pi_name', ''), '|', g['reason'][:150])
        print('discovery DOIs', len({d['doi'] for d in discovery}))
        return
    tmp = STAGE / 'proposals.json.part'
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    tmp.replace(STAGE / 'proposals.json')
    print(json.dumps(dict(identities=len(identities), by_format=Counter(r['identity_evidence_format'] for r in identities),
                          discovery_dois=len({d['doi'] for d in discovery}),
                          gaps=len(gaps), gap_reasons=Counter(g['reason'].split(':')[0][:70] for g in gaps).most_common(12)),
                     default=str, indent=1))


if __name__ == '__main__':
    if sys.argv[1:2] == ['propose']:
        propose(set(sys.argv[2:]) or None)
    elif sys.argv[1:] == ['fetch-directors']:
        fetch_directors()
    else:
        print(__doc__)
