"""tools/pi_hierarchy.py is the entry point of the split builder (tools/pihier/, ROADMAP item 8) and must keep every name
it had and every name a caller imports from it: a missing re-export fails here, not at rebuild time."""
import ast
import subprocess
from pathlib import Path

import pi_hierarchy

CODE = Path(__file__).resolve().parents[1]

# every top-level name of tools/pi_hierarchy.py before the split (commit a62a04a)
BEFORE_SPLIT = '''HERE SITE DBLP INST AFF TODAY WINDOW_START COLLECTIVE NOT_PAPERS ADV_RX NICK _nick_pairs NICK_MAP DUMP_PERSONS nick_ok
read LETTERS toks given SUFFIX nosuffix DEGREE_JUNK clean_person_name ADVISING_LABEL WEAK_LABEL advising_label ADVISER_NAMED
relation_names_other_adviser relation_is_weak PROGRAM_Q ACADEMIC_ADVISOR_Q program_adviser_groups relation_is_program_advising
ADVISER_LABEL _fold names_full_form own_roster_entry DSPACE_ADVISOR dspace_advisors apply_relation_evidence
relation_own_entry_names_other near_relation Name same_student hyphen_half byline_name name_variants student_on_byline one_edit
EAST_ASIAN_FAMILY strict_name_one strict_name _words name_conflict norm_title ndoi SEASON datebounds contains same_year EN_WORDS
FOREIGN_WORDS foreign_title transition_side _year listings_after_move full_pair all_initials gwords given_conflict fold_books
doi_book_prefix SUPPLEMENT_TITLE ERRATUM_TITLE EDITORIAL_TITLE AWARD_TITLE AWARD_END WORKSHOP_TITLE TUTORIAL_ON HIGHLIGHTS_TITLE
TRIBUTE_TITLE LIFE_DATES COMMON_WORD_NAMES NOUN_SUFFIX GIVEN_NAMES given_names person_name_title ABSTRACT_VENUE ABSTRACT_DOI
ABSTRACT_TITLE ABSTRACT_JOURNALS THESIS_REPOSITORY_DOI not_a_paper doi_year_conflict dedupe_tokens norm_unit PLACE units_in
DISCIPLINE_WORDS generic_unit page1_head SCHOOL_LOOSE AFFILIATION_MARK page1_elsewhere source_year sweep_works NOT_FACULTY
OTHER_INST OWN_UNITS names_other_inst INCOMING not_faculty_row basis_advisees best_sources venue_version_date bare_unit_school
rekey_pi_person_ids relation_source as_list build'''.split()


def test_every_name_before_the_split_is_still_there():
    missing = [n for n in BEFORE_SPLIT if not hasattr(pi_hierarchy, n)]
    assert not missing, missing


def caller_names():
    """(file, name) for every `from pi_hierarchy import name` and every `<alias>.name` on `import pi_hierarchy as <alias>`
    in the tracked Python files."""
    files = subprocess.run(['git', '-C', str(CODE), 'ls-files', '*.py'], capture_output=True, text=True, check=True).stdout.split()
    out = []
    for f in files:
        p = CODE / f
        if not p.exists() or f.startswith(('tools/pihier/', 'vendor/')) or f == 'tools/pi_hierarchy.py':
            continue
        try:
            tree = ast.parse(p.read_text())
        except (SyntaxError, UnicodeDecodeError):
            continue
        aliases = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == 'pi_hierarchy':
                out += [(f, a.name) for a in node.names if a.name != '*']
            elif isinstance(node, ast.Import):
                aliases |= {a.asname or a.name for a in node.names if a.name == 'pi_hierarchy'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases \
                    and isinstance(node.ctx, ast.Load):
                out.append((f, node.attr))
    return out


def test_every_name_a_caller_uses_is_exported():
    used = caller_names()
    assert len({f for f, _ in used}) >= 20                                                 # the scan found the callers
    missing = sorted({(f, n) for f, n in used if not hasattr(pi_hierarchy, n)})
    assert not missing, missing


def test_the_caches_read_live():
    import pihier.names
    pi_hierarchy.nick_ok('a', 'b')
    assert pi_hierarchy.NICK_MAP is pihier.names.NICK_MAP is not None
