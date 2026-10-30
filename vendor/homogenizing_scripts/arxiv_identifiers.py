# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/arxiv_identifiers.py (sha256 e62ade4b27c9643b498bbb6191f0040e43b1bc0dcac60339c7683c6a5c52e010); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Canonical arXiv DOI mapping documented at https://info.arxiv.org/help/doi.html."""
import re
from urllib.parse import urlsplit

def arxiv_doi(url):
    parsed=urlsplit(url)
    if parsed.scheme not in {'http','https'} or parsed.hostname not in {'arxiv.org','www.arxiv.org','export.arxiv.org'} or parsed.query or parsed.fragment:
        return ''
    match=re.fullmatch(r'/(?:abs|pdf)/(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v[1-9]\d*)?(?:\.pdf)?',parsed.path)
    if not match:return ''
    identifier=match.group(1)
    stamp=identifier.split('/')[-1][:4]
    if not 1<=int(stamp[2:4])<=12:return ''
    return '10.48550/arxiv.'+identifier.lower()

