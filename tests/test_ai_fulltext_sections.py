"""ai-writing/fulltext_sections.py: the main / references / appendix split, on synthetic text (no NFS, no pdftotext)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ai-writing'))
import fulltext_sections as S  # noqa: E402

PROSE = ' '.join(['We study the effect of the method in this setting and show that the results hold for the data.'] * 30)
REFS = 'References\n' + '\n'.join(f'[{i}] Author {i}. A paper about topic {i}. Journal of Things, {2000 + i}.' for i in range(1, 30)) + '\n'
FRONT = 'A Paper Title\nSome Author\nAbstract. We do things.\n\n1 Introduction\n'


def doc(*parts):
    return FRONT + '\n\n'.join(parts)


def test_appendix_after_references():
    t = doc(PROSE, '2 Method\n' + PROSE, '3 Conclusion\n' + PROSE, REFS, 'Appendix A: Proofs\n' + PROSE, 'Appendix B: More plots\n' + PROSE)
    r = S.split_text(t)
    f = r['flags']
    assert f['appendix_found'] and f['appendix_position'] == 'after_refs' and f['appendix_rule'] == 'appendix'
    assert 'Appendix A' in r['appendix'] and 'Appendix B' in r['appendix']
    assert 'References' not in r['main'] and 'Appendix' not in r['main'] and r['references'].startswith('References')
    assert f['main_words'] > 400 and f['appendix_words'] > 400 and f['refs_found']


def test_appendix_before_references_journal_style():
    t = doc(PROSE, '2 Method\n' + PROSE, 'Appendix A. Derivations\n' + PROSE, REFS)
    r = S.split_text(t)
    assert r['flags']['appendix_position'] == 'before_refs'
    assert 'Derivations' in r['appendix'] and 'Derivations' not in r['main'] and 'Journal of Things' not in r['appendix']


def test_appendix_split_around_references():
    t = doc(PROSE, 'Appendix A. Derivations\n' + PROSE, REFS, 'Supplementary Material\n' + PROSE)
    r = S.split_text(t)
    assert r['flags']['appendix_position'] == 'split'
    assert 'Derivations' in r['appendix'] and 'Supplementary Material' in r['appendix'] and 'Journal of Things' not in r['appendix']


def test_no_appendix():
    r = S.split_text(doc(PROSE, '2 Method\n' + PROSE, REFS))
    assert not r['flags']['appendix_found'] and r['appendix'] == '' and r['flags']['appendix_position'] is None


def test_lettered_appendix_needs_a_sequence_and_follows_the_conclusion():
    body = 'A Proof of Theorem 1\n' + PROSE + '\n\nB Additional experiments\n' + PROSE
    r = S.split_text(doc(PROSE, '5 Conclusion\n' + PROSE, REFS, body))
    assert r['flags']['appendix_rule'] == 'lettered' and r['appendix'].startswith('A Proof of Theorem 1')
    # an 'A' heading with no 'B' / 'A.1' continuation is not an appendix
    r2 = S.split_text(doc(PROSE, '5 Conclusion\n' + PROSE, REFS, 'A Proof of Theorem 1\n' + PROSE))
    assert not r2['flags']['appendix_found']


def test_subsection_letters_inside_the_paper_are_not_appendices():
    t = doc('II. Method\nA. Setup\n' + PROSE, 'B. Training\n' + PROSE, 'C. Evaluation\n' + PROSE, 'V. Conclusion\n' + PROSE, REFS)
    assert not S.split_text(t)['flags']['appendix_found']


def test_figure_panel_labels_are_not_an_appendix():
    t = doc(PROSE, '5 Conclusion\n' + PROSE, 'A CLC loci\nB LncRNA 64 8\nChain alignment\n', REFS)
    assert not S.split_text(t)['flags']['appendix_found']


def test_inline_mention_of_an_appendix_is_not_a_heading():
    t = doc(PROSE + '\nAppendix C. Figure 3 shows examples of the state queries\nbuilt by each heuristic.\n' + PROSE, REFS)
    assert not S.split_text(t)['flags']['appendix_found']


def test_small_caps_headings():
    t = doc(PROSE, '5 Conclusion\n' + PROSE, 'R EFERENCES\n' + REFS[len('References\n'):], 'A PPENDIX A P ROOF OF L EMMA 1\n' + PROSE)
    r = S.split_text(t)
    assert r['flags']['appendix_found'] and r['flags']['refs_found'] and 'EFERENCES' not in r['main']


def test_stub_supplementary_is_not_an_appendix():
    t = doc(PROSE, 'Supplementary Material\nSupplementary material is available online at the journal website.\n\n', REFS)
    r = S.split_text(t)
    assert not r['flags']['appendix_found']
    t2 = doc(PROSE, 'Supplementary Material\nFigure S1. A tiny legend.\n\n', REFS)
    r2 = S.split_text(t2)
    assert r2['flags'].get('appendix_stub') and r2['appendix'] == ''


def test_online_methods_are_main_text():
    t = doc(PROSE, 'Online Methods\n' + PROSE, REFS)
    assert not S.split_text(t)['flags']['appendix_found']


def test_supplementary_rule_is_tagged():
    t = doc(PROSE, REFS, 'Supplementary Material\n' + PROSE)
    f = S.split_text(t)['flags']
    assert f['appendix_found'] and f['appendix_rule'] == 'supplementary'


def test_table_of_contents_is_not_an_introduction_or_appendix():
    toc = 'Contents\n1 Introduction . . . . . . . . . . . 1\nAppendix . . . . . . . . . . . . . 30\n\n'
    r = S.split_text(toc + FRONT.replace('A Paper Title', 'Title') + PROSE + '\n\n' + REFS)
    assert r['flags']['intro_found'] and not r['flags']['appendix_found']


def test_reference_list_without_heading_is_trimmed():
    refs = ' '.join(f'Author {i}, B. et al. Title {i}. Proc. of the Conference, {2000 + i}, pp. 1-10, doi:10.1/{i}.' for i in range(60))
    r = S.split_text(doc(PROSE, '3 Conclusion\n' + PROSE, refs))
    assert not r['flags']['refs_found'] or r['flags'].get('refs_heuristic')
    assert 'Proc. of the Conference' not in r['main'][-2000:]


def test_main_matches_vendored_body_up_to_the_references():
    """The main text is the vendored body (Introduction to the references heading) when there is no appendix."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vendor' / 'homogenization_tools'))
    import fulltext_store as fs
    t = doc(PROSE, '2 Method\n' + PROSE, REFS)
    assert S.split_text(t)['main'] == fs.sections(t, 'A Paper Title')['body']


JATS = '<article><body><sec><title>Introduction</title><p>%s</p></sec></body><back>%s<ref-list><ref>[1] Someone. A paper. 2001.</ref></ref-list></back></article>'
APP = '<app-group><app><title>Appendix A: Details</title><p>%s</p></app></app-group>'


def test_jats_back_appendix():
    r = S.split_xml(JATS % (PROSE, APP % PROSE))
    f = r['flags']
    assert f['appendix_found'] and f['appendix_rule'] == 'xml_back' and f['appendix_position'] == 'before_refs'
    assert 'Details' in r['appendix'] and 'Details' not in r['main'] and f['refs_found']


def test_jats_appendix_after_the_reference_list():
    raw = '<article><body><sec><title>Introduction</title><p>%s</p></sec></body><back><ref-list><ref>[1] x 2001.</ref></ref-list>%s</back></article>' % (PROSE, APP % PROSE)
    assert S.split_xml(raw)['flags']['appendix_position'] == 'after_refs'


def test_tei_annex():
    raw = ('<TEI><text><body><div><head>Introduction</head><p>%s</p></div></body><back><div type="annex"><head>Appendix A</head><p>%s</p></div>'
           '<div type="references"><listBibl><biblStruct>x 2001</biblStruct></listBibl></div></back></text></TEI>') % (PROSE, PROSE)
    r = S.split_xml(raw)
    assert r['flags']['appendix_found'] and r['flags']['refs_found'] and r['flags']['appendix_words'] > 100


def test_xml_without_appendix():
    r = S.split_xml(JATS % (PROSE, ''))
    assert not r['flags']['appendix_found'] and r['main']


def test_passages_are_tagged_and_main_equals_todays_rule():
    def passages(body, cap=100):
        w = body.split()
        return [' '.join(w[i:i + 150]) for i in range(0, len(w) - 39, 150)][:cap]
    tagged = S.passages_tagged('word ' * 400, 'other ' * 200, passages)
    assert [s for s, _ in tagged].count('main') == len(passages('word ' * 400)) and [s for s, _ in tagged].count('appendix') == 2


def test_missing_file_is_an_error_not_an_exception(tmp_path):
    assert S.split_file(tmp_path / 'none.pdf') == {'error': 'missing'}
