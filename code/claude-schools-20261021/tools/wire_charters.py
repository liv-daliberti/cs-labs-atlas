"""Make the builder's own school tables read the charters (schools/<key>.toml): the prepared change for the files another
agent owned while Michigan was onboarded (2026-10-29). Run once that agent's release is cut; it edits the files in place
and is idempotent (an anchor that is already replaced is skipped; an anchor that is missing stops the run with no edits).

tools/pi_hierarchy.py   DBLP, INST, AFF, SCHOOL_LOOSE, OWN_UNITS from the charters; the EPFL-only foreign-title exception
                        from [rules].foreign_title_exception
tools/chain_audit.py    SCHOOLS = atlas_paths.SCHOOL_IDS (the released schools; name an onboarding school on the command line)
tools/export_release.py ORDER = atlas_paths.SCHOOL_IDS
tools/organize_tree.py  NAMES from the charters
After running: pytest (tests/test_school_config.py checks that the charters and the builder agree), then commit.
usage: wire_charters.py [--dry]
"""
import re, sys
from pathlib import Path

T = Path(__file__).resolve().parent

EDITS = {
    'pi_hierarchy.py': [
        (re.compile(r"^DBLP = \{'cmu'.*?\n(?=INST = )", re.S | re.M),
         "import school_config as _S  # noqa: E402  (the school charters schools/<key>.toml: protocol stage 0)\n"
         "DBLP = {k: _S.dblp_sweep(k) for k in _S.keys() if _S.dblp_sweep(k)}  # pre-protocol schools' cached DBLP lists\n"),
        (re.compile(r"^INST = \{'princeton': 'I20089843'.*?\n", re.M),
         "INST = {k: _S.inst(k) for k in _S.keys()}  # the primary lineage id ([ids].openalex[0])\n"),
        (re.compile(r"^AFF = \{'princeton'.*?\n(?=TODAY = )", re.S | re.M),
         "AFF = {k: _S.aff(k) for k in _S.keys()}  # [affiliation].regex, tested by school_config.py --check\n"),
        (re.compile(r"^SCHOOL_LOOSE = \{'princeton'.*?'stanford': r'stanford'\}\n", re.S | re.M),
         "SCHOOL_LOOSE = {k: _S.field(_S.get(k), 'affiliation.loose') or _S.aff(k) for k in _S.keys()}\n"),
        (re.compile(r"^OWN_UNITS = \{'cmu': re\.compile\(.*?re\.I\)\}\n", re.S | re.M),
         "OWN_UNITS = {k: rx for k in _S.keys() for rx in [_S.own_units(k)] if rx}  # [affiliation].own_units (R-PAP-09)\n"),
        (re.compile(r"    if school != 'epfl':\n"),
         "    if not _S.field(_S.get(school), 'rules.foreign_title_exception'):  # R-PAP-15 (EPFL's French titles are originals)\n"),
    ],
    'chain_audit.py': [
        (re.compile(r"^SCHOOLS = \['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford'\]\n", re.M),
         "SCHOOLS = list(P.SCHOOL_IDS)  # the released schools (schools/<key>.toml); an onboarding school is named on the command line\n"),
    ],
    'export_release.py': [
        (re.compile(r"^ORDER = \['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford'\]", re.M),
         "ORDER = list(AP.SCHOOL_IDS)"),
    ],
    'organize_tree.py': [
        (re.compile(r"^NAMES = \{'princeton': 'Princeton University'.*?'stanford': 'Stanford University'\}\n", re.S | re.M),
         "import school_config as _S  # noqa: E402  (the school charters)\nNAMES = _S.full_names()\n"),
    ],
}


def main(dry=False):
    plan = {}
    for f, edits in EDITS.items():
        s = (T / f).read_text(); new = s
        for rx, rep in edits:
            if rep.strip().splitlines()[0] in new:
                continue
            if not rx.search(new):
                sys.exit(f'{f}: anchor not found ({rx.pattern[:60]}...): nothing edited; update this script')
            new = rx.sub(lambda m: rep, new, count=1)
        if new != s:
            plan[f] = new
    for f, new in plan.items():
        print(('would edit ' if dry else 'edited ') + f)
        if not dry:
            (T / f).write_text(new)
    if not plan:
        print('already wired')


if __name__ == '__main__':
    main('--dry' in sys.argv)
