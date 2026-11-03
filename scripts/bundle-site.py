#!/usr/bin/env python3
"""Create a complete, movable Node/Docker publication bundle; no hosting API.

Input: prepared atlas assets, the exact frozen reader release, and paper stores.
Every output object is checked by SHA-256 before the server serves it. Build-time
verification hashes site assets and checks paper lengths; --verify-papers also
hashes all paper bytes up front (potentially many GB).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from release_inputs import verify_release

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(2**20), b""):
            result.update(block)
    return result.hexdigest()


def contained(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Object source escapes its root")
    return path


def build(release, stores, output, mode="copy", verify_papers=False):
    pin = read(ROOT / "deployment/release.json")
    manifest = verify_release(release, pin["manifestSha256"], pin["release"])
    if manifest.get("evidence_check") is not True:
        raise ValueError("Research evidence gate did not pass")
    asset_manifest = ROOT / "deployment/asset-manifest.json"
    assets = read(asset_manifest)
    objects = {}

    def admit(sha, source, size, verify=True):
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("Invalid object digest")
        if source.stat().st_size != size or (verify and digest(source) != sha):
            raise ValueError("Object changed: " + str(source))
        objects.setdefault(sha, (source, size))

    for name, entry in assets["files"].items():
        if name.startswith("papers/"):
            raise ValueError("Paper files must use the frozen reader allowlist")
        source = contained(ROOT / "atlas", name)
        if source.stat().st_size != entry["size"] or digest(source) != entry["sha256"]:
            raise ValueError("Rebuild the asset manifest before bundling: " + name)
        if entry.get("chunks"):
            for chunk in entry["chunks"]:
                admit(
                    chunk["sha256"],
                    ROOT / "atlas-storage/chunks" / chunk["sha256"],
                    chunk["size"],
                )
        else:
            admit(entry["sha256"], source, entry["size"], verify=False)

    compact = read(ROOT / "atlas/data/reader-objects.json")
    if compact["release"] != pin["release"]:
        raise ValueError("Reader index differs from the release pin")
    with (release / "reader/hosted-files.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if compact["files"] != {row["sha256"]: int(row["bytes"]) for row in rows}:
        raise ValueError("Reader allowlist differs from frozen release")
    paper_checks = []
    for row in rows:
        sha, size = row["sha256"], int(row["bytes"])
        if compact.get("chunks", {}).get(sha):
            for chunk in compact["chunks"][sha]:
                admit(
                    chunk["sha256"],
                    ROOT / "atlas-storage/chunks" / chunk["sha256"],
                    chunk["size"],
                )
        else:
            source = contained(stores, row["school"] + "/" + row["path"])
            admit(sha, source, size, verify=False)
            if verify_papers:
                paper_checks.append((sha, source, size))
    if paper_checks:
        print(
            json.dumps({"verifyingPaperObjects": len(paper_checks), "workers": 8}),
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [
                pool.submit(admit, sha, source, size, True)
                for sha, source, size in paper_checks
            ]
            for count, future in enumerate(as_completed(futures), 1):
                future.result()
                if count % 500 == 0:
                    print(
                        json.dumps(
                            {"verifiedPaperObjects": count, "total": len(futures)}
                        ),
                        flush=True,
                    )
    manifest_sha = digest(asset_manifest)
    admit(manifest_sha, asset_manifest, asset_manifest.stat().st_size)
    if output.exists():
        raise ValueError("Bundle already exists; use a new output directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".bundle-", dir=output.parent))
    try:
        (stage / "objects").mkdir()
        for index, (sha, (source, size)) in enumerate(objects.items(), 1):
            destination = stage / "objects" / sha
            if mode == "link":
                os.link(source, destination)
            else:
                shutil.copyfile(source, destination)
            if index % 1000 == 0:
                print(json.dumps({"bundled": index, "total": len(objects)}), flush=True)
        config = {
            "schema": 1,
            "release": pin["release"],
            "manifestSha256": manifest_sha,
        }
        (stage / "config.json").write_text(json.dumps(config, indent=2) + "\n")
        receipt = dict(
            config,
            objects=len(objects),
            bytes=sum(size for _, size in objects.values()),
            hostedFiles=len(rows),
            mode=mode,
            paperHashesCheckedAtBuild=verify_papers,
            runtimeChecksumVerification=True,
        )
        (stage / "bundle.json").write_text(json.dumps(receipt, indent=2) + "\n")
        stage.rename(output)
        print(json.dumps(dict(receipt, directory=str(output))))
        return receipt
    except BaseException:
        shutil.rmtree(stage)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--stores", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=["copy", "link"],
        default="copy",
        help="link is for same-filesystem previews; copy is portable",
    )
    parser.add_argument("--verify-papers", action="store_true")
    args = parser.parse_args()
    try:
        build(
            args.release_dir.resolve(),
            args.stores.resolve(),
            args.output.resolve(),
            args.mode,
            args.verify_papers,
        )
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Bundle failed: {error}\n")


if __name__ == "__main__":
    main()
