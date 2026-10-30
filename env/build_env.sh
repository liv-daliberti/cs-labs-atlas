#!/bin/bash
# Build the project environment (env/atlas) from the committed lock. conda-forge only; the package cache goes to local
# /tmp (not NFS). Lock method: conda's explicit spec (`conda list --explicit --md5`): every package by URL and md5, so a
# rebuild installs exactly the same files without solving.
#   env/build_env.sh             create $CS_ATLAS_ENV/atlas from env/conda-linux-64.lock (exact; no solve)
#   env/build_env.sh --solve     solve env/environment.yml afresh, then rewrite the lock from the result (commit it)
# PREFIX=<dir> builds elsewhere (a test build). An existing prefix is never edited in place: move it aside first.
# Afterwards the repo is installed editable (--no-deps), so `atlas` is on the env's bin/ (see docs/ENVIRONMENT.md).
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd); REPO=$(dirname "$HERE")
. "$REPO/paths.sh"
CONDA=${CONDA:-/n/fs/cssoftware/anaconda3/2026.07/bin/conda}   # `module load anaconda3/2026.07`
PREFIX=${PREFIX:-$CS_ATLAS_ENV/atlas}
INSTALL_FROM=${INSTALL_FROM:-$CS_ATLAS_CODE}                   # the checkout `atlas` runs (the main one by default)
export CONDA_PKGS_DIRS=${CONDA_PKGS_DIRS:-/tmp/$USER-conda-pkgs}
mkdir -p "$CONDA_PKGS_DIRS"
if [ -e "$PREFIX" ]; then echo "$PREFIX exists; move it aside first (an env is never edited in place)"; exit 1; fi
if [ "${1:-}" = --solve ]; then
  SPECS=$(awk '/^dependencies:/{d=1;next} d && /^  - /{print $2}' "$HERE/environment.yml")
  # --override-channels: the system condarc lists defaults, whose terms of service a batch job cannot accept
  # shellcheck disable=SC2086
  nice "$CONDA" create --yes --quiet --override-channels -c conda-forge -p "$PREFIX" $SPECS
  { echo "# Generated from env/environment.yml on $(date -u +%F) (conda-forge, linux-64); do not edit. Rebuild exactly: env/build_env.sh"
    echo "# (= conda create -p <prefix> --file env/conda-linux-64.lock). Re-solve after editing environment.yml: env/build_env.sh --solve"
    "$CONDA" list -p "$PREFIX" --explicit --md5; } > "$HERE/conda-linux-64.lock"
else
  nice "$CONDA" create --yes --quiet --override-channels -c conda-forge -p "$PREFIX" --file "$HERE/conda-linux-64.lock"
fi
"$PREFIX/bin/python" -m pip install --no-deps --no-build-isolation --no-cache-dir -q -e "$INSTALL_FROM"
"$PREFIX/bin/python" -c "import requests, bs4, lxml, protego, rapidfuzz, pymupdf, numpy, huggingface_hub, pytest, tomllib; print('env ok')"
"$PREFIX/bin/pdftotext" -v 2>&1 | head -1
