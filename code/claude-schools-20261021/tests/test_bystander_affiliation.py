"""Named bystander affiliations must not become the PI's own school evidence."""
import collections
import copy
import re
from types import SimpleNamespace

import pytest

from pihier import papers
from test_build_rules import au, run_stages, work, write_school


PI = 'Susan A Murphy'
INST = 'https://openalex.org/I136199984'
# Relevant original fields: institutional snapshot year2022/page75, body SHA256
# 4f79f2c3bddcf552484757e56b17a26b5a446c0355cde0ac19e8f95b339a2093.
BAKER_HARVARD = 'Harvard T. H. Chan School of Public Health, Harvard University, Boston, Massachusetts (Dr Baker)'
MURPHY_COMPANY = 'Business Consultants Group, Inc, Rancho Mirage, California (Dr Murphy)'


def authorship(name, aid, raw, institutions=True):
    return dict(raw_author_name=name, author=dict(id=aid, display_name=name), author_position='last',
                institutions=[dict(id=INST, display_name='Harvard University', lineage=[INST], type='education')]
                if institutions else [], raw_affiliation_strings=list(raw))


def packet(raw=None):
    baker = authorship('Edward L. Baker', 'A5113689095', [BAKER_HARVARD])
    murphy = authorship('Susan A. Murphy', 'A5070589969', raw if raw is not None else [
        'UNC Gillings School of Global Public Health, Chapel Hill, North Carolina (Dr Baker)',
        'and ' + MURPHY_COMPANY, MURPHY_COMPANY, BAKER_HARVARD, 'The authors declare no conflicts of interest'])
    # The structured field incorrectly repeats the combined institutional mapping too.
    murphy['institutions'].append(dict(id='https://openalex.org/I114027177',
                                      display_name='University of North Carolina at Chapel Hill', type='education'))
    murphy['author']['orcid'] = 'https://orcid.org/0000-0002-2032-4286'
    return dict(id='https://openalex.org/W4281561714', title='Delegation: A Core Leadership Skill',
                doi='https://doi.org/10.1097/phh.0000000000001545', publication_year=2022,
                authorships=[baker, murphy]), murphy


def context():
    return SimpleNamespace(school='harvard', n=collections.Counter(), inst=INST, aff=re.compile(r'harvard', re.I),
                           tied={}, pi_units=collections.defaultdict(set), school_units=set(),
                           anchored=collections.defaultdict(collections.Counter), advisee_names=collections.defaultdict(list),
                           adv_full=collections.defaultdict(set), from_pw=set(),
                           pid0={PI: dict(names=['Susan A Murphy'])}, direct_years=collections.defaultdict(collections.Counter))


def test_original_packet_rejects_bakers_address_and_preserves_unknown_person_identity():
    w, a = packet(); before = copy.deepcopy(w); ctx = context()
    assert papers.school_basis(ctx, PI, w, a, 'pi_orcid', None)[0] == []
    assert w == before  # no identity verdict, author block, source edit or ORCID rewrite
    assert ctx.n['school_affiliation_explicit_other_author'] == 1


@pytest.mark.parametrize('qualifier', ['Dr Murphy', 'Dr. Susan A. Murphy', 'Dr S. Murphy',
                                       'Drs Baker and Murphy', 'Drs Baker, Murphy', 'Dr Baker & Dr Murphy'])
def test_own_and_explicitly_shared_named_affiliations_stay(qualifier):
    w, a = packet(['Harvard University (' + qualifier + ')'])
    assert papers.school_basis(context(), PI, w, a, 'pi_orcid', None)[0]


def test_a_combined_string_is_segmented_before_deciding_which_author_owns_the_school():
    w, a = packet([BAKER_HARVARD + '; and ' + MURPHY_COMPANY])
    assert papers.school_basis(context(), PI, w, a, 'pi_orcid', None)[0] == []


@pytest.mark.parametrize('raw', ['Harvard University', 'Harvard University (Boston)',
                                'Harvard University (Dr Unknown)', 'Harvard University (Dr B)',
                                'Harvard University (Baker)', 'Harvard University (Dr Baker and Unknown)'])
def test_unparseable_or_unresolved_qualifiers_are_not_assumed_to_prove_another_author(raw):
    w, a = packet([raw])
    assert papers.school_basis(context(), PI, w, a, 'pi_orcid', None)[0]


def test_same_family_name_is_ambiguous_and_must_not_be_declared_other_only():
    w, a = packet(['Harvard University (Dr Murphy)'])
    w['authorships'][0]['raw_author_name'] = 'Edward Murphy'
    w['authorships'][0]['author']['display_name'] = 'Edward Murphy'
    assert papers.school_basis(context(), PI, w, a, 'pi_orcid', None)[0]


def test_explicit_other_author_evidence_cannot_be_recovered_through_R11():
    w, a = packet(); a['institutions'] = []; ctx = context()
    ctx.advisee_names[PI] = [re.compile('Edward', re.I)]
    assert papers.school_basis(ctx, PI, w, a, 'pi_orcid', None)[0] == []
    assert ctx.n['school_via_advisee_coauthor'] == 0


def test_explicit_other_author_evidence_cannot_be_recovered_through_company_cross_affiliation():
    w, a = packet(); a['institutions'] = [dict(display_name='Business Consultants Group', type='company')]
    ctx = context(); ctx.direct_years[PI][2022] = 3
    assert papers.school_basis(ctx, PI, w, a, 'pi_orcid', None)[0] == []
    assert ctx.n['school_via_cross_affiliation'] == 0


def test_R11_does_not_borrow_a_wrongly_assigned_advisees_structured_institution():
    w, a = packet(); a['institutions'] = []; a['raw_affiliation_strings'] = []
    w['authorships'][0]['raw_affiliation_strings'] = ['Harvard University (Dr Smith)']
    w['authorships'].append(authorship('Terry Smith', 'A3', [], institutions=False))
    ctx = context(); ctx.advisee_names[PI] = [re.compile('Edward', re.I)]
    assert papers.school_basis(ctx, PI, w, a, 'pi_orcid', None)[0] == []


def test_independent_primary_page_one_tie_can_correct_a_derived_mapping():
    w, a = packet(); ctx = context()
    ctx.tied[w['id']] = dict(how='footnote', quotes=['Susan A Murphy, Harvard University'])
    via, _ = papers.school_basis(ctx, PI, w, a, 'pi_orcid', None)
    assert via and via[0].startswith('page 1')


@pytest.mark.usefixtures('layout')
def test_native_pipeline_withholds_only_the_wrong_school_relation_not_the_whole_author(tmp_path):
    bad = work('W100', 'A false affiliation fixture', 2020, [
        au('Ada Lovelace', 'A1', raw=['Princeton University (Dr Turing)', 'Example Company (Dr Lovelace)']),
        au('Alan Turing', 'A9', raw=['Princeton University (Dr Turing)'])])
    good = work('W101', 'A valid affiliation fixture', 2020, [
        au('Ada Lovelace', 'A1', raw=['Princeton University (Drs Lovelace and Turing)']), au('Alan Turing', 'A9')])
    write_school(tmp_path, sweep=[bad, good]); ctx = run_stages(tmp_path, upto='papers')
    assert [r['title'] for r in ctx.rows if r['pi'] == 'Ada Lovelace'] == ['A valid affiliation fixture']
    assert ctx.n['school_affiliation_explicit_other_author'] == 1


@pytest.mark.usefixtures('layout')
def test_native_school_byline_does_not_relabel_a_bystander_as_affiliated(tmp_path):
    paper = work('W102', 'A valid paper with a wrong coauthor slot', 2020, [
        au('Ada Lovelace', 'A1', raw=['Princeton University (Dr Lovelace)']),
        au('Alan Turing', 'A9', raw=['Princeton University (Dr Lovelace)'])])
    write_school(tmp_path, sweep=[paper]); ctx = run_stages(tmp_path, upto='papers')
    result = next(r for r in ctx.rows if r['pi'] == 'Ada Lovelace')
    assert result['byline'] == ['Ada Lovelace', 'Alan Turing']
    assert result['byline_school'] == ['Ada Lovelace']
