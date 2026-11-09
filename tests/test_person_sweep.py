import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import person_sweep as W  # noqa: E402


def test_name_keys_and_urls():
    assert 'jane pan' in W.name_keys('Jane Q. Pan')
    assert 'jane pan' in W.name_keys('Pan, Jane')
    assert W.norm_url('https://web.archive.org/web/2020id_/http://www.x.edu/a/') == 'x.edu/a'


def test_classify():
    d = r'princeton\.edu'
    assert W.classify('https://www.linkedin.com/in/x', d) == 'social_or_profile'
    assert W.classify('https://www.cs.princeton.edu/~ab/', d) == 'personal_site'
    assert W.classify('https://www.cs.princeton.edu/people/profile/ab', d) == 'school_profile'
    assert W.classify('https://someone.github.io/', d) == 'personal_site'


def test_registered_files_have_the_contract():
    for f in (Path(__file__).resolve().parents[1] / 'hierarchy').glob('*/reviewed/person-sweep.json'):
        doc = json.loads(f.read_text())
        assert doc['counts']['students_neither'] == 0
        for r in doc['rows']:
            assert r['url'].startswith('http') and r['found_from'] and 'fetched' in r and r['kind']
