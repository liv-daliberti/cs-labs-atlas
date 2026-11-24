import listing_formats as F
import listing_rows as R


def test_nus_legacy_tables_reject_administration_and_research_staff():
    html = '''<table><tr><td>Head</td><td>LEE Example</td></tr></table>
    <table><tr><th>Name</th><th>Designation</th><th>Contact</th></tr>
    <tr><td><a href="/cs/bio/lim">LIM Example</a></td><td>Associate Professor</td>
    <td>[email removed]</td></tr>
    <tr><td>Student Example</td><td>Research Assistant</td><td></td></tr></table>'''
    assert F.parse(html, 'nus_cs_any')[1] == [
        dict(name_listed='LIM Example', titles=['Associate Professor'],
             homepage=None, division=None, profile='/cs/bio/lim')]


def test_nus_inline_roster_checks_raw_source_quote_and_department():
    html = '''<script>$scope.allStaffs = [
    {name: "CHAN Example", title: "Assistant Professor", email: "private@example.org",
     Dept: "252", Bio: "/cs/people/chan"},
    {name: "LEE Example", title: "Professor", Dept: "253", Bio: "/disa/people/lee"},
    ];</script>'''
    rows = F.parse(html, 'nus_cs_any')[1]
    assert len(rows) == 1
    assert rows[0]['name_listed'] == 'CHAN Example'
    assert rows[0]['titles'] == ['Assistant Professor']
    assert rows[0]['profile'] == '/cs/people/chan'
    assert 'private' not in rows[0]['quote_raw']
    assert R.quote_of('', rows[0], html) == rows[0]['quote_raw']
    assert R.quote_of('', rows[0], html.replace('CHAN Example', 'Other')) is None
