#!/usr/bin/env python3
"""Standard release gate and reversible activation; hosting adapters consume the same receipt."""
import argparse, contextlib, hashlib, json, os, shutil, socket, subprocess, sys, time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = [
    "portable/server.mjs",
    "portable/file-bucket.mjs",
    "portable/readiness.mjs",
    "lib/atlas-storage.mjs",
    "lib/chunked-graph.mjs",
]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(2**20), b""):
            h.update(b)
    return h.hexdigest()


def source_hash():
    names = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
        )
        .decode()
        .split("\0")
    )
    values = {
        n: sha(ROOT / n)
        for n in sorted(set(names))
        if n
        and (ROOT / n).is_file()
        and not n.startswith(
            ("deployment/validation", "deployment/upload-verification")
        )
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def fingerprint(bundle):
    config = json.loads((bundle / "config.json").read_text())
    manifest = bundle / "objects" / config["manifestSha256"]
    if sha(manifest) != config["manifestSha256"]:
        raise ValueError("Bundle manifest changed")
    m = json.loads(manifest.read_text())
    objects = {config["manifestSha256"]: manifest.stat().st_size}
    for entry in m["files"].values():
        for part in entry.get("chunks") or [entry]:
            objects[part["sha256"]] = part["size"]
    for key, size in objects.items():
        p = bundle / "objects" / key
        if p.stat().st_size != size or sha(p) != key:
            raise ValueError("Bundle asset changed: " + key)
    return {
        "config": config,
        "sourceHash": source_hash(),
        "runtime": {n: sha(ROOT / n) for n in RUNTIME},
    }


def run(args, env=None):
    subprocess.run(args, cwd=ROOT, env=env, check=True)


@contextlib.contextmanager
def preview(bundle):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = dict(os.environ, ATLAS_DATA_DIR=str(bundle), PORT=str(port))
    log = ROOT / "outputs/preview.log"
    log.parent.mkdir(exist_ok=True)
    with log.open("w") as output:
        process = subprocess.Popen(
            ["node", str(bundle / "code/portable/server.mjs")],
            cwd=ROOT,
            env=env,
            stdout=output,
            stderr=output,
        )
        try:
            origin = f"http://127.0.0.1:{port}"
            for _ in range(100):
                if process.poll() is not None:
                    raise ValueError("Preview failed; see outputs/preview.log")
                try:
                    with urlopen(origin + "/healthz", timeout=1) as r:
                        if r.status == 200:
                            break
                except OSError:
                    time.sleep(0.1)
            else:
                raise ValueError("Preview startup timed out")
            yield origin
        finally:
            process.terminate()
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def validate(bundle, projects):
    before = fingerprint(bundle)
    run(["npm", "test"])
    run(["npm", "run", "format:check"])
    run(["npm", "run", "build"])
    shutil.copytree(ROOT / "dist", bundle / "code", dirs_exist_ok=True)
    with preview(bundle) as origin:
        run(["node", "portable/smoke.mjs", origin, before["config"]["manifestSha256"]])
        env = dict(os.environ, ATLAS_BASE_URL=origin)
        args = [
            "npm",
            "run",
            "test:browser",
            "--",
            "--grep-invert",
            "synthetic fixture",
        ]
        for p in projects:
            args += ["--project", p]
        run(args, env)
    if fingerprint(bundle) != before:
        raise ValueError("Inputs changed during tests")
    receipt = {
        **before,
        "schema": 1,
        "passed": True,
        "browserProjects": projects,
        "testedAt": time.time(),
        "steps": ["unit", "format", "build", "smoke", "browser"],
    }
    (bundle / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                "verified": str(bundle),
                "manifestSha256": before["config"]["manifestSha256"],
            }
        )
    )


def check(bundle, require_current=True):
    receipt = json.loads((bundle / "verification.json").read_text())
    if receipt.get("passed") is not True or not {
        "unit",
        "format",
        "build",
        "smoke",
        "browser",
    } <= set(receipt.get("steps", [])):
        raise ValueError("Complete test receipt required")
    if receipt.get("browserProjects") is None or not receipt["browserProjects"]:
        raise ValueError("Browser tests required")
    for key, value in fingerprint(bundle).items():
        if key in ("sourceHash", "runtime") and not require_current:
            continue
        if receipt.get(key) != value:
            raise ValueError("Tested " + key + " changed; validate again")
    for name, expected in receipt.get("runtime", {}).items():
        if sha(bundle / "code" / name) != expected:
            raise ValueError("Packaged runtime changed")
    return receipt


def switch(root, target, restart, verify):
    root.mkdir(parents=True, exist_ok=True)
    current = root / "current"
    previous = current.resolve() if current.is_symlink() else None
    if current.exists() and not current.is_symlink():
        raise ValueError("current must be a release symlink")

    def point(path):
        temporary = root / "current.next"
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(path, target_is_directory=True)
        temporary.replace(current)

    point(target)
    try:
        restart()
        verify()
    except BaseException:
        if previous:
            point(previous)
            restart()
        else:
            current.unlink()
        raise
    if previous:
        (root / "previous.json").write_text(json.dumps({"path": str(previous)}) + "\n")


def activate(bundle, root, command, origin):
    receipt = check(bundle, require_current=False)
    if json.loads((bundle / "bundle.json").read_text()).get("mode") != "copy":
        raise ValueError(
            "Activation requires an independent copy, not a hardlinked preview"
        )
    switch(
        root,
        bundle,
        lambda: subprocess.run(command, check=True),
        lambda: run(
            ["node", "portable/smoke.mjs", origin, receipt["config"]["manifestSha256"]]
        ),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "command", choices=["release", "validate", "check", "activate", "rollback"]
    )
    p.add_argument("--bundle", type=Path)
    p.add_argument("--root", type=Path)
    p.add_argument(
        "--restart-command",
        help='JSON argument array, e.g. ["systemctl","restart","atlas"]',
    )
    p.add_argument("--origin")
    p.add_argument(
        "--projects", nargs="+", default=["desktop", "mobile", "firefox", "webkit"]
    )
    p.add_argument("--release")
    p.add_argument("--releases-dir", type=Path)
    p.add_argument("--stores", type=Path)
    p.add_argument("--edition")
    p.add_argument("--preview-only", action="store_true")
    a = p.parse_args()
    try:
        if a.command == "release":
            if not all(
                [a.bundle, a.release, a.releases_dir, a.stores, a.edition, a.origin]
            ):
                p.error(
                    "release requires --bundle, --release, --releases-dir, --stores, --edition and --origin"
                )
            run(
                [
                    sys.executable,
                    "scripts/release.py",
                    "prepare",
                    "--release",
                    a.release,
                    "--releases-dir",
                    str(a.releases_dir),
                    "--stores",
                    str(a.stores),
                ]
            )
            run(
                [
                    sys.executable,
                    "scripts/data-package.py",
                    "--tag",
                    a.edition,
                    "--origin",
                    a.origin,
                ]
            )
            run(["node", "scripts/prepare-atlas.mjs", "atlas", "r2"])
            pin = json.loads((ROOT / "lib/atlas-release.json").read_text())
            shutil.copyfile(
                ROOT / "atlas-storage/releases" / (pin["manifestSha256"] + ".json"),
                ROOT / "deployment/asset-manifest.json",
            )
            run(
                [
                    sys.executable,
                    "scripts/bundle-site.py",
                    "--release-dir",
                    str(a.releases_dir / a.release),
                    "--stores",
                    str(a.stores),
                    "--output",
                    str(a.bundle),
                    "--mode",
                    "link" if a.preview_only else "copy",
                    "--verify-papers",
                ]
            )
            validate(a.bundle.resolve(), a.projects)
        elif a.command in ("validate", "check"):
            if not a.bundle:
                p.error("--bundle required")
            if a.command == "validate":
                validate(a.bundle.resolve(), a.projects)
            else:
                print(json.dumps(check(a.bundle.resolve())))
        else:
            if not a.root or not a.restart_command or not a.origin:
                p.error("--root, --restart-command and --origin required")
            command = json.loads(a.restart_command)
            if (
                not isinstance(command, list)
                or not command
                or not all(isinstance(s, str) for s in command)
            ):
                raise ValueError("Restart command must be an argument array")
            bundle = (
                Path(json.loads((a.root / "previous.json").read_text())["path"])
                if a.command == "rollback"
                else a.bundle
            )
            if not bundle:
                p.error("--bundle required")
            activate(bundle.resolve(), a.root.resolve(), command, a.origin)
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        p.exit(1, str(e) + "\n")
