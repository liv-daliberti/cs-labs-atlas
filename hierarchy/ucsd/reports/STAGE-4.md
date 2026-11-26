# UCSD onboarding, stage 4 (appointment periods) - submitted, 2026-11-24

Chain submitted by hand (stage_gate has no dependency option): `atlas_pipeline.submit('stage4-ucsd', ..., dependency='afterany:32543240')`, so Wayback fetching starts only
when the stage-3 labpage-discover array ends (one fetching stage at a time, L-28/L-49). Jobs (afterok chain): periods-fetch 32545271, extract 32545272, gaps 32545273,
extend 32545274, truncated 32545275, deep 32545276. Run again for PIs that stage 2 adds (fetch is incremental).
