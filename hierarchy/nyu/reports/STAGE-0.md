# NYU onboarding, stage 0 - 2026-11-24

NYU is registered as `nyu` (New York University, status `onboarding`, order 36). Registration only: no PI, student, paper or website coverage is claimed.

## Scope (owner decision D-0058)
- Kept: I57206974 (ROR 0190ak572, GRAS 2025 CS&E 51-75) with Courant I36672615 and NYU Grossman Long Island I4405267893. Tandon has no OpenAlex id (Polytechnic Institute of NYU / poly.edu before 2014); the regex names it.
- Excluded children: Abu Dhabi I120250893, Shanghai I258800397, Paris I4210165353, Florence I4210123063, Press I2799442855.
- Related, regex-only: NYU Langone Health I4210086933, Langone Orthopedic I4210163050, Rusk I42102869.
- Not NYU: Bellevue, VA NY Harbor, Brookdale, Coleridge. Flatiron Institute I4387153999 / Simons Foundation: separate, in excluded hosts and excluded_regex.
- Verified with `oa_institutions.py search 'New York' --country US` and `lineage I57206974` against the local snapshot (live ROR not queried). `children-counts` returned 0 works for every child (noted in ids_note, not blocking).

## Charter checks
- `school_config.py --check nyu`: ok (30 must_match, 43 must_not_match cases incl. Abu Dhabi/Shanghai strings and hosts, SUNY/CUNY/NYIT, Flatiron, NewYork-Presbyterian, Tandon, Polytechnic Institute of NYU, Courant, CDS, Grossman, CUSP, cs/cims/engineering.nyu.edu).
- `school_hosts.py nyu`: 16 hosts, 0 inconsistent. Wayback-only after the first run found robots 403/302/unreachable or a challenge: cds, math, as, cusp, wagner, www.nyu.edu, poly.edu, files.nyu.edu. Live: cs, engineering, cims, wp, stern, steinhardt, med, tisch.

## Snapshot extension
`OA_DATE=2026-10-14 atlas pipeline snapshot-ext SCHOOLS=nyu --from-worktree`: first submission 32539281/32539282 failed in 2 s (node012/node016 /tmp full; merge cancelled). Resubmitted with SBATCH_EXCLUDE=node302,node014,node012,node016: filter array 32539354 (16 tasks, 51-56 min of the 59 min cap, all COMPLETED), merge 32539355 COMPLETED. No API credits. Gate: snapshot_works = 326,415.

## Gate
`atlas stage-gate nyu 0`: pass (open 0, hosts 16, snapshot_works 326415).
