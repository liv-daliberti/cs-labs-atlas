"""Upload one release to the private Hugging Face dataset and verify it file by file (2026-10-29).

  <release dir>/ -> hamlab-princeton/homogenizing-science-research (repo_type dataset) under releases/<id>/
  Every MANIFEST file is checked on the Hub at the upload commit: size, and the LFS sha256 (or, for a small file stored
  in git, its git blob sha1) against the local file. The result, with the Hub commit, goes into
  <release>/HF-UPLOAD.json (tools/make_release.py add-note).

Needs HF_TOKEN in the environment (set -a; . ~/.config/cs-atlas/hf.env; set +a) and HF_HOME set explicitly (never under
/n/fs/similarity); the token is never printed.
usage: hf_upload_release.py [<release id>|latest] [--repo REPO] [--dry-run]
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)

REPO = 'hamlab-princeton/homogenizing-science-research'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def git_blob_sha1(p):
    b = Path(p).read_bytes()
    return hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('release', nargs='?', default='latest')
    ap.add_argument('--repo', default=REPO)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    hf_home = os.environ.get('HF_HOME', '')
    if not hf_home or hf_home.startswith('/n/fs/similarity'):
        raise SystemExit(f'set HF_HOME explicitly (e.g. {P.HF_HOME}); never under /n/fs/similarity')
    if not os.environ.get('HF_TOKEN'):
        raise SystemExit('HF_TOKEN is not set: set -a; . ~/.config/cs-atlas/hf.env; set +a')
    d = (P.RELEASES / a.release).resolve()
    man = json.loads((d / 'MANIFEST.json').read_text())
    rid = man['release']
    if (d / 'HF-UPLOAD.json').exists():
        raise SystemExit(f'{rid} already has HF-UPLOAD.json')
    local = {f: e for f, e in man['files'].items()}
    local['MANIFEST.json'] = dict(bytes=(d / 'MANIFEST.json').stat().st_size, sha256=sha256(d / 'MANIFEST.json'))
    if (d / 'SITE-HANDOFF.md').exists():
        local['SITE-HANDOFF.md'] = dict(bytes=(d / 'SITE-HANDOFF.md').stat().st_size, sha256=sha256(d / 'SITE-HANDOFF.md'))
    for f, e in local.items():  # the release on disk still matches its manifest
        if (d / f).stat().st_size != e['bytes'] or sha256(d / f) != e['sha256']:
            raise SystemExit(f'{rid}/{f} differs from its MANIFEST entry')
    prefix = f'releases/{rid}'
    if a.dry_run:
        print(json.dumps(dict(release=rid, repo=a.repo, path=prefix, files=len(local), bytes=sum(e['bytes'] for e in local.values()))))
        return
    from huggingface_hub import HfApi
    api = HfApi()
    existing = [f for f in api.list_repo_files(a.repo, repo_type='dataset') if f.startswith(prefix + '/')]
    if existing:
        raise SystemExit(f'{a.repo} already holds {len(existing)} files under {prefix}/; releases are never overwritten')
    info = api.upload_folder(repo_id=a.repo, repo_type='dataset', folder_path=str(d), path_in_repo=prefix,
                             allow_patterns=sorted(local), commit_message=f'Add CS Labs Atlas release {rid}',
                             commit_description=f"code {man['code']['commit']}; {len(local)} files; MANIFEST sha256 {local['MANIFEST.json']['sha256']}")
    commit = info.oid
    remote = {}
    paths = [f'{prefix}/{f}' for f in sorted(local)]
    for i in range(0, len(paths), 50):
        for x in api.get_paths_info(a.repo, paths[i:i + 50], repo_type='dataset', revision=commit, expand=True):
            remote[x.path[len(prefix) + 1:]] = x
    checked, bad = [], []
    for f, e in sorted(local.items()):
        x = remote.get(f)
        if x is None:
            bad.append(dict(file=f, problem='missing on the Hub')); continue
        if x.size != e['bytes']:
            bad.append(dict(file=f, problem='size', local=e['bytes'], hub=x.size)); continue
        if x.lfs is not None:
            ok, how = x.lfs.sha256 == e['sha256'], 'lfs_sha256'
        else:
            ok, how = x.blob_id == git_blob_sha1(d / f), 'git_blob_sha1'
        (checked if ok else bad).append(dict(file=f, check=how) if ok else dict(file=f, problem=how))
    rec = dict(repo=a.repo, repo_type='dataset', path=prefix, commit=commit, commit_url=info.commit_url,
               uploaded=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), files=len(local),
               bytes=sum(e['bytes'] for e in local.values()), verified=len(checked),
               verified_by={k: sum(1 for c in checked if c['check'] == k) for k in ('lfs_sha256', 'git_blob_sha1')},
               mismatches=bad, manifest_sha256=local['MANIFEST.json']['sha256'])
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as t:
        json.dump(rec, t, indent=1); tmp = t.name
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'make_release.py'), 'add-note', rid, 'HF-UPLOAD.json', tmp], check=True)
    os.unlink(tmp)
    print(json.dumps({k: v for k, v in rec.items() if k != 'mismatches'} | dict(mismatches=len(bad))))
    if bad:
        print(json.dumps(bad[:20]))
        sys.exit(1)


if __name__ == '__main__':
    main()
