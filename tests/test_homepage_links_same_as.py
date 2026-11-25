import homepage_links_school as HL

PAGE = '''<html><script type="application/ld+json">{"@type":"Person","name":"Juho Kim","sameAs":["https://scholar.google.com/citations?user=2dDAbMgAAAAJ&hl=en",
"https://dblp.org/pid/64/3462-1.html","https://orcid.org/0000-0001-6348-4127"]}</script></html>'''


def test_same_as_urls_and_matching():
    urls = HL.same_as_urls(PAGE)
    assert 'https://dblp.org/pid/64/3462-1.html' in urls and len(urls) == 3
    m = HL.DBLP.search('href="https://dblp.org/pid/64/3462-1.html"')
    assert m.group(2) == '64/3462-1'
    assert HL.ORCID.search('href="https://orcid.org/0000-0001-6348-4127"').group(2) == '0000-0001-6348-4127'
    assert HL.same_as_urls('<script type="application/ld+json">not json</script>') == []
