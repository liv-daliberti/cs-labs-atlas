"""Lab hunt 2026-11-23: WashU Bulletin faculty entries become person rows; Han-only PIs keep pinyin-bound DBLP records."""
import listing_rows as R
from pihier.names import han_reading

SECTION = (
    'Faculty Chair Roch Guérin (https://engineering.wustl.edu/Profiles/Pages/ Roch-Gu%C3%A9rin.aspx) Harold B. and Adelaide G. '
    'Welge Professor of Computer Science PhD, California Institute of Technology Computer networks and communication systems '
    'Associate Professors Kunal Agrawal (https://engineering.wustl.edu/Profiles/Pages/ Kunal-Agrawal.aspx) PhD, Massachusetts '
    'Institute of Technology Parallel computing Sanmay Das (https://engineering.wustl.edu/Profiles/Pages/ Sanmay-Das.aspx) PhD, '
    'Massachusetts Institute of Technology Design of algorithms Assistant Professors Angelina Lee (https://engineering.wustl.edu/'
    'Profiles/Pages/I- Ting-Angelina-Lee.aspx) PhD, Massachusetts Institute of Technology Parallel programming Lecturers Douglas '
    'Shook (https://cse.wustl.edu/faculty/Pages/Doug- Shook.aspx) MS, Washington University Compiler design William Siever '
    '(https://cse.wustl.edu/faculty/Pages/Bill- Siever.aspx) Principal Lecturer PhD, Missouri University of Science and '
    'Technology Todd Sproull (https://cse.wustl.edu/faculty/Pages/Todd- Sproull.aspx) PhD, Washington University Networking '
    'Senior Professors Jerome R. Cox Jr. ScD, Massachusetts Institute of Technology Computer system design Mark A. Franklin '
    'Hugo F. and Ina Champ Urbauer Professor of Engineering PhD, Carnegie Mellon University Computer architecture '
    'Professors Emeriti Takayuki D. Kimura PhD, University of Pennsylvania Visual programming')


def test_bulletin_entries_names_and_ranks():
    entries, unread = R.washu_bulletin_entries(SECTION)
    got = {e['name']: e['rank'] for e in entries}
    assert got == {'Roch Guérin': 'ladder', 'Kunal Agrawal': 'ladder', 'Sanmay Das': 'ladder', 'Angelina Lee': 'ladder',
                   'Douglas Shook': 'lecturer', 'William Siever': 'lecturer', 'Todd Sproull': 'lecturer',
                   'Jerome R. Cox Jr.': 'ladder', 'Mark A. Franklin': 'ladder', 'Takayuki D. Kimura': 'emeritus'}
    assert not unread
    for e in entries:   # every quote is verbatim and opens with the printed name
        assert SECTION[e['start']:e['end']].startswith(e['name'])
    das = next(e for e in entries if e['name'] == 'Sanmay Das')
    assert das['profile'] == 'https://engineering.wustl.edu/Profiles/Pages/Sanmay-Das.aspx'


def test_han_reading():
    assert han_reading(['肖鸣宇'], 'Mingyu Xiao 0001')
    assert han_reading(['肖鸣宇'], 'Xiao Mingyu')
    assert not han_reading(['肖鸣宇'], 'Ming Xiao')
    assert not han_reading(['肖鸣宇', 'Mingyu Xiao'], 'Mingyu Xiao')   # a PI with a Latin form keeps the ordinary name check
    assert han_reading(['欧阳红'], 'Hong Ouyang')                      # two-syllable family name
    assert han_reading(['单志广'], 'Zhiguang Shan')                     # polyphonic first character
    assert not han_reading(['张伟'], 'Wei Wang')
