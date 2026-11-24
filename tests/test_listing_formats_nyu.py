from listing_formats import parse


def test_nyu_cs_dynamic_keeps_name_title_and_homepage_only():
    html = ('<ul><li class="col-sm-6"><span class="row"><div><p class="name bold"><a href="http://cs.nyu.edu/~khot/">Subhash Khot</a></p>'
            '<p class="title">Silver Professor of Computer Science</p><p class="info">Email: khot at cs.nyu.edu<br/>Office: WWH 416</p></div></span></li>'
            '<li><p class="name bold">Plain Name</p><p class="title">Clinical Assistant Professor of Computer Science</p></li></ul>')
    _, rows = parse(html, 'nyu_cs_dynamic')
    assert rows == [dict(name_listed='Subhash Khot', titles=['Silver Professor of Computer Science'], homepage='http://cs.nyu.edu/~khot/', division=None),
                    dict(name_listed='Plain Name', titles=['Clinical Assistant Professor of Computer Science'], homepage=None, division=None)]
    assert 'Email' not in str(rows)


def test_nyu_cds_2017_keeps_only_cds_faculty_group():
    def card(n, t):
        return f'<li><article class="hentry"><div><a href="http://x.edu/{n[0]}"><h3 class="accent">{n}</h3></a><h6><em>{t}</em></h6><span class="research-interest">topic</span></div></article></li>'
    html = ('<div class="post-list dt_people sc"><h2 class="post-list-title">Staff</h2><ul>' + card('Some Staff', 'Director of Operations') + '</ul></div>'
            '<div class="post-list dt_people sc"><h2 class="post-list-title">CDS Faculty</h2><ul>' + card('Cristina Savin (Starting Fall 2017)', 'Assistant Professor of Neural Science and Data Science') + '</ul></div>'
            '<div class="post-list"><h2 class="post-list-title">Affiliated Faculty</h2><ul>' + card('Other Person', 'Professor of Physics') + '</ul></div>')
    _, rows = parse(html, 'nyu_cds_wp_2017')
    assert [r['name_listed'] for r in rows] == ['Cristina Savin']
    assert rows[0]['titles'] == ['Assistant Professor of Neural Science and Data Science']


def test_nyu_tandon_cards_keeps_faculty_groups_and_both_template_eras():
    def card(n, t, tag):
        name = f'<h3 class="h4"><a href="/faculty/x"><span>{n}</span></a></h3>' if tag == 'h3' else f'<div class="h4"><a href="/faculty/x"><span>{n}</span></a></div>'
        return f'<article class="node node--type-profile"><div class="card-body">{name}<div class="field--name-field-title">{t}</div></div></article>'
    html = ('<h2>Core Faculty</h2>' + card('A Person', 'Professor', 'h3') + card('B Person', 'Industry Assistant Professor', 'div')
            + '<h2>Global Network Faculty</h2>' + card('Shanghai Person', 'Professor', 'h3')
            + '<h2>Emeritus Faculty</h2>' + card('Old Person', 'Professor Emeritus', 'h3') + '<h2>Staff</h2>' + card('Staff Person', 'Program Coordinator', 'h3'))
    rows = parse(html, 'nyu_tandon_cards')[1]
    assert [(r['name_listed'], r['division']) for r in rows] == [('A Person', 'Core Faculty'), ('B Person', 'Core Faculty'), ('Old Person', 'Emeritus Faculty')]
