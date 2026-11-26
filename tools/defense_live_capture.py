"""Bounded, live-only recapture of exact Georgia Tech defense URLs.

Uses school_web's stored robots/refusal policy and redirect-safe requests. Retains
the original HTML bytes needed to verify defense evidence, rather than only its
parsed text. The caller supplies a private school-capture overlay and the same
host lock used by defense_crawl. No archive fallback, discovery, or retries.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import re
import time
import zlib
from pathlib import Path

_spec = importlib.util.spec_from_file_location('school_web', Path(__file__).with_name('school_web.py'))
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

HOST = 'hg.gatech.edu'
EVENT = re.compile(r'https://hg\.gatech\.edu/node/\d+\Z')
NAMED_AI = re.compile(r'(?im)^\s*user-agent:\s*(?:ClaudeBot|Claude-Web|anthropic-ai|Claude)\s*$')


def manifest_urls(manifest, maximum):
    if manifest.get('school') != 'gatech' or manifest.get('host') != HOST:
        raise ValueError('manifest must name gatech and hg.gatech.edu')
    urls = manifest.get('urls')
    if not isinstance(urls, list) or not urls or any(not isinstance(u, str) or not EVENT.fullmatch(u) for u in urls):
        raise ValueError('only exact HTTPS Mercury node URLs are permitted')
    if len(set(urls)) != len(urls):
        raise ValueError('manifest URLs must be unique')
    if not 1 <= maximum <= 100 or len(urls) > maximum or manifest.get('max_pages') != maximum:
        raise ValueError('manifest exceeds its explicit page budget (hard limit 100)')
    return urls


def save(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    tmp.replace(path)


def capture(manifest, out, lock, maximum):
    urls = manifest_urls(manifest, maximum)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'sources').mkdir(exist_ok=True)
    receipt = {'school': 'gatech', 'host': HOST, 'urls_planned': len(urls),
               'network_policy': 'live only; no redirects, archive, or refusal retries', 'pages': []}
    Path(lock).parent.mkdir(parents=True, exist_ok=True)
    with open(lock, 'a') as locked:
        try:
            fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            receipt['stop'] = 'existing defense collector owns host lock'
            save(out / 'capture-receipt.json', receipt)
            return receipt
        c = W.con('gatech')
        try:
            # Loading the seeded cache restores historical refusal receipts.
            if HOST in W._blocked:
                receipt['stop'] = 'host has a prior cached refusal; no requests'
                save(out / 'capture-receipt.json', receipt)
                return receipt
            status, body = W.robots_row(c, HOST)
            receipt['robots_status'] = status
            receipt['robots_sha256'] = hashlib.sha256(body.encode()).hexdigest()
            allowed, ai, delay = W.robots_decision(status, body, urls[0])
            if not allowed or not ai or NAMED_AI.search(body):
                receipt['stop'] = 'robots unavailable, disallowed, redirected, or explicitly names a restricted agent'
                save(out / 'capture-receipt.json', receipt)
                return receipt
            # Includes the robots request in the same conservative host interval.
            last = time.monotonic()
            for url in urls:
                time.sleep(max(0, last + max(3.0, delay) - time.monotonic()))
                result = W.live(c, url)
                last = time.monotonic()
                if result is None:
                    receipt['stop'] = 'host or exact path refused by stored policy'
                    break
                status, sha, _ = result
                row = c.execute('select fetched_at,status,sha256,content_type,raw_zlib from live where url=?', (url,)).fetchone()
                entry = {'url': url, 'status': status, 'sha256': sha}
                if row:
                    fetched, stored_status, stored_sha, ct, compressed = row
                    entry.update(fetched_at=fetched, content_type=ct)
                    raw = zlib.decompress(compressed) if compressed else b''
                    if stored_status != status or stored_sha != sha or (raw and hashlib.sha256(raw).hexdigest() != sha):
                        raise ValueError('capture bytes do not match the stored receipt')
                    if status == 200 and (b'<html' in raw[:4000].lower() or b'<!doctype html' in raw[:200].lower()):
                        source = out / 'sources' / f'{sha}.html'
                        source.write_bytes(raw)
                        entry['raw_file'] = str(source)
                    elif status == 200:
                        entry['held'] = 'not an HTML event page'
                receipt['pages'].append(entry)
                save(out / 'capture-receipt.json', receipt)
                print(json.dumps(entry), flush=True)
                if status in (401, 403, 429, 999):
                    receipt['stop'] = f'host refusal HTTP {status}; remaining URLs not requested'
                    break
            receipt['remaining'] = len(urls) - len(receipt['pages'])
            save(out / 'capture-receipt.json', receipt)
            return receipt
        finally:
            c.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--lock', type=Path, required=True)
    ap.add_argument('--max', type=int, required=True)
    args = ap.parse_args()
    receipt = capture(json.loads(args.manifest.read_text()), args.out, args.lock, args.max)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'pages'}), flush=True)


if __name__ == '__main__':
    main()
