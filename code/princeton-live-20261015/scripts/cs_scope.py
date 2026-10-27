"""The computer-science scope of the research atlas: the one place that defines it.

Owner request (2026-10-21): "for all schools to only show CS departments / related to
CS departments / staff". The atlas keeps every field on disk and shows only this scope.

A lab is in the CS atlas when EITHER
  1. its `field` is computer_and_information_sciences ("field"), OR
  2. its recorded `department` (the lab's primary department string) names a computing
     department ("department"): DEPARTMENT_TERMS below, matched case-insensitively
     anywhere in the string.
A lab matching both has reason "field_and_department". A lab matching neither is still in
scope when it is a PI lab of the CS departments view ("cs_department_pi_lab": a faculty PI
the computing departments list but who is homed elsewhere, e.g. an associated professor's
lab in Psychology); atlas/data/cs-hierarchy is built first (scripts/build-cs-hierarchy.py).

Inside the CS view a lab is grouped under the computing departments among its recorded
department labels; a lab with none (a CS-field lab in, say, Mathematics) keeps the
departments it has. This is applied by atlas/assets/cs-scope.js with the same pattern.

To change the scope, edit FIELD or DEPARTMENT_TERMS and run
    python3 scripts/build-cs-scope.py
which re-marks every university shard (csScope / csScopeReason on each lab), rewrites the
CS count cells and metrics, and copies this rule into data.json (`csScope.rule`) and
atlas/data/cs-scope-rule.json for the browser. Never edit the pattern anywhere else.
`python3 scripts/test-cs-scope.py` checks the result.

What the atlas SHOWS (owner decision 2026-10-22, "PI labs with papers only"; see SHOWN_RULE):
  * at a school of the CS departments view (atlas/data/cs-hierarchy/index.json: Princeton, CMU,
    EPFL, MIT, Berkeley) the atlas shows that school's PI labs, built from
    atlas/data/cs-hierarchy/<school>.json.gz, and only those with at least one lab paper
    (hidden: "no_lab_papers"). The school's inventory units are hidden ("replaced_by_pi_labs");
    their shards, lab and people files stay on disk;
  * at every other university it shows the in-scope CS units with at least one linked paper in
    any publication view (hidden: "no_papers").
The build marks each shard lab `csShown` / `csHidden` (unit_visibility) and writes the PI labs it
shows to atlas/data/cs-pi-labs/<university>.json.gz (pi_lab_visibility, atlas_lab_ids).
Hiding never deletes data and never changes `csScope` (the CS field/department scope above).

Not computing departments (deliberately unmatched): MIT IDSS, Media Lab, RLE and Lincoln
Laboratory; plain Mechanical, Civil, Chemical, Materials or Electrical(-only) Engineering.
Labs there are in scope only through their field.
"""
import gzip, json, re
from pathlib import Path

FIELD = 'computer_and_information_sciences'
PI_LAB = 'cs_department_pi_lab'
HIERARCHY = Path(__file__).resolve().parents[1] / 'atlas/data/cs-hierarchy'


def hierarchy_schools():
    """[{id, uni, file}] for every school of the CS departments view (atlas/data/cs-hierarchy/index.json)."""
    if not (HIERARCHY / 'index.json').exists():
        return []
    return [dict(id=s['id'], uni=s['uni'], file=f"data/cs-hierarchy/{s['id']}.json.gz")
            for s in json.loads((HIERARCHY / 'index.json').read_text())['schools']]


def read_hierarchy(school):
    return json.loads(gzip.decompress((HIERARCHY / f"{school['id']}.json.gz").read_bytes()))


def pi_lab_ids():
    """{university id: site lab ids of the CS departments' PI labs} (atlas/data/cs-hierarchy).
    `siteLab` is the inventory unit build-cs-hierarchy.py found for the PI lab; it marks that unit
    in scope (PI_LAB) even when its field and department are not computing ones."""
    return {s['uni']: frozenset(l['siteLab'] for l in read_hierarchy(s)['labs'] if l.get('siteLab'))
            for s in hierarchy_schools()}


# ---- What the atlas shows (owner decision 2026-10-22, "PI labs with papers only") -----------
VIEWS = ('combined', 'reviewed', 'strict')
HIDDEN_REASONS = {
    'no_papers': 'CS unit without papers',
    'replaced_by_pi_labs': 'inventory unit of a school whose CS departments are shown as PI labs',
    'no_lab_papers': 'PI lab without lab papers',
}
SHOWN_RULE = ('The atlas shows, at a school of the CS departments view, that school\'s PI labs with at least one '
              'lab paper (atlas/data/cs-hierarchy; its inventory units are hidden as replaced_by_pi_labs), and at '
              'every other university the in-scope CS units with at least one linked paper in any publication view '
              '(others hidden as no_papers). Hidden records stay on disk.')


def unit_has_papers(lab):
    """An inventory unit has papers when any publication view links it to at least one work."""
    counts = lab.get('paperCounts') or {}
    return any(sum((counts.get(view) or {}).values()) > 0 for view in VIEWS)


def unit_visibility(lab, scope_reason, pi_lab_school):
    """(shown, hidden reason) of an inventory unit. scope_reason: reason() of the lab;
    pi_lab_school: its university is a school of the CS departments view."""
    if scope_reason is None:
        return False, None              # outside computer science: not a hidden CS unit
    if pi_lab_school:
        return False, 'replaced_by_pi_labs'
    if not unit_has_papers(lab):
        return False, 'no_papers'
    return True, None


def pi_lab_visibility(hierarchy_lab):
    """(shown, hidden reason) of a PI lab of the CS departments view."""
    return (True, None) if hierarchy_lab.get('papers') else (False, 'no_lab_papers')


def atlas_lab_ids(hierarchy_labs):
    """Atlas ids of a school's PI labs: the hierarchy id; a repeated id gets ~2, ~3 in file order.
    A link with the plain hierarchy id (cs-departments.js) therefore opens its first occurrence."""
    seen, out = {}, []
    for lab in hierarchy_labs:
        n = seen[lab['id']] = seen.get(lab['id'], 0) + 1
        out.append(lab['id'] if n == 1 else f"{lab['id']}~{n}")
    return out

# One regex alternative per entry. Each must be valid in both Python `re` and JavaScript
# RegExp (no lookbehind, no \b, no named groups); both use case-insensitive matching.
DEPARTMENT_TERMS = [
    r'comput',                              # computing, computer, computation(al)
    r'informati(?:c|k|que)',                # informatics, Informatik, informatique, informatica
    r'(?:^|[^a-z])eecs(?:[^a-z]|$)',        # EECS as a word
    r'electrical\s*(?:&|and)\s*computer',   # electrical and computer engineering
    r'data\s*science',
    r'artificial\s*intelligence',
    r'robotic',
    r'software',
    r'machine\s*learning',
    r'language\s*technolog',                # e.g. CMU Language Technologies Institute
    r'human[\s\-‐-―]*computer',   # human-computer interaction, any dash
    r'information\s*(?:science|technolog|system)',
    r'school\s*of\s*information',
    r'cyber',
    r'intelligent\s*systems',
    '计算机',                   # 计算机 computer
    '软件',                         # 软件 software
    '人工智能',             # 人工智能 artificial intelligence
    '컴퓨터',                   # 컴퓨터 computer (Korean)
]
DEPARTMENT_PATTERN = '|'.join(DEPARTMENT_TERMS)
_DEPARTMENT = re.compile(DEPARTMENT_PATTERN, re.IGNORECASE)

# Department names that match only as computational science, medical or bio informatics,
# or quantum computing. They stay IN scope (CMU's Computational Biology Department is a
# School of Computer Science department); the build report lists them for the owner.
BORDERLINE_TERMS = [
    r'(?:bio|medical|biomedical|health|clinical|medizinische)\s*informati',
    r'computational\s+(?:biology|medicine|biomedicine|neuroscience|genomics|health)',
    r'quantum\s*comput',
]
_CORE = re.compile(r'computer|computing|(?:^|[^a-z])eecs(?:[^a-z]|$)|software|robotic|machine\s*learning'
                   r'|artificial\s*intelligence|计算机|컴퓨터', re.IGNORECASE)
_BORDERLINE = re.compile('|'.join(BORDERLINE_TERMS), re.IGNORECASE)

REASONS = ('field', 'department', 'field_and_department', PI_LAB)


def computing_department(name):
    """True when a department string names a computing department."""
    return isinstance(name, str) and bool(_DEPARTMENT.search(name))


def borderline_department(name):
    """A matched department that is only computational science / bio-medical informatics /
    quantum computing, with no other computing term. Reported, never excluded."""
    if not computing_department(name):
        return False
    if _BORDERLINE.search(name):
        return not _CORE.search(_BORDERLINE.sub(' ', name))
    return bool(re.search(r'computation', name, re.IGNORECASE)) and not _CORE.search(name) \
        and not re.search(r'informati|data\s*science|information\s*(?:science|technolog|system)'
                          r'|school\s*of\s*information|language\s*technolog|cyber|intelligent\s*systems'
                          r'|软件|人工智能', name, re.IGNORECASE)


def reason(lab, pi_labs=frozenset()):
    """'field', 'department', 'field_and_department', PI_LAB, or None when out of scope.
    pi_labs: the university's CS-department PI lab ids (pi_lab_ids())."""
    by_field = lab.get('field') == FIELD
    by_department = computing_department(lab.get('department') or '')
    if by_field and by_department:
        return 'field_and_department'
    if by_field:
        return 'field'
    if by_department:
        return 'department'
    if lab.get('id') in pi_labs:
        return PI_LAB
    return None


def in_scope(lab, pi_labs=frozenset()):
    return reason(lab, pi_labs) is not None


def department_labels(labels):
    """The department labels a CS lab is grouped under in the CS view (see cs-scope.js)."""
    computing = [x for x in labels if computing_department(x)]
    return computing or list(labels)


def browser_rule():
    """The generated copy of this rule that the browser applies (never edit the copy)."""
    return {
        'schema': 1,
        'field': FIELD,
        'departmentPattern': DEPARTMENT_PATTERN,
        'flags': 'i',
        'reasons': list(REASONS),
        'source': 'scripts/cs_scope.py',
        'rule': 'A lab is in the CS atlas when its field is ' + FIELD + ' or its recorded department '
                'matches departmentPattern (case-insensitive), or it is a PI lab of the CS departments view '
                '(csScopeReason ' + PI_LAB + ', marked by the build). In the CS view a lab is grouped under its '
                'computing department labels; a lab with none keeps its recorded departments.',
        'shown': SHOWN_RULE,
        'hiddenReasons': HIDDEN_REASONS,
    }


def count_cells(labs, uid, departments=False):
    """Inventory count cells with exactly the semantics of the existing data.json `counts`.

    Reproduces counts() in scripts/project-claude-refresh-people.py (and the identical
    helpers in project-collection-people.py / project-mit-cs.py), which matches every
    university's current cells: one cell per (field, leadershipStatus[, department]);
    n labs; named = PI text present; reviewed = status leadership_reviewed or
    publication_identity_verified; verified = status publication_identity_verified;
    active = any dated year; years = labs per dated year.
    """
    groups = {}
    for lab in labs:
        key = (lab.get('field', 'interdisciplinary'), lab.get('leadershipStatus', 'missing_name'),
               lab.get('department', '') if departments else '')
        if key not in groups:
            groups[key] = {'u': uid, 'field': key[0], 'status': key[1], 'n': 0, 'named': 0, 'reviewed': 0,
                           'verified': 0, 'active': 0, 'years': {}}
            if departments:
                groups[key]['department'] = key[2]
        cell = groups[key]
        cell['n'] += 1
        cell['named'] += int(bool(lab.get('pi')))
        cell['reviewed'] += int(key[1] in ('leadership_reviewed', 'publication_identity_verified'))
        cell['verified'] += int(key[1] == 'publication_identity_verified')
        cell['active'] += int(bool(lab.get('years')))
        for year in sorted(set(lab.get('years', []))):
            cell['years'][str(year)] = cell['years'].get(str(year), 0) + 1
    return list(groups.values())
