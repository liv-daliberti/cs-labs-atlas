"""Allowed hosts for open PDFs: the fulltext-push rule, imported read-only from the CMU tools (s2_key_lookup.ok_pdf:
not doi.org / arxiv.org / ACM DL / OpenReview / AAAI / IACR ePrint / SSRN / OSF / CORE; core_search.usable: also not
the publisher hosts IEEE, Springer, Elsevier, Scopus, Wiley, SAGE, ... nor ORCID / Princeton DataSpace)."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(P.vendor('cmu_tools')))  # vendored code
import s2_key_lookup as _s2k  # noqa: E402
import core_search as _cs  # noqa: E402


def allowed(url):
    return _s2k.ok_pdf(url) and _cs.usable(url)
