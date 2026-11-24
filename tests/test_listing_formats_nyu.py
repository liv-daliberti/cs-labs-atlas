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
