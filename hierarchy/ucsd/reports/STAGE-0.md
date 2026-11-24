# UCSD onboarding, stage 0 - 2026-11-24

UCSD is registered as `ucsd`, University of California San Diego, status `onboarding`. This registers the
school and its sources; no PI, student, paper or website coverage is claimed.

## Scope

Owner decision D-0053 (`leases/coord/DECISIONS.md`) is binding: UIUC-style boundary (campus plus internal research
centres), UW-style regex-only hospitals, census 2016-2026 including departed and retired faculty, computing faculty only.
OpenAlex I36258959, ROR https://ror.org/0168r3w48 (GRAS 2025 CS&E rank 50), verified against the local 2026-10-14
institutions snapshot with `oa_institutions.py search` and `lineage` (live ROR API not queried).

- Kept lineage children: SDSC I181653535, Scripps Institution of Oceanography I150209017, Center for Wireless
  Communications I4392738179, Swartz Center I4405263016, plus OpenTopography I4394709161 and the CCE LTER I4387152662
  (SDSC/SIO-hosted facilities; not named in D-0053, kept as internal facilities).
- Excluded: CloudBank I4405259881, UCSD-CNRS joint chemistry lab I4387154842, California Sea Grant I4210136348, California
  Space Grant I4210159531 (all named in D-0053), and CalCOFI I4405260842 (multi-agency consortium found in the lineage; my
  conservative choice under D-0053's "any other consortium/joint child").
- Related, regex-only: UC San Diego Health System I2800935791, UCSD Medical Center I4210132395, Moores Cancer Center
  I4390039236. In OpenAlex all three are lineage children of the campus; the snapshot filter gates an institution whose
  lineage holds a related id by the affiliation regex (`oa_snapshot.keep_work`), so listing them as related makes them
  regex-gated even though they sit in the lineage. They credit papers of in-scope PIs and never add a PI.
- Not related, never swept: Salk, Rady Children's, VA San Diego, Scripps Mercy, UC San Diego Foundation. Look-alikes:
  San Diego State I26538001, University of San Diego I160856358. The Scripps Research Institute is a different
  institution from Scripps Institution of Oceanography; the regex names the latter in full and never the bare word "Scripps".

## Charter checks

`school_config.py --check ucsd`: ok. The charter embeds 19 must_match and 22 must_not_match cases (both campus-name
spellings, UC San Diego / UCSD, SDSC, SIO, Qualcomm Institute, Halicioglu Data Science Institute, SCIDS, Jacobs, Moores, DBLP
note form, e-mail and URL forms; other UC campuses, bare "University of California", SDSU, USD, Salk, Scripps Research,
Scripps Mercy/Clinic, Rady, VA, community colleges, bare "La Jolla"). "La Jolla" and Calit2 (shared with UC Irvine) appear
only in `loose`, never in the main regex. CSE is the full-coverage department; ECE, HDSI/SCIDS, Cognitive Science,
Mathematics, MAE, Bioengineering, SDSC, Qualcomm Institute, Swartz, CWC, Jacobs, SIO and UC San Diego Profiles are
discovery sources, not automatic admissions, as at UIUC.

## Host gate

`school_hosts.py ucsd`: 17 hosts, 0 inconsistent. 15 live (all probes ok, no challenge; no named-AI-agent group;
Crawl-delay treated as 2 s), 2 wayback-only, 0 none.
- `escholarship.org`: robots.txt returned HTTP 403 to the project fetcher, so wayback-only (2026-11-05 owner rule);
  thesis `robots = "unreachable"`, `kind = "none"`. Theses are reachable through OpenAlex/CORE and Wayback.
- `cseweb.ucsd.edu` (legacy CSE host): robots.txt answers a 302 to cse.ucsd.edu, treated as disallowed, wayback-only; the
  current directory is on `cse.ucsd.edu`.
- Probe corrections: MAE's directory is `mae.ucsd.edu/people/faculty-profiles` (a Google-Sites page also exists, not used);
  `profiles.ucsd.edu` redirects to `/search/` (probe uses that; Profiles is discovery only, no login).

## Gates

`atlas stage-gate ucsd 0`: fails only on "openalex snapshot: no works of I36258959" until the snapshot extension merges
(as UIUC). `--traps` lists the not-yet-created lab-page capture store, expected before stage 1.
The standard `new-school` created an empty catalog and a receipt; no other school's data was copied.

## Snapshot extension

Submitted from the committed charter (see job ids appended below). Follow-up: queue task UCSD-SNAPSHOT-REVIEW-1124.
