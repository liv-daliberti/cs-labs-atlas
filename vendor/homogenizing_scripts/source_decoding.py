# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/source_decoding.py (sha256 f4532e9cc6ea9f538da66aafca52674c0e419242ebba78cf055bb4241ca18a08); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Decode preserved evidence without replacing undecodable source bytes."""
import re
from bs4 import BeautifulSoup


def decode_preserved_text(raw, content_type='', suffix=''):
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        if 'html' not in content_type.lower() and suffix.lower() not in {'.html', '.htm'}:
            raise
        declared = re.search(r'charset\s*=\s*[\"\']?([^;\s\"\']+)', content_type, re.I)
        soup = BeautifulSoup(raw, 'html.parser', from_encoding=declared.group(1) if declared else None)
        if soup.contains_replacement_characters or not soup.original_encoding:
            raise UnicodeError('Lossy HTML charset decoding')
        # The parser supplies the detected encoding; strict decoding retains
        # the original markup, without serializing a modified DOM.
        return raw.decode(soup.original_encoding)
