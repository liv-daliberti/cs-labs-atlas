"""Candidates that share a display name carry their source id (one decision key per identity)."""
import cs_related_disambiguate as D


def test_colliding_display_names_get_their_source_id_and_it_is_idempotent():
    cands = [dict(name='Bin Li', dblp='https://dblp.org/pid/89/6764-38'), dict(name='Bin Li', dblp='https://dblp.org/pid/89/6764-77'),
             dict(name='Bin Li', openalex=['https://openalex.org/A5069353502']), dict(name='Ana Lee', dblp='https://dblp.org/pid/1/2')]
    out = D.disambiguate_display_names(cands)
    assert [c['name'] for c in out] == ['Bin Li [89/6764-38]', 'Bin Li [89/6764-77]', 'Bin Li [A5069353502]', 'Ana Lee']
    assert [c['name'] for c in D.disambiguate_display_names(out)] == [c['name'] for c in out]
