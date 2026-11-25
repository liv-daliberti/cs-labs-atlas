# UCSD onboarding, stage 3 (PIs and labs) - in progress, 2026-11-24

Run on the CSE census (136 ladder-faculty PIs) while stage 2 continues. `atlas stage-gate ucsd 3 --run --submit --from-worktree --allow-shared`:
census-refresh ok; homes ok (120 accepted CSE homes, 16 held with no accepted home: people the CSE page lists as ladder whose home unit is another
department; their homes come from their own unit's listing row once the stage-2 unit captures are reviewed, never from title text); homes-shared ok (ucsd rows only).
Jobs: build 32543239 (COMPLETED), labpage-discover array 32543240_[0-7], discover-merge 32543241, labpage-audit 32543242.
Stage 3 is rerun after the stage-2 census is final; discovery is per-PI resumable so only newly admitted PIs are asked.

Discovery shard 7 (32543240_7) was at 12 PIs after 6 h 20 m of its 8 h limit (Wayback-paced PIs take up to ~30 min each). Fallback 32551689 reruns
`labpage_audit.py discover ucsd --shard 7 --of 8` at the same snapshot commit 55c3c68a, afternotok on shard 7 with kill-on-invalid-dep (discovery skips PIs
that already have a record). Merge 32543241 now waits afterany on 32543240 and 32551689 (shards 0-6 completed ok), so check before the audit that every
PI has a discovery record; the stage-4 fetch 32545271 also waits on the fallback.
