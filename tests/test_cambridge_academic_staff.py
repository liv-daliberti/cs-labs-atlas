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
        dict(name_listed='Anderson, Ross', titles=['Prof'], quote_name='Anderson, Prof Ross',
             homepage='/~rja14/', division='Academic staff'),
        dict(name_listed='Beresford, Alastair', titles=['Academic staff'], quote_name='Beresford, Dr Alastair',
             homepage='/~arb33/', division='Academic staff'),
    ]
    assert F.cambridge_academic_staff(html.replace('Academic staff</title>', 'People</title>')) == []


def test_historical_titles_do_not_lose_source_quotes():
    from listing_rows import quote_of

    html = """<title>Computer Laboratory: Academic staff</title>
      <table class="directory">
      <tr><td class="name"><a href="/~rja14/">Anderson, Prof Ross</a></td></tr>
      <tr><td class="name"><a href="/~arb33/">Beresford, Dr Alastair</a></td></tr>
      </table>"""
    rows = F.cambridge_academic_staff(html)
    flat = 'Computer Laboratory: Academic staff Anderson, Prof Ross Beresford, Dr Alastair'
    assert [quote_of(flat, row) for row in rows] == [
        'Anderson, Prof Ross', 'Beresford, Dr Alastair',
    ]


def test_cambridge_ladder_titles_respect_appointment_categories():
    from listing_rows import rank_of
    import school_config

    extra = school_config.get('cambridge')['census']['rank_words']
    for title in ('University Lecturer', 'University Senior Lecturer', 'Reader', 'Prof'):
        assert rank_of([title], extra) == 'ladder'
    assert rank_of(['Lecturer'], extra) == 'lecturer'
    assert rank_of(['Visiting University Lecturer'], extra) == 'visiting'
    assert rank_of(['Emeritus University Lecturer'], extra) == 'emeritus'
    assert rank_of(['University Lecturer']) == 'lecturer'
