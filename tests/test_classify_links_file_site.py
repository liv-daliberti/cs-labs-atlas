import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import labpage_audit as A  # noqa: E402


def test_site_page_file_keeps_sibling_student_page():
    out = A.classify_links([('https://people.iiis.tsinghua.edu.cn/~yuanyang/student-en.html', 'Student')],
                           'https://people.iiis.tsinghua.edu.cn/~yuanyang/en.html', r'tsinghua\.edu\.cn')
    assert out['people'] == ['https://people.iiis.tsinghua.edu.cn/~yuanyang/student-en.html']


def test_two_level_listing_still_excluded():
    out = A.classify_links([('https://cs.example.edu/people/other/', 'People')], 'https://cs.example.edu/people/pattie/', r'example\.edu')
    assert not out.get('people')
