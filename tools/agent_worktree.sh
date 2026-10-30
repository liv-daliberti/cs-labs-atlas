#!/bin/bash
# One worktree per agent or person (docs/CONTRIBUTING.md). Worktrees live next to the code checkout as code-<name>/
# (today: /n/fs/resemble/cs-atlas/work-<name>), each on its own branch <kind>/<name>.
#   tools/agent_worktree.sh new <name> [<kind>]   create the worktree and branch <kind>/<name> from main (kind: agent)
#   tools/agent_worktree.sh <name>                 the same (shorthand)
#   tools/agent_worktree.sh land <name>            rebase <kind>/<name> onto main, run the full tests, fast-forward main
#   tools/agent_worktree.sh rm <name>              remove the worktree (refuses with uncommitted changes) and its branch
#                                                  once merged (-f/--force: also an unmerged branch)
#   tools/agent_worktree.sh ls                     the worktrees
# Data never lives in a worktree: atlas_paths points every data slot at the main checkout's data (CS_ATLAS_CODE
# stays the main checkout); code paths that should come from the worktree are run from it (bin/atlas, tools/...).
set -euo pipefail
main_top=$(git -C "$(dirname "$0")" rev-parse --path-format=absolute --git-common-dir | sed 's#/\.git$##')
cmd=${1:-ls}
case "$cmd" in new|land|rm|ls) shift || true ;; *) cmd=new ;; esac
name=${1:-}; kind=${2:-agent}
dir="$(dirname "$main_top")/$(basename "$main_top")-${name}"
branch_of() { git -C "$main_top" worktree list --porcelain | awk -v d="$1" '$1=="worktree"{w=$2} $1=="branch" && w==d {sub("refs/heads/","",$2); print $2}'; }
need_name() { [ -n "$name" ] || { echo "usage: $0 $cmd <name>"; exit 2; }; [[ "$name" =~ ^[a-z0-9][a-z0-9._-]*$ ]] || { echo "name: lower-case letters, digits, . _ -"; exit 2; }; }
case "$cmd" in
  ls) git -C "$main_top" worktree list ;;
  new)
    need_name
    [ -e "$dir" ] && { echo "$dir exists"; exit 1; }
    git -C "$main_top" worktree add "$dir" -b "$kind/$name" main
    echo "worktree $dir on branch $kind/$name. Work and commit there; land with: $0 land $name" ;;
  land)
    need_name
    b=$(branch_of "$dir"); [ -n "$b" ] || { echo "no worktree at $dir"; exit 1; }
    git -C "$dir" diff --quiet && git -C "$dir" diff --cached --quiet || { echo "$dir has uncommitted changes"; exit 1; }
    git -C "$dir" rebase main
    (cd "$dir" && CS_ATLAS_VENDOR="$dir/vendor" bin/atlas test) || { echo "tests failed: main unchanged"; exit 1; }
    "$dir/bin/atlas" scan --staged >/dev/null 2>&1 || true
    git -C "$main_top" merge --ff-only "$b" || { echo "main moved or has local changes in these files: rebase again and retry"; exit 1; }
    echo "main fast-forwarded to $b ($(git -C "$main_top" rev-parse --short HEAD))" ;;
  rm)
    need_name
    b=$(branch_of "$dir"); force=${2:-}
    git -C "$main_top" worktree remove "$dir"
    if [ -n "$b" ]; then
      if [ "$force" = -f ] || [ "$force" = --force ]; then git -C "$main_top" branch -D "$b"; else git -C "$main_top" branch -d "$b"; fi
    fi ;;
esac
