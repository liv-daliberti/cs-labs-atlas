"""Record Peng He's dated VT visit and Chongqing faculty appointment."""

import json

import atlas_paths as P


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Peng He'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=['何鹏'], source='dblp_affiliation',
        decision='not_faculty_listed',
        reason=('Chongqing University’s named faculty profile says Peng He visited '
                'Virginia Tech for research in 2010–2012, completed his Chongqing '
                'doctorate in 2013, and joined Chongqing University’s College of '
                'Optoelectronic Engineering in 2015. Its spectral CT research area '
                'and penghe@cqu.edu.cn match the imaging publications in the DBLP '
                'candidate. The VT affiliation predates the 2016–2026 window.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/84/6016-2'], dblp_window=17,
                      affiliation_notes=['Chongqing University, Key Lab of Optoelectronic Technology and Systems',
                                         'Virginia Tech, Biomedical Imaging Division']),
        faculty_evidence=[], status_evidence=[dict(
            url='https://coe.cqu.edu.cn/info/1201/2599.htm',
            observed='2026-11-10',
            quote=('2010年至2012年曾获国家公派留学资格赴美国弗吉尼亚理工大学进行访学研究。'
                   '2015年至今入职于重庆大学光电工程学院。'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment in 2016–2026 is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Peng He dated VT visit and Chongqing role')


if __name__ == '__main__':
    main()
