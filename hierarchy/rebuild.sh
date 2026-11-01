#!/bin/bash
# The full rebuild, locally (the Slurm equivalent is hierarchy/rebuild-all.slurm, which runs this script):
#   snapshot    back up the current packages and record their counts (<SCRATCH>/pkg-before-<tag>/, outside the tree)
#   build       tools/pi_hierarchy.py for every school
#   ids         tools/atlas_ids.py: stable atlas ids (atl:p:/atl:w:/atl:l:) into the packages, the registry and the
#               cross-reference table (hierarchy/ids/; docs/IDS.md); always over every released school
#   copies      tools/lab_paper_copies.py (copies.json from the full-text stores, with access-review causes)
#   ledger      fulltext-push/unavailable_ledger.py (collector Python): why each lab paper without a local copy has none
#               -> hierarchy/<school>/unavailable.jsonl.gz + unavailable-summary.json, reasons onto copies.json
#               (docs/UNAVAILABLE.md); for $SCHOOLS plus every charter with status "onboarding"
#   reader      tools/reader_export.py: host-or-link decision per confirmed copy by licence -> hierarchy/reader/ (released as reader/)
#   audits      student audit, chain audit (open items), link diagnosis, chain audit
#   evidence    tools/evidence_check.py: every claim carries its evidence -> hierarchy/EVIDENCE-CHECK.md; a failure holds the release
#   tests       pytest tests/
#   regression  tools/build_regression.py check against the snapshot -> hierarchy/BUILD-REGRESSION.md (+ .json)
#   validate    tools/validate.py: every package and shared derived file against schemas/ (docs/DATA-DICTIONARY.md)
#               -> hierarchy/VALIDATION.json; a violation fails the stage and holds the release
#   release     tools/make_release.py -> /n/fs/resemble/homogenizing-science/releases/<date>[.N]/ and releases/latest; only when
#               every earlier stage passed and the regression flagged nothing (ALLOW_SWINGS=1 releases anyway)
#   tree        tools/organize_tree.py from releases/latest -> /n/fs/resemble/homogenizing-science/schools/
#   housekeeping tools/scratch.py clean --apply: scratch and old equivalence reports older than 14 days (never packages)
# Code: the tools run from a snapshot of one commit (CS_ATLAS_SNAPSHOT_COMMIT, default HEAD now), data from the main checkout.
# usage: hierarchy/rebuild.sh                       (all stages, all schools; run under nohup or in tmux, ~1 h)
#        STAGES="build audits" SCHOOLS="mit" hierarchy/rebuild.sh
#        TAG=<name> sets the snapshot name (default local-<timestamp>); BEFORE=<dir> compares against another snapshot
# Exit status: 0 all good, 1 a stage failed, 2 regression swings blocked the release.
set -u -o pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_WORK" || exit 1   # the data: always the main checkout
if [ -z "${CS_ATLAS_SNAPSHOT:-}" ]; then  # run from a code snapshot of one commit (docs/CONTRIBUTING.md, tools/job_code_snapshot.sh)
  . "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
  bash "$CS_ATLAS_SNAPSHOT/hierarchy/rebuild.sh" "$@"; rc=$?; snapshot_remove; exit $rc
fi
PY="nice -n10 $CS_ATLAS_PY -u"  # the project interpreter (env/atlas; tools/atlas_paths.py PY)
SCHOOLS=${SCHOOLS:-$CS_ATLAS_SCHOOLS}
STAGES=${STAGES:-snapshot build ids copies ledger reader audits evidence tests regression validate release tree housekeeping}
TAG=${TAG:-local-$(date +%Y%m%d-%H%M%S)}
BEFORE=${BEFORE:-$CS_ATLAS_SCRATCH/pkg-before-$TAG}   # scratch, outside the tree (tools/scratch.py)
has() { case " $STAGES " in *" $1 "*) return 0 ;; esac; return 1; }
fail=0; swings=0
echo "== rebuild $TAG stages: $STAGES schools: $SCHOOLS code: $(git rev-parse --short HEAD 2>/dev/null)$(git diff --quiet HEAD -- tools 2>/dev/null || echo '+dirty') $(date +%T)"

if has snapshot; then
  echo "== snapshot $(date +%T)"
  for s in $SCHOOLS; do
    mkdir -p "$BEFORE/$s" && $CS_ATLAS_PY -c "import sys, shutil; sys.path.insert(0, '$CS_ATLAS_TOOLS'); import atlas_paths as P; [shutil.copy2(P.data(f, '$s'), '$BEFORE/$s/' + f) for f in ('pis.json', 'students.json', 'report.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz') if P.data(f, '$s').exists()]" 2>/dev/null
  done
  $PY $CS_ATLAS_TOOLS/build_regression.py snapshot --out "$BEFORE/counts.json" || fail=1
fi
if has build; then
  $CS_ATLAS_PY -c "import sys; sys.path.insert(0, '$CS_ATLAS_TOOLS'); import atlas_paths as P; [P.data('link-diagnosis.json', s).unlink(missing_ok=True) for s in P.SCHOOL_IDS]"  # stale diagnoses would hide open items from the re-diagnosis
  for s in $SCHOOLS; do echo "== $s $(date +%T)"; $PY $CS_ATLAS_TOOLS/pi_hierarchy.py $s || { echo "FAILED $s"; fail=1; }; done
fi
if has ids; then
  # after the build, before every consumer (2026-10-29): ids never change once issued (hierarchy/ids/registry.sqlite)
  echo "== ids $(date +%T)"; $PY $CS_ATLAS_TOOLS/atlas_ids.py || { echo "FAILED ids"; fail=1; }
fi
if has copies; then
  # before the audits (2026-10-29): the chain audit's copies check reads copies.json, with the stores' access-review causes
  echo "== copies $(date +%T)"; $PY $CS_ATLAS_TOOLS/lab_paper_copies.py $SCHOOLS || fail=1
fi
if has ledger; then
  # after the copies, before the audits and the evidence check (2026-10-30, docs/UNAVAILABLE.md, R-AUD-10): the
  # unavailability ledger, run with the collectors' interpreter; it also writes the reasons onto copies.json
  # (lab_paper_copies.attach_ledger). Onboarding schools (school charters) get their ledger before their first release.
  onb=$($CS_ATLAS_PY -c 'import sys; sys.path.insert(0, __import__("os").environ["CS_ATLAS_TOOLS"]); import school_config as c; print(" ".join(c.onboarding()))') || { echo "FAILED ledger: onboarding schools"; fail=1; onb=""; }
  ledger_schools=$(echo $SCHOOLS $onb | tr ' ' '\n' | awk 'NF && !seen[$0]++' | tr '\n' ' ')
  echo "== ledger $(date +%T) schools: $ledger_schools"
  nice -n10 $CS_ATLAS_COLLECTOR_PY -I -u "$CS_ATLAS_FULLTEXT_PUSH/unavailable_ledger.py" $ledger_schools || { echo "FAILED ledger"; fail=1; }
fi
if has reader; then
  # (2026-11-01, owner) which confirmed copies the site may host (licence allows redistribution) and a source link for the rest;
  # reads the catalogs read-only -> hierarchy/reader/ (README.md there), copied into the release as reader/
  echo "== reader $(date +%T)"
  $PY $CS_ATLAS_TOOLS/reader_export.py --site-local-papers "$CS_ATLAS_SITE/atlas/data/local-papers.json" || { echo "FAILED reader"; fail=1; }
fi
if has audits; then
  echo "== student audit $(date +%T)"; $PY $CS_ATLAS_TOOLS/student_audit.py $CS_ATLAS_SCHOOLS > /dev/null || fail=1
  echo "== chain audit (open items) $(date +%T)"; $PY $CS_ATLAS_TOOLS/chain_audit.py > /dev/null || fail=1
  echo "== link diagnosis $(date +%T)"; $PY $CS_ATLAS_TOOLS/link_diagnosis.py $CS_ATLAS_SCHOOLS || true
  echo "== chain audit $(date +%T)"; $PY $CS_ATLAS_TOOLS/chain_audit.py || fail=1
fi
if has evidence; then
  # the build-time evidence check (2026-10-29): every period, listing, student relation, lab paper and byline link carries
  # its evidence (url, sha256, quote; school basis; appointment), or is whitelisted with a count in docs/evidence-whitelist.json
  echo "== evidence check $(date +%T)"; $PY $CS_ATLAS_TOOLS/evidence_check.py || { echo "FAILED evidence check"; fail=1; }
fi
if has tests; then
  echo "== tests $(date +%T)"; $PY -m pytest "$CS_ATLAS_TESTS" -q -p no:cacheprovider 2>&1 | tail -3; [ "${PIPESTATUS[0]}" = 0 ] || { echo "FAILED tests"; fail=1; }
fi
if has regression; then
  echo "== regression $(date +%T)"
  $PY $CS_ATLAS_TOOLS/build_regression.py check --before "$BEFORE/counts.json"; rc=$?
  [ $rc = 2 ] && swings=1
  [ $rc = 1 ] && fail=1
fi
if has validate; then
  # (2026-10-31, ROADMAP item 9) the packages and the shared derived files against their schemas
  echo "== validate $(date +%T)"; $PY $CS_ATLAS_TOOLS/validate.py $SCHOOLS --shared --json "$($CS_ATLAS_PY -c 'import sys; sys.path.insert(0, __import__("os").environ["CS_ATLAS_TOOLS"]); import atlas_paths as P; print(P.data("VALIDATION.json"))')" || { echo "FAILED validate"; fail=1; }
fi
if has release; then
  if [ $fail != 0 ]; then echo "== release skipped: a stage failed"
  elif [ $swings != 0 ] && [ "${ALLOW_SWINGS:-0}" != 1 ]; then echo "== release skipped: regression swings (hierarchy/BUILD-REGRESSION.md); ALLOW_SWINGS=1 releases anyway"
  else
    echo "== release $(date +%T)"; $PY $CS_ATLAS_TOOLS/make_release.py --before "$BEFORE/counts.json" $([ "${ALLOW_SWINGS:-0}" = 1 ] && echo --allow-swings) || fail=1
  fi
fi
if has tree && [ $fail = 0 ]; then
  echo "== tree $(date +%T)"; nice -n10 ionice -c3 $CS_ATLAS_PY -u $CS_ATLAS_TOOLS/organize_tree.py $SCHOOLS || fail=1
fi
if has housekeeping; then  # ROADMAP item 13: scratch older than 14 days, old equivalence reports; never touches packages
  echo "== housekeeping $(date +%T)"; $PY $CS_ATLAS_TOOLS/scratch.py clean --apply || echo "housekeeping failed (not fatal)"
fi
echo "== done all $(date +%T) fail=$fail swings=$swings"
[ $fail != 0 ] && exit 1
[ $swings != 0 ] && exit 2
exit 0
