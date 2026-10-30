#!/bin/bash
# Install the repository's git hooks (once per clone; worktrees share them). The installed hook is a stub that runs
# tools/hooks/<hook> from the worktree that is committing, so a change to the hook ships with the code.
#   tools/install_hooks.sh            install (or refresh) pre-commit
#   tools/install_hooks.sh --remove   remove it
# Main-branch policy: git config atlas.mainCommits warn (default) | enforce   (docs/CONTRIBUTING.md)
set -euo pipefail
hooks="$(git rev-parse --git-common-dir)/hooks"
mkdir -p "$hooks"
if [ "${1:-}" = --remove ]; then rm -f "$hooks/pre-commit"; echo "removed $hooks/pre-commit"; exit 0; fi
if [ -e "$hooks/pre-commit" ] && ! grep -q 'cs-atlas hook stub' "$hooks/pre-commit"; then
  echo "$hooks/pre-commit exists and is not ours; move it aside first"; exit 1
fi
cat > "$hooks/pre-commit" <<'STUB'
#!/bin/bash
# cs-atlas hook stub (tools/install_hooks.sh): run this worktree's tools/hooks/pre-commit when it has one
h="$(git rev-parse --show-toplevel)/tools/hooks/pre-commit"
[ -x "$h" ] && exec "$h" "$@"
exit 0
STUB
chmod +x "$hooks/pre-commit"
echo "installed $hooks/pre-commit (main commits: $(git config --get atlas.mainCommits || echo warn))"
