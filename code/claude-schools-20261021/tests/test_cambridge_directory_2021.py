import listing_formats as F


def test_2021_cst_directory_preserves_literal_faculty_classification():
    html = '''<table class="views-table"><tbody><tr class="odd views-row-first">
      <td class="views-field views-field-title"><a href="/people/abc12">Ada Example</a></td>
      <td class="views-field views-field-field-tax-singular">Faculty</td>
      </tr><tr class="even"><td class="views-field views-field-title">Student Example</td>
      <td class="views-field views-field-field-tax-singular">PhD student</td></tr></tbody></table>'''
    assert F.cambridge_directory(html) == [
        dict(name_listed='Ada Example', titles=['Faculty'], homepage='/people/abc12', division=None),
        dict(name_listed='Student Example', titles=['PhD student'], homepage=None, division=None),
    ]
