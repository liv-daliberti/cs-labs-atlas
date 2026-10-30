#!/bin/bash
# The full rebuild, locally (the Slurm equivalent is hierarchy/rebuild-all.slurm, which runs this script):
#   snapshot    back up the current packages and record their counts (hierarchy/logs/pkg-before-<tag>/)
#   build       tools/pi_hierarchy.py for every school
#   ids         tools/atlas_ids.py: stable atlas ids (atl:p:/atl:w:/atl:l:) into the packages, the registry and the
#               cross-reference table (hierarchy/ids/; docs/IDS.md); always over every released school
#   copies      tools/lab_paper_copies.py (copies.json from the full-text stores, with access-review causes)
#   ledger      fulltext-push/unavailable_ledger.py (collector Python): why each lab paper without a local copy has none
#               -> hierarchy/<school>/unavailable.jsonl.gz + unavailable-summary.json, reasons onto copies.json
#               (docs/UNAVAILABLE.md); for $SCHOOLS plus every charter with status "onboarding"
#   audits      student audit, chain audit (open items), link diagnosis, chain audit
#   evidence    tools/evidence_check.py: every claim carries its evidence -> hierarchy/EVIDENCE-CHECK.md; a failure holds the release
#   tests       pytest tests/
#   regression  tools/build_regression.py check against the snapshot -> hierarchy/BUILD-REGRESSION.md (+ .json)
#   release     tools/make_release.py -> /n/fs/resemble/cs-atlas/releases/<date>[.N]/ and releases/latest; only when
#               every earlier stage passed and the regression flagged nothing (ALLOW_SWINGS=1 releases anyway)
#   tree        tools/organize_tree.py from releases/latest -> /n/fs/resemble/cs-atlas/schools/
# usage: hierarchy/rebuild.sh                       (all stages, all schools; run under nohup or in tmux, ~1 h)
#        STAGES="build audits" SCHOOLS="mit" hierarchy/rebuild.sh
#        TAG=<name> sets the snapshot name (default local-<timestamp>); BEFORE=<dir> compares against another snapshot
# Exit status: 0 all good, 1 a stage failed, 2 regression swings blocked the release.
set -u -o pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_WORK" || exit 1
PY="nice -n10 $CS_ATLAS_PY -u"  # the project interpreter (env/atlas; tools/atlas_paths.py PY)
SCHOOLS=${SCHOOLS:-$CS_ATLAS_SCHOOLS}
STAGES=${STAGES:-snapshot build ids copies ledger audits evidence tests regression release tree}
TAG=${TAG:-local-$(date +%Y%m%d-%H%M%S)}
BEFORE=${BEFORE:-hierarchy/logs/pkg-before-$TAG}
has() { case " $STAGES " in *" $1 "*) return 0 ;; esac; return 1; }
fail=0; swings=0
echo "== rebuild $TAG stages: $STAGES schools: $SCHOOLS code: $(git rev-parse --short HEAD 2>/dev/null)$(git diff --quiet HEAD -- tools 2>/dev/null || echo '+dirty') $(date +%T)"

if has snapshot; then
  echo "== snapshot $(date +%T)"
  for s in $SCHOOLS; do
    mkdir -p "$BEFORE/$s" && cp -p hierarchy/$s/{pis.json,students.json,report.json,lab_papers.jsonl.gz,student_papers.jsonl.gz} "$BEFORE/$s/" 2>/dev/null
  done
  $PY tools/build_regression.py snapshot --out "$BEFORE/counts.json" || fail=1
fi
if has build; then
  rm -f hierarchy/*/link-diagnosis.json  # stale diagnoses would hide open items from the re-diagnosis
  for s in $SCHOOLS; do echo "== $s $(date +%T)"; $PY tools/pi_hierarchy.py $s || { echo "FAILED $s"; fail=1; }; done
fi
if has ids; then
  # after the build, before every consumer (2026-10-29): ids never change once issued (hierarchy/ids/registry.sqlite)
  echo "== ids $(date +%T)"; $PY tools/atlas_ids.py || { echo "FAILED ids"; fail=1; }
fi
if has copies; then
  # before the audits (2026-10-29): the chain audit's copies check reads copies.json, with the stores' access-review causes
  echo "== copies $(date +%T)"; $PY tools/lab_paper_copies.py $SCHOOLS || fail=1
fi
if has ledger; then
  # after the copies, before the audits and the evidence check (2026-10-30, docs/UNAVAILABLE.md, R-AUD-10): the
  # unavailability ledger, run with the collectors' interpreter; it also writes the reasons onto copies.json
  # (lab_paper_copies.attach_ledger). Onboarding schools (school charters) get their ledger before their first release.
  onb=$($CS_ATLAS_PY -c 'import sys; sys.path.insert(0, "tools"); import school_config as c; print(" ".join(c.onboarding()))') || { echo "FAILED ledger: onboarding schools"; fail=1; onb=""; }
  ledger_schools=$(echo $SCHOOLS $onb | tr ' ' '\n' | awk 'NF && !seen[$0]++' | tr '\n' ' ')
  echo "== ledger $(date +%T) schools: $ledger_schools"
  nice -n10 $CS_ATLAS_COLLECTOR_PY -I -u "$CS_ATLAS_FULLTEXT_PUSH/unavailable_ledger.py" $ledger_schools || { echo "FAILED ledger"; fail=1; }
fi
if has audits; then
  echo "== student audit $(date +%T)"; $PY tools/student_audit.py $CS_ATLAS_SCHOOLS > /dev/null || fail=1
  echo "== chain audit (open items) $(date +%T)"; $PY tools/chain_audit.py > /dev/null || fail=1
  echo "== link diagnosis $(date +%T)"; $PY tools/link_diagnosis.py $CS_ATLAS_SCHOOLS || true
  echo "== chain audit $(date +%T)"; $PY tools/chain_audit.py || fail=1
fi
if has evidence; then
  # the build-time evidence check (2026-10-29): every period, listing, student relation, lab paper and byline link carries
  # its evidence (url, sha256, quote; school basis; appointment), or is whitelisted with a count in docs/evidence-whitelist.json
  echo "== evidence check $(date +%T)"; $PY tools/evidence_check.py || { echo "FAILED evidence check"; fail=1; }
fi
if has tests; then
  echo "== tests $(date +%T)"; $PY -m pytest tests -q -p no:cacheprovider 2>&1 | tail -3; [ "${PIPESTATUS[0]}" = 0 ] || { echo "FAILED tests"; fail=1; }
fi
if has regression; then
  echo "== regression $(date +%T)"
  $PY tools/build_regression.py check --before "$BEFORE/counts.json"; rc=$?
  [ $rc = 2 ] && swings=1
  [ $rc = 1 ] && fail=1
fi
if has release; then
  if [ $fail != 0 ]; then echo "== release skipped: a stage failed"
  elif [ $swings != 0 ] && [ "${ALLOW_SWINGS:-0}" != 1 ]; then echo "== release skipped: regression swings (hierarchy/BUILD-REGRESSION.md); ALLOW_SWINGS=1 releases anyway"
  else
    echo "== release $(date +%T)"; $PY tools/make_release.py --before "$BEFORE/counts.json" $([ "${ALLOW_SWINGS:-0}" = 1 ] && echo --allow-swings) || fail=1
  fi
fi
if has tree && [ $fail = 0 ]; then
  echo "== tree $(date +%T)"; nice -n10 ionice -c3 $CS_ATLAS_PY -u tools/organize_tree.py $SCHOOLS || fail=1
fi
echo "== done all $(date +%T) fail=$fail swings=$swings"
[ $fail != 0 ] && exit 1
[ $swings != 0 ] && exit 2
exit 0
