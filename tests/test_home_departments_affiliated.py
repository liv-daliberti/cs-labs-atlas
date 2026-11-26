"""ETH homes 2026-11-25: a '(D-XXX)' tag on an affiliated listing names the department; 'Prof.' counts as a professor title."""
import home_departments_school as H


def test_prof_abbreviation_is_a_professor_title():
    assert H.PROF.search('Prof.') and H.PROF.search('Full Professor') and not H.PROF.search('Affiliated Faculty')


def test_affiliated_tag_names_the_department():
    rows = [{'name': 'Bernd Bickel', 'name_listed': 'Bernd Bickel', 'slot': 'INFK affiliated', 'sha256': 'a'},
            {'name': 'Bernd Bickel', 'name_listed': 'Bernd Bickel', 'slot': 'INFK professors', 'sha256': 'b'}]
    texts = {'a': 'Konrad Schindler (D-BAUG) Professor Bernd Bickel (D-ARCH) Professor', 'b': 'Bernd Bickel (D-INFK)'}
    assert H.affiliated_tags(rows, texts.get) == ['ARCH']   # only the affiliated slot counts


def test_no_tag_no_decision():
    rows = [{'name': 'X Y', 'slot': 'INFK affiliated', 'sha256': 'a'}]
    assert H.affiliated_tags(rows, lambda sha: 'X Y Professor') == []


def test_native_merge_alias_helper_needs_the_opt_in(tmp_path, monkeypatch):
    import json
    f = tmp_path / 'census-name-aliases.json'
    f.write_text(json.dumps({'native_pi_merges': [{'canonical': 'A', 'aliases': ['B'], 'gate_counts_once': True}, {'canonical': 'C', 'aliases': ['D']}]}))
    monkeypatch.setattr(H.P, 'data', lambda name, key=None: f)
    assert H.native_merge_aliases('x') == {'B'}
