"""identity_review finds a record by its `person` id when the per-PI dict is keyed by another id (Stanford Gyurgyik, 2026-11-11)."""
import collections
import json
import types

import atlas_paths as P
from pihier import students as S


def test_same_person_review_matches_the_person_field(tmp_path):
    rev = [dict(school='s', pi='X', a=['s_stu_chris', 'Chris G'], b=['ext:s:christophe', 'Christophe G'], verdict='same_person',
                canonical_name='Christophe G', reason='r', evidence=[])]
    P.data_w('student-identity-review.json', root=tmp_path).write_text(json.dumps(rev))
    ctx = types.SimpleNamespace(here=tmp_path, school='s', n=collections.Counter(), typo_pairs=[])
    stu = {'X': {'key1': dict(person='s_stu_chris', name='Chris G', relations=[1]), 'key2': dict(person='ext:s:christophe', name='Christophe G', relations=[2])}}
    assert S.identity_review(ctx, stu) == 1
    assert len(stu['X']) == 1 and list(stu['X'].values())[0]['name'] == 'Christophe G'
