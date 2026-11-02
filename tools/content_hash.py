"""Content hashes that ignore the clock (ROADMAP #22, 2026-11-01).

Some generated files carry a deliberate timestamp (the build time of a package, the ledger's `built_at` and each record's `checked_at`, a release's `created`). The
stamp is kept - it says when the file was made - but it is not content: two runs on unchanged inputs must be equal without it. `content_sha256(path)` is the sha256 of
the file's decoded data with the volatile fields removed, serialised canonically; make_release records it beside the byte hash, and tools/package_diff.py
ignores the same fields (VOLATILE) by default. A file not named here is hashed whole.
"""
import gzip, hashlib, json
from pathlib import Path

# file name -> dotted paths dropped from a JSON document, or from every row of a JSON-lines file
VOLATILE = {
    'report.json': ['builtAt', 'provenance.at'],
    'unavailable-summary.json': ['built_at', 'inputs.copies_json', 'inputs.lab_papers'],
    'unavailable.jsonl.gz': ['checked_at'],
    'copies.json': ['summary.counted_at', 'summary.ledger_built_at'],
    'MANIFEST.json': ['created'],
    'BUILD-REGRESSION.json': ['before.at', 'after.at'],
    'EVIDENCE-CHECK.json': ['at'],
    'chain-audit.json': ['at'],
    'SUMMARY.json': ['built_at'],
}


def drop(d, path):
    keys = path.split('.')
    for k in keys[:-1]:
        if not isinstance(d, dict) or k not in d:
            return False
        d = d[k]
    return isinstance(d, dict) and d.pop(keys[-1], None) is not None


def load(path):
    p = Path(path)
    b = p.read_bytes()
    if p.suffix == '.gz':
        b = gzip.decompress(b)
    name = p.name[:-3] if p.suffix == '.gz' else p.name
    if name.endswith('.jsonl'):
        return 'jsonl', [json.loads(x) for x in b.decode().split('\n') if x.strip()]
    if name.endswith('.json'):
        return 'json', json.loads(b)
    return 'bytes', b


def content_sha256(path):
    """sha256 of the decoded content without the volatile fields, or of the raw bytes for a file that is not JSON."""
    kind, data = load(path)
    specs = VOLATILE.get(Path(path).name, [])
    if kind == 'bytes':
        return hashlib.sha256(data).hexdigest()
    for spec in specs:
        for row in (data if kind == 'jsonl' else [data]):
            drop(row, spec)
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
