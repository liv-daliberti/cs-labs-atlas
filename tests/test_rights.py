"""Rights and citation files (tools/rights.py, docs/RIGHTS-AND-CITATION.md): the owner's single definition fills every output,
the outputs parse, nothing leaks an e-mail, a path or a key, and the HF card carries the licence."""
import json
import re
from pathlib import Path

import pytest
import yaml

import rights

TOOLS = Path(rights.__file__).resolve().parent
RID = '2026-11-05'


def test_cff_parses_and_is_a_dataset():
    c = yaml.safe_load(rights.cff(RID))
    assert c['cff-version'] == '1.2.0' and c['type'] == 'dataset' and c['version'] == RID
    assert c['license'] == 'CC-BY-NC-4.0'
    assert c['authors'][0]['family-names'] == "d'Aliberti" and c['authors'][0]['given-names'] == 'Liv'
    assert c['doi'] == '10.5281/zenodo.23988437'  # the Zenodo concept DOI (all versions)
    assert 'https://doi.org/10.5281/zenodo.23988437' in rights.citation(RID)


def test_zenodo_json():
    z = json.loads(rights.zenodo(RID))
    assert z['upload_type'] == 'dataset' and z['license'] == 'cc-by-nc-4.0'
    assert z['creators'][0]['name'] == "d'Aliberti, Liv" and z['description'] and z['keywords']


def test_license_is_the_full_legal_code():
    t = rights.license_text(RID)
    assert "Copyright (c) 2026 Liv d'Aliberti" in t
    assert 'Attribution-NonCommercial 4.0 International' in t and 'Section 8 -- Interpretation.' in t
    assert 'NonCommercial means not primarily intended for or' in t


def test_notice_says_what_is_and_is_not_covered():
    n = rights.notice(RID)
    assert 'COVERED' in n and 'NOT covered' in n and 'plain facts' in n and 'Directive 2019/790' in n


def test_hf_card_front_matter_and_citation():
    card = rights.hf_card(RID)
    assert card.startswith('---\nlicense: cc-by-nc-4.0\n')
    assert "d'Aliberti" in card and '@dataset{' in card and 'Directive 2019/790' in card


def test_no_leaks():
    for name, text in {**rights.files(RID), 'card': rights.hf_card(RID), 'readme': rights.readme_section(RID)}.items():
        assert not re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text), name
        assert '/n/fs/' not in text, name
    with pytest.raises(SystemExit):
        rights.assert_clean('mail me at someone@example.org', 'x')


def test_readme_section_is_replaced_not_duplicated():
    once = rights.update_readme('# Atlas\n', RID)
    twice = rights.update_readme(once, '2026-12-01')
    assert twice.count('## How to cite') == 1 and '2026-12-01' in twice and RID not in twice.split('<!-- cite:start -->')[1].split('Zenodo.')[0]


def test_write_all(tmp_path):
    (tmp_path / 'README.md').write_text('# Atlas\n')
    names = rights.write_all(tmp_path, RID)
    assert names == ['.zenodo.json', 'CITATION.cff', 'LICENSE', 'NOTICE']
    assert all((tmp_path / n).stat().st_size > 100 for n in names) and 'How to cite' in (tmp_path / 'README.md').read_text()


def test_export_writes_the_rights_files():
    src = (TOOLS / 'export_release.py').read_text()
    assert "_load_tool('rights').write_all" in src and "('tools/rights', 1" in src
