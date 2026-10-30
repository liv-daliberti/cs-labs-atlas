# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/common.py (sha256 72c4919082175c98d440ef15e5dd8f49615de1ff9f510402af70f9e45cd35ad7); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Source preservation and deterministic local exports."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
from pathlib import Path
import csv, hashlib, json, re
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

ROOT = P.WORLD_ATLAS  # vendored: the data root (was Path(__file__).resolve().parents[1])
AS_OF = '2026-10-13'
RAW = ROOT / 'data/raw'


def stable_id(prefix, value):
    return prefix + '_' + hashlib.sha256(value.encode()).hexdigest()[:16]


def write_csv(path, rows, fields=None):
    rows = list(rows)
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def fetch(url, refresh=False):
    source_id = stable_id('src', url)
    path = RAW / (source_id + '.html')
    meta = RAW / (source_id + '.json')
    if not refresh and path.exists() and meta.exists():
        return path.read_text(), json.loads(meta.read_text())
    response = requests.get(url, timeout=35, headers={'User-Agent': 'HomogenizingScienceResearch/0.1 (public academic directory research)'})
    response.raise_for_status()
    try:
        content = response.content.decode('utf-8')
    except UnicodeDecodeError:
        response.encoding = response.apparent_encoding or response.encoding or 'utf-8'
        content = response.text
    metadata = dict(source_id=source_id, requested_url=url, final_url=response.url,
                    observed_on=AS_OF, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                    http_status=response.status_code, content_type=response.headers.get('Content-Type',''),
                    sha256=hashlib.sha256(content.encode()).hexdigest(), snapshot_path=str(path.relative_to(ROOT)))
    path.write_text(content, encoding='utf-8')
    meta.write_text(json.dumps(metadata, indent=2)+'\n')
    return content, metadata


def soup_for(url):
    text, meta = fetch(url)
    return BeautifulSoup(text, 'html.parser'), meta


def clean(value):
    return re.sub(r'\s+', ' ', value).strip()


def source_text(metadata):
    """Read preserved source content; PDF text is derived from the original bytes.

    Legacy HTML is decoded from unchanged bytes using its declared/detected charset.
    Requires Poppler's pdftotext for PDF sources. A PDF observation is never
    substituted with an HTML error or a separately edited text transcription.
    """
    return _source_text_cached(str(ROOT/metadata['snapshot_path']),metadata.get('sha256',''),metadata.get('content_type',''))


from functools import lru_cache
import subprocess

@lru_cache(maxsize=128)
def _source_text_cached(path,sha256,content_type):
    p=Path(path)
    if p.suffix.lower()=='.pdf' or 'application/pdf' in content_type:
        content=subprocess.run(['pdftotext',str(p),'-'],check=True,capture_output=True,text=True).stdout
        return clean(content)
    raw=p.read_bytes()
    is_html='html' in content_type.lower() or p.suffix.lower() in {'.html','.htm'}
    from source_decoding import decode_preserved_text
    content=decode_preserved_text(raw,content_type,p.suffix)
    return clean(BeautifulSoup(content,'html.parser').get_text(' ',strip=True)) if is_html else clean(content)
