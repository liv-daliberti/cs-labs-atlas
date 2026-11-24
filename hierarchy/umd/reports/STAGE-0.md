# UMD stage 0: charter and config (2026-11-24, worker claude-umd-1124)

Scope: owner decision D-0054 (leases/coord/DECISIONS.md), encoded in `schools/umd.toml`. Census span 2016-2026 including departed and retired faculty (as D-0045). Process v4, per-PI admission.

## What was done
- Charter `schools/umd.toml`: primary I66946132, ROR 047s2c258. Kept lineage children: ARLIS I4388482636, ESSIC I4210144776, CISESS I4405270764, Maryland Quantum Materials Center I4405254040, QuICS I4210108409, JQI I4210151733. UMIACS has no OpenAlex id and is covered by the affiliation regex (`UMIACS`, "Institute for Advanced Computer Studies").
- `openalex_excluded` (12 ids): IBBR I4389425230, JGCRI I112475681, Virginia-Maryland Vet College I39822340, Fraunhofer USA CMA I4210162509 (associated, not a child), UMB I126744593 and its School of Medicine I4405257352, UMBC I79272384, UMGC I4210107443, UMES I22407884, UMCES I149521062, USM I1317227900, UM Medical System I14285509. `openalex_related` is empty: no hospital is related (College Park has no medical school).
- Baltimore trap: the regex requires College Park evidence (`University of Maryland, College Park` variants, a bounded gap form that refuses baltimore / eastern shore / global campus / medical, `UMIACS`, or a umd.edu domain). A bare "University of Maryland" does not match; 17 must_match and 26 must_not_match cases pass `school_config --check`. `excluded_regex` names the other USM institutions and the four excluded units.
- Hosts (23): `school_hosts.py umd` reports 0 inconsistent. robots.txt checked for every host on 2026-11-24.
  - quics.umd.edu and jqi.umd.edu: robots.txt disallows ClaudeBot, so `use = none` (no request, not even Wayback). Their papers come through OpenAlex lineage only.
  - arlis.umd.edu and mqmc.umd.edu: unreachable (connection fails, no robots.txt), `wayback-only`.
  - robotics.umd.edu (403 Access Denied) and cs.umd.edu (301 alias of www.cs.umd.edu): `wayback-only`.
  - info.umd.edu (the iSchool, ischool.umd.edu redirects there): probe URL moved to `/directory/` after a 301.
  - Crawl delays honoured: linguistics 10 s, ece/isr/me/aero/cee/bioe/robotics 5 s, others 2 s; the project floor is 3.2 s per host.
- Snapshot extension (OA_DATE=2026-10-14): filter array 32539207 failed on node016 (disk full; tasks 1-6), requeued; tasks 1, 6, 9 hit the 59 min cap amid heavy contention and were rerun as job 32540456 (COMPLETED); merge 32541469 COMPLETED 2026-11-24 20:15Z on node203. ext-umd holds 243,775 works and 153,783 authors (work_author is 0 in every ext store).

## Gate
`bin/atlas stage-gate umd 0 --record`: pass, 0 open, 23 hosts, snapshot_works 243775.

## Exceptions
None. Open choices carried to the owner are in the final report (QuICS/JQI use=none, ARLIS/MQMC wayback-only: confirmed by the coordinator).

## Not verified
Live ROR API was not queried; the ROR id is the snapshot's.
