import homepage_links_school as H


def test_page_links_fold_accents_and_need_the_family_name():
    html = '<p>Srdjan Capkun</p><a href="https://dblp.org/pid/51/1639.html">dblp</a><a href="https://orcid.org/0000-0001-2345-678X">o</a>'
    d, o = H.page_links(html, 'Čapkun')
    assert list(d) == ['https://dblp.org/pid/51/1639'] and list(o) == ['0000-0001-2345-678X']
    assert H.page_links(html, 'Nobody') == ({}, {})
