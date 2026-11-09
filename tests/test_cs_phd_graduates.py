"""JHU CS PhD graduate pages: one adviser per defense block, never the next block's (R-STU-26)."""
import re

import cs_phd_graduates as G

FLAT = ('The Department of Computer Science would like to congratulate Dr. Keith Levin on the recent successful defense of his thesis work, "T" on December 13, 2018. '
        'Primary Advisor: Ben Van Durme Professional Plans: none. The Department of Computer Science would like to congratulate Dr. Ayushi Sinha on the recent '
        'successful defense of her thesis work, "U" on April 2, 2019. Primary Advisor: Russ Taylor. For more information')


def test_blocks_do_not_leak_into_each_other():
    starts = [m.start() for m in re.finditer('would like to congratulate ', FLAT)]
    got = []
    for i, st in enumerate(starts):
        chunk = FLAT[st:starts[i + 1] if i + 1 < len(starts) else len(FLAT)]
        mn, md, ma = G.NAME.match(chunk), G.DATE.search(chunk), G.ADV.search(chunk)
        got.append((mn.group(1), md.group(2), ma.group(2).rstrip(' .')))
    assert got == [('Dr. Keith Levin'.replace('Dr. ', ''), '2018', 'Ben Van Durme'), ('Ayushi Sinha', '2019', 'Russ Taylor')]
