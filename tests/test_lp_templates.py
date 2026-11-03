"""tools/lp_templates.py: template detection and the structural heading / entry reader."""

import lp_templates as T  # noqa: E402

GOOGLE = ('<html><head><meta name="generator" content="Google Sites"></head><body>'
          '<h2>Postdocs and Visitors</h2><p>Dr. John Atkins</p><p>Dr. Daniel Esser</p>'
          '<h2>Undergraduate Researchers (S26)</h2><p>Allison Dana</p><p>Justin Hoang</p></body></html>')
WP = ('<html><body><link href="/wp-content/themes/x.css"><h3 class="wp-block-heading">PhD Students</h3>'
      '<div class="wp-block-columns"><div class="wp-block-column"><p>Ann Lee</p></div><div class="wp-block-column"><p>Bo Wu</p></div></div>'
      '<h3 class="wp-block-heading">Alumni</h3><ul><li>Cy Xu, PhD 2019</li></ul></body></html>')
FOLIO = ('<html><head><link href="al-folio.css"></head><body><h2>People</h2><h3>Current</h3>'
         '<div class="card"><h5>Di Yang</h5><p>PhD student</p></div><h3>Former</h3><ul><li>Ed Zhao</li></ul></body></html>')


def test_detect():
    assert T.detect(GOOGLE, 'https://sites.google.com/view/x') == 'google_sites'
    assert T.detect(WP) == 'wordpress'
    assert T.detect(FOLIO) == 'al_folio'
    assert T.detect('<html><body>plain</body></html>') is None


def test_adjacent_one_line_sections_keep_their_own_heading():
    assert T.locate(GOOGLE, 'Daniel Esser')[0] == 'Postdocs and Visitors'
    assert T.locate(GOOGLE, 'Justin Hoang')[0] == 'Undergraduate Researchers (S26)'


def test_wordpress_columns_and_lists():
    assert T.locate(WP, 'Bo Wu') == ('PhD Students', 'Bo Wu')
    head, entry = T.locate(WP, 'Cy Xu')
    assert head == 'Alumni' and entry.startswith('Cy Xu')


def test_al_folio_card_and_nested_headings():
    head, entry = T.locate(FOLIO, 'Di Yang')
    assert head == 'People > Current' and 'PhD student' in entry
    assert T.locate(FOLIO, 'Ed Zhao')[0] == 'People > Former'
    assert T.locate(FOLIO, 'Nobody Here') == (None, None)


def test_apply_template_reader_sets_head_and_desc():
    import labpage_audit as A

    class Lpev:
        @staticmethod
        def cap(school, src):
            return {'content': GOOGLE.encode(), 'content_type': 'text/html'}, {}

    class Autom:
        _role = staticmethod(lambda t: (None, None))

    class Kit:
        lpev = Lpev()
        autom = Autom()
    x = {'name': 'Justin Hoang', 'head': 'Postdocs and Visitors', 'desc': 'Undergraduate Researchers (S26): ...'}
    A.apply_template_reader(Kit(), 'berkeley', 'https://sites.google.com/view/x', x, {})
    assert x['head'] == 'Undergraduate Researchers (S26)' and x['template'] == 'google_sites' and x['desc'] == ''


def test_bare_text_sublabel_between_heading_and_list():
    html = ('<html><body><h2> Former Students and Postdocs </h2>Postdocs<ul><li>Josh K (2020-2022): ML</li></ul>'
            '<p>Ph.D. Students<ul><li>Laura Niss, Ph.D. 2022. Thesis</li></ul></body></html>')
    assert T.locate(html, 'Josh K')[0] == 'Former Students and Postdocs > Postdocs'
    assert T.locate(html, 'Laura Niss')[0] == 'Former Students and Postdocs > Ph.D. Students'
