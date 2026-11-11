import listing_formats as F


def test_legacy_academic_staff_page_preserves_literal_role_and_names():
    html = '''<title>Computer Laboratory: Academic staff</title>
      <table class="directory"><tr><th class="name">Name</th></tr>
      <tr id="A"><td class="letter">A</td></tr>
      <tr id="rja14"><td class="name"><a href="/~rja14/">Anderson, Prof Ross</a></td></tr>
      <tr id="arb33"><td class="name"><a href="/~arb33/">Beresford, Dr Alastair</a></td></tr>
      </table>'''
    fmt, rows = F.parse(html)
    assert fmt == 'cambridge_academic_staff'
    assert rows == [
        dict(name_listed='Anderson, Ross', titles=['Academic staff'],
             homepage='/~rja14/', division='Academic staff'),
        dict(name_listed='Beresford, Alastair', titles=['Academic staff'],
             homepage='/~arb33/', division='Academic staff'),
    ]
    assert F.cambridge_academic_staff(html.replace('Academic staff</title>', 'People</title>')) == []
