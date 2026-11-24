"""An exact repository author authority supports one public mononym; no name-only joins."""
import collections
import copy
import hashlib
import json
import sqlite3
import zlib

import pytest

import atlas_ids as A
from test_atlas_ids import pi, stu, write

URL = ('https://infoscience.epfl.ch/server/api/discover/search/objects?query=dc.type%3A%22thesis%3A%3Adoctoral+thesis%22'
       '&dsoType=ITEM&size=100&page=3&f.dateIssued=%5B2023+TO+2023%5D%2Cequals&sort=dc.date.accessioned%2CASC')
AUTHOR = dict(value='Vidit', language=None, authority='68cb81ee-a70a-46b9-807d-ca48ac423c6f', confidence=600, place=0)
ADVISERS = [dict(value='Fua, Pascal', language=None, authority='26ee9199-5a82-4097-90f0-e9eb052de875', confidence=600, place=0),
            dict(value='Salzmann, Mathieu', language=None, authority='191ffa93-13b8-4573-be61-28f10aabf314', confidence=600, place=1)]
ITEM = '7dc2f81a-86ad-41df-a3be-819dbfb24eda'
POINTER = '/_embedded/searchResult/_embedded/objects/75/_embedded/indexableObject'
REAL_SHA = 'ca9a82057352cdc02e2199b9c0d18b17a6a3e97a5ed9e0e2e307a791857c7f62'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def capture(root, raw, sha):
    path = A.P.hfile_w(root, 'thesis-captures.sqlite', 'epfl')
    with sqlite3.connect(path) as db:
        db.execute('create table if not exists captures(url text,status int,sha256 text,content blob,final_url text)')
        db.execute('delete from captures')
        db.execute('insert into captures values(?,?,?,?,?)', (URL, 200, sha, zlib.compress(raw), URL))
    return path


def fixture(raw=None):
    """Literal names/authority/item/handle from the original EPFL source, with independent test bytes."""
    typed = {'dc.contributor.advisor': copy.deepcopy(ADVISERS), 'dc.contributor.author': [copy.deepcopy(AUTHOR)]}
    item = dict(id=ITEM, uuid=ITEM, type='item', handle='20.500.14299/201880', metadata=typed)
    if raw is None:
        page = {'_embedded': {'searchResult': {'_embedded': {'objects': [{} for _ in range(75)] + [{'_embedded': {'indexableObject': item}}]}}}}
        raw = json.dumps(page, ensure_ascii=False, indent=2).encode()
        quote = ' '.join(json.dumps(typed, ensure_ascii=False, indent=2)[1:-1].split())
    else:
        page = json.loads(raw); item = A._repository_json_pointer(page, POINTER)
        # Actual native quotes are checked in the separate source-real fixture below.
        quote = ('"dc.contributor.advisor" : [ { "value" : "Fua, Pascal", "language" : null, "authority" : '
                 '"26ee9199-5a82-4097-90f0-e9eb052de875", "confidence" : 600, "place" : 0 }, { "value" : '
                 '"Salzmann, Mathieu", "language" : null, "authority" : "191ffa93-13b8-4573-be61-28f10aabf314", '
                 '"confidence" : 600, "place" : 1 } ], "dc.contributor.author" : [ { "value" : "Vidit", "language" : '
                 'null, "authority" : "68cb81ee-a70a-46b9-807d-ca48ac423c6f", "confidence" : 600, "place" : 0 } ]')
    sha = hashlib.sha256(raw).hexdigest(); endpoint = quote.index('"Vidit"', quote.index('"dc.contributor.author"')) + len('"Vidit"')
    native = dict(url=URL, sha256=sha, quote=quote[:endpoint]); names = ['Pascal Fua', 'Mathieu Salzmann']
    records = {}
    for name in names:
        r = stu('ext:epfl:vidit', 'Vidit', []); r['relations'] = [dict(type='researched_advising', years=[2023, 2023], role='phd', sources=[copy.deepcopy(native)])]; records[name] = [r]
    fx = {'epfl': dict(pis=[pi(n) for n in names], students=records, papers=[], links=[], sweep=[])}
    review = dict(scope='cross_lab', identity_basis='typed_repository_author', school='epfl', verdict='same_person', canonical_name='Vidit',
                  memberships=[dict(pi=n, person='ext:epfl:vidit', native_sources=[copy.deepcopy(native)]) for n in names],
                  repository_author=dict(namespace='infoscience.epfl.ch', source_json_pointer=POINTER, item_id=ITEM,
                                         handle='20.500.14299/201880', author=copy.deepcopy(AUTHOR),
                                         advisor_bindings=[dict(pi=n, source_name=a['value'], authority=a['authority']) for n, a in zip(names, ADVISERS)],
                                         source_record_sha256=digest(item)),
                  evidence=[dict(kind='typed_repository_author_record', url=URL, sha256=sha, quote=quote)])
    return fx, review, raw


def prepared(root, dbpath, fx, review, raw, write_package=True):
    write(root, fx); capture(root, raw, review['evidence'][0]['sha256'])
    A.P.hfile_w(root, 'student-identity-review.json').write_text(json.dumps([review]))
    db = A.open_registry(dbpath, seed=False)
    try:
        return A.run(['epfl'], root, db, use_sweep=False, today='2026-11-08', write=write_package)
    finally:
        db.close()


def member_ids(result):
    return {v for k, v in result['person_of'].items() if k[0] == 'stu'}


def test_exact_source_author_reuses_one_issued_id_and_preserves_every_native_fact(tmp_path):
    fx, review, raw = fixture(); before = copy.deepcopy(fx['epfl']['students']); reg = tmp_path / 'registry.sqlite'
    only = copy.deepcopy(fx); only['epfl']['students'].pop('Mathieu Salzmann'); root = tmp_path / 'seed'; write(root, only)
    db = A.open_registry(reg, seed=False)
    first = A.run(['epfl'], root, db, use_sweep=False, today='2026-11-08'); db.close(); issued = member_ids(first)
    assert issued == {'atl:p:c5ce424c1047'}  # The actual issued Vidit name/source anchor.
    result = prepared(tmp_path / 'new', reg, fx, review, raw)
    again = prepared(tmp_path / 'again', reg, fx, review, raw)
    assert member_ids(result) == member_ids(again) == issued
    assert result['report']['stats'].get('redirects_new', 0) == again['report']['stats'].get('split_minted', 0) == 0
    after = json.loads(A.P.hfile(tmp_path / 'new', 'students.json', 'epfl').read_text())
    for name, rows in after.items():
        rows[0].pop('atlasId'); assert rows == before[name]
    proof = result['report']['reviewed_cross_lab_identity_evidence'][0]['repository_author']
    assert proof['namespace'] == 'infoscience.epfl.ch' and proof['author'] == AUTHOR
    db = A.open_registry(reg, seed=False)
    anchors = [r[0] for r in db.execute('select anchor from anchors')]; db.close()
    assert 'p|coll:epfl:repository-author:infoscience.epfl.ch:' + AUTHOR['authority'] in anchors
    assert not any('orcid' in a or 'scopus' in a or 'personURI' in a for a in anchors)


@pytest.mark.parametrize('change', ['missing_body', 'body_hash', 'bad_zlib', 'namespace', 'pointer', 'item', 'handle', 'record_digest',
                                   'author_uuid', 'multiple_authors', 'adviser_uuid', 'adviser_name', 'missing_binding', 'native_hash',
                                   'native_url', 'native_quote', 'bare_name_quote', 'missing_preimage', 'native_name', 'alias', 'different_native_key',
                                   'author_only_prefix'])
def test_invalid_original_certificate_or_native_preimage_fails_before_any_write(tmp_path, change):
    fx, review, raw = fixture(); root = tmp_path / 'trial'; reg = tmp_path / 'registry.sqlite'
    if change == 'namespace': review['repository_author']['namespace'] = 'other.example'
    elif change == 'pointer': review['repository_author']['source_json_pointer'] = POINTER.replace('/75/', '/74/')
    elif change == 'item': review['repository_author']['item_id'] = 'wrong'
    elif change == 'handle': review['repository_author']['handle'] = '20.500/other'
    elif change == 'record_digest': review['repository_author']['source_record_sha256'] = '0' * 64
    elif change == 'author_uuid': review['repository_author']['author']['authority'] = ADVISERS[0]['authority']
    elif change == 'adviser_uuid': review['repository_author']['advisor_bindings'][0]['authority'] = AUTHOR['authority']
    elif change == 'adviser_name': review['repository_author']['advisor_bindings'][0]['source_name'] = 'Other, Adviser'
    elif change == 'missing_binding': review['repository_author']['advisor_bindings'].pop()
    elif change == 'native_hash': fx['epfl']['students']['Pascal Fua'][0]['relations'][0]['sources'][0]['sha256'] = '0' * 64
    elif change == 'native_url': fx['epfl']['students']['Pascal Fua'][0]['relations'][0]['sources'][0]['url'] += '&other=1'
    elif change in {'native_quote', 'bare_name_quote'}:
        fx['epfl']['students']['Pascal Fua'][0]['relations'][0]['sources'][0]['quote'] = 'Vidit'
        if change == 'bare_name_quote': review['memberships'][0]['native_sources'][0]['quote'] = 'Vidit'
    elif change == 'missing_preimage': review['memberships'][0].pop('native_sources')
    elif change == 'native_name': fx['epfl']['students']['Pascal Fua'][0]['name'] = 'Other'
    elif change == 'alias': fx['epfl']['students']['Pascal Fua'][0]['aliases'] = ['Vidit Person']
    elif change == 'different_native_key': review['memberships'][0]['person'] += '-different'
    elif change == 'author_only_prefix':
        page = json.loads(raw); item = A._repository_json_pointer(page, POINTER)
        typed = {'dc.contributor.author': item['metadata']['dc.contributor.author'], 'dc.contributor.advisor': item['metadata']['dc.contributor.advisor']}
        item['metadata'] = typed; raw = json.dumps(page, indent=2).encode()
        quote = ' '.join(json.dumps(typed, indent=2)[1:-1].split()); partial = quote[:quote.index('"Vidit"') + len('"Vidit"')]
        review['evidence'][0].update(quote=quote, sha256=hashlib.sha256(raw).hexdigest()); review['repository_author']['source_record_sha256'] = digest(item)
        for m in review['memberships']: m['native_sources'][0].update(quote=partial, sha256=review['evidence'][0]['sha256'])
        for rows in fx['epfl']['students'].values(): rows[0]['relations'][0]['sources'][0].update(quote=partial, sha256=review['evidence'][0]['sha256'])
    elif change == 'multiple_authors':
        page = json.loads(raw); item = A._repository_json_pointer(page, POINTER); item['metadata']['dc.contributor.author'].append(dict(AUTHOR, value='Other', authority=ADVISERS[0]['authority']))
        raw = json.dumps(page, indent=2).encode(); review['evidence'][0]['sha256'] = hashlib.sha256(raw).hexdigest(); review['repository_author']['source_record_sha256'] = digest(item)
        for m in review['memberships']: m['native_sources'][0]['sha256'] = review['evidence'][0]['sha256']
        for rows in fx['epfl']['students'].values(): rows[0]['relations'][0]['sources'][0]['sha256'] = review['evidence'][0]['sha256']
    write(root, fx); path = capture(root, raw, review['evidence'][0]['sha256'])
    if change == 'missing_body': path.unlink()
    elif change in {'body_hash', 'bad_zlib'}:
        with sqlite3.connect(path) as db: db.execute('update captures set content=?', (b'bad' if change == 'bad_zlib' else zlib.compress(b'{}'),))
    A.P.hfile_w(root, 'student-identity-review.json').write_text(json.dumps([review]))
    before = {p: p.read_bytes() for p in (root / 'epfl').iterdir()}; db = A.open_registry(reg, seed=False)
    with pytest.raises(ValueError): A.run(['epfl'], root, db, use_sweep=False)
    assert db.execute('select count(*)from ids').fetchone()[0] == db.execute('select count(*)from anchors').fetchone()[0] == 0
    assert {p: p.read_bytes() for p in (root / 'epfl').iterdir()} == before
    db.close()


def test_bare_mononym_without_certificate_stays_held(tmp_path):
    fx, _, _ = fixture(); root = tmp_path / 'trial'; write(root, fx); db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    with pytest.raises(A.CoadvisingIDConflict, match='incompatible'): A.run(['epfl'], root, db, use_sweep=False)
    assert db.execute('select count(*)from ids').fetchone()[0] == 0; db.close()


def test_repository_proof_cannot_redirect_two_issued_ids(tmp_path):
    fx, review, raw = fixture(); reg = tmp_path / 'registry.sqlite'; db = A.open_registry(reg, seed=False)
    name_anchor = A.person_anchor_str('name', 'epfl:vidit:' + URL)
    repo_anchor = A.person_anchor_str('coll', 'epfl:repository-author:infoscience.epfl.ch:' + AUTHOR['authority'])
    A.assign(db, 'person', 'atl:p:', {'old1': [(A.RANK['name'], name_anchor)], 'old2': [(A.RANK['coll'], repo_anchor)]}, '2026-01-01', collections.Counter()); db.commit(); before = A.registry_fingerprint(db); db.close()
    with pytest.raises(A.CoadvisingIDConflict, match='issued'): prepared(tmp_path / 'trial', reg, fx, review, raw)
    db = A.open_registry(reg, seed=False); assert A.registry_fingerprint(db) == before; db.close()


@pytest.mark.parametrize('change', ['truncated_zlib', 'trailing_zlib', 'inflation_limit', 'compressed_limit', 'unregistered_path'])
def test_original_capture_is_bounded_and_only_registered_slot_is_read(tmp_path, change):
    fx, review, raw = fixture(); root = tmp_path / 'trial'; write(root, fx)
    path = capture(root, raw, review['evidence'][0]['sha256'])
    if change == 'unregistered_path':
        decoy = tmp_path / 'unregistered.sqlite'; path.rename(decoy); review['repository_author']['capture_path'] = str(decoy)
    else:
        content = zlib.compress(raw)
        if change == 'truncated_zlib': content = content[:-1]
        elif change == 'trailing_zlib': content += b'unreviewed trailing data'
        elif change == 'inflation_limit': content = zlib.compress(b'x' * (16 * 1024 * 1024 + 1))
        else: content = b'x' * (8 * 1024 * 1024 + 1)
        with sqlite3.connect(path) as db: db.execute('update captures set content=?', (content,))
    A.P.hfile_w(root, 'student-identity-review.json').write_text(json.dumps([review]))
    db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    with pytest.raises(ValueError): A.run(['epfl'], root, db, use_sweep=False)
    assert db.execute('select count(*)from ids').fetchone()[0] == 0; db.close()


def test_native_within_lab_stage_ignores_typed_repository_review(tmp_path):
    import types
    from pihier import students as S
    fx, review, _ = fixture(); A.P.data_w('student-identity-review.json', root=tmp_path).write_text(json.dumps([review]))
    ctx = types.SimpleNamespace(here=tmp_path, school='epfl', n=collections.Counter(), typo_pairs=[])
    students = {'Pascal Fua': {'one': fx['epfl']['students']['Pascal Fua'][0]}}
    before = copy.deepcopy(students)
    assert S.identity_review(ctx, students) == 0
    S.queue_surname_typos(ctx, students)
    assert students == before and not ctx.typo_pairs


@pytest.mark.nfs
def test_actual_original_epfl_body_and_both_native_preimages(tmp_path):
    path = A.P.data('thesis-captures.sqlite', 'epfl')
    if not path.is_file(): pytest.skip('original registered EPFL repository cache absent')
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        rows = db.execute('select content from captures where url=? and sha256=?', (URL, REAL_SHA)).fetchall()
    assert len(rows) == 1; raw = zlib.decompress(rows[0][0]); assert hashlib.sha256(raw).hexdigest() == REAL_SHA
    fx, review, _ = fixture(raw); assert review['repository_author']['source_record_sha256'] == '13047e38e5a4231211179123f4cc55428906399451a706995bf72484e8c5122a'
    natives = json.loads(A.P.data('students.json', 'epfl').read_text())
    for name in fx['epfl']['students']:
        actual = next(r for r in natives[name] if r['person'] == 'ext:epfl:vidit'); actual = copy.deepcopy(actual); actual.pop('atlasId', None)
        assert actual == fx['epfl']['students'][name][0]
    result = prepared(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx, review, raw, write_package=False)
    assert len(member_ids(result)) == 1
