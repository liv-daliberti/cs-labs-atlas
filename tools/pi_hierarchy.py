"""One school's PI hierarchy package (owner decisions 2026-10-21): department -> PI lab -> papers + students -> student papers.

pis        every census faculty member with is_pi; each gets one own lab (PI + advisees). A census lab unit is reused only
           when the collection unit has this PI as its single leader; otherwise a new own lab is proposed and the
           multi-leader / umbrella unit stays a collective (not a lab).
papers     an OpenAlex work from hierarchy/<school>/openalex-sweep.sqlite is the PI's lab paper when
             (a) an authorship matches the PI's name and its OWN institutions (lineage) or raw affiliation strings name the
                 school, and
             (b) that authorship is the PI: the work is on the PI's own DBLP person page (census PID; cached DBLP
                 publication lists, matched by DOI or title) or is one of the PI's DBLP-verified collection works, or a
                 stated advisee of the PI is a co-author, or the authorship's OpenAlex author id is anchored (it sits at the
                 PI's name on one of those works), and
             (c) the paper falls in the PI's appointment: contains() against a reviewed faculty period (the site's rule,
                 boundary years unresolved), else a captured department listing from the paper's own year that names the
                 PI (owner decision 2026-10-21; it proves that calendar year only).
           Works are matched to collection works by DOI, else normalized title within one year; the rest are new works.
students   people whose advising context names the PI (by person id, or by name), and direct lab memberships of a reused
           unit. Advising is the owner's lab model (PI + advisees); the relation and its sources are kept.
student    a lab paper with a lab student on its byline: the student's collection personLink (status kept), or for a new
papers     work an authorship that matches the student's name and lists the school (candidate).
-> hierarchy/<school>/pis.json, lab_papers.jsonl.gz, students.json, student_papers.jsonl.gz, report.json


The code is the package tools/pihier/, one module per stage (its docstring lists them); this file is the entry point and
re-exports every name the builder had, so callers keep `from pi_hierarchy import ...`.

usage: pi_hierarchy.py <school> [<school> ...]
"""
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:  # loaded by file path (importlib) from elsewhere
    sys.path.append(str(Path(__file__).resolve().parent))

from pihier import names as _names, papers as _papers, identity as _identity  # noqa: E402  (the read-once caches, below)
from pihier.common import (HERE, SITE, DBLP, INST, AFF, TODAY, WINDOW_START, NOT_PAPERS, SCHOOL_LOOSE, OWN_UNITS,  # noqa: E402,F401
                           read, norm_title, ndoi, source_year, sweep_works, best_sources, as_list)
from pihier.names import (NICK, _nick_pairs, nick_ok, LETTERS, toks, given, SUFFIX, nosuffix, DEGREE_JUNK,  # noqa: E402,F401
                          clean_person_name, _fold, names_full_form, Name, same_student, hyphen_half, byline_name,
                          name_variants, student_on_byline, one_edit, EAST_ASIAN_FAMILY, strict_name_one, strict_name,
                          _words, name_conflict, full_pair, all_initials, gwords, given_conflict, dedupe_tokens)
from pihier.periods import (SEASON, datebounds, contains, same_year, transition_side, _year, listings_after_move,  # noqa: E402,F401
                            NOT_FACULTY, INCOMING, not_faculty_row)
from pihier.census import COLLECTIVE  # noqa: E402,F401
from pihier.students import (ADV_RX, ADVISING_LABEL, WEAK_LABEL, advising_label, ADVISER_NAMED,  # noqa: E402,F401
                             relation_names_other_adviser, relation_is_weak, PROGRAM_Q, ACADEMIC_ADVISOR_Q,
                             program_adviser_groups, relation_is_program_advising, ADVISER_LABEL, own_roster_entry,
                             DSPACE_ADVISOR, dspace_advisors, apply_relation_evidence, relation_own_entry_names_other,
                             basis_advisees, rekey_pi_person_ids)
from pihier.papers import (EN_WORDS, FOREIGN_WORDS, foreign_title, fold_books, doi_book_prefix, SUPPLEMENT_TITLE,  # noqa: E402,F401
                           ERRATUM_TITLE, EDITORIAL_TITLE, AWARD_TITLE, AWARD_END, WORKSHOP_TITLE, TUTORIAL_ON,
                           HIGHLIGHTS_TITLE, TRIBUTE_TITLE, LIFE_DATES, COMMON_WORD_NAMES, NOUN_SUFFIX, given_names,
                           person_name_title, ABSTRACT_VENUE, ABSTRACT_DOI, ABSTRACT_TITLE, ABSTRACT_JOURNALS,
                           THESIS_REPOSITORY_DOI, not_a_paper, doi_year_conflict, norm_unit, PLACE, units_in,
                           DISCIPLINE_WORDS, generic_unit, page1_head, AFFILIATION_MARK, page1_elsewhere, OTHER_INST,
                           names_other_inst, venue_version_date, bare_unit_school)
from pihier.links import near_relation, relation_source  # noqa: E402,F401
from pihier.build import build  # noqa: E402,F401

# Read-once caches live in their stage module; reading them here gives the live value. To reset one, set it on its module
# (pihier.names.NICK_MAP = None).
_CACHES = {'NICK_MAP': _names, 'GIVEN_NAMES': _papers, 'DUMP_PERSONS': _identity}


def __getattr__(name):
    if name in _CACHES:
        return getattr(_CACHES[name], name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


if __name__ == '__main__':
    for s in sys.argv[1:]:
        build(s)
