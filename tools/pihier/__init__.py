"""The PI-hierarchy build, by stage (ROADMAP item 8, 2026-10-30): tools/pi_hierarchy.py is its entry point and re-exports
every name, so `tools/pi_hierarchy.py <school>` and `from pi_hierarchy import ...` work as before.

  common     the charter tables (INST, AFF, DBLP, SCHOOL_LOOSE, OWN_UNITS), the date, readers, work keys, evidence order
  names      name readings and matchers (toks, Name, nick_ok, byline_name, the given-name guard)
  census     the build's inputs; the census rows merged into PIs; each PI's lab (R-HIER-01, R-HIER-02)
  periods    appointment periods and dated listings (R-PAP-01, R-PAP-02, R-PAP-03, R-PAP-13)
  students   the lab's students: gathering, merges, corrections, weak relations (R-HIER-03, R-HIER-04, R-STU-*)
  identity   the PI's identity anchors and the sweep authorships matched to PIs (R-PAP-04 .. R-PAP-07, R-PAP-14)
  papers     which matched works are lab papers (R-PAP-08 .. R-PAP-26)
  links      student-paper links (R-LNK-*)
  build      the stages in order, and the package files written (Ctx carries the state between stages)
"""
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent.parent) not in sys.path:  # tools/: atlas_paths, provenance, school_config
    sys.path.append(str(Path(__file__).resolve().parent.parent))
