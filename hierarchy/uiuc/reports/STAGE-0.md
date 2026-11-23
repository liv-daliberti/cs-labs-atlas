# UIUC onboarding — 2026-11-23

UIUC is registered as `uiuc`, University of Illinois Urbana-Champaign, with status
`onboarding`. This registers the school; no PI, student, paper, release or public
website coverage is claimed by this change.

## Scope

Owner decision D-0043 (`leases/coord/DECISIONS.md`) approves Urbana-Champaign and
internal research centers, including NCSA; excludes Chicago/Springfield campuses,
separately affiliated hospitals, Biohub and joint institutes. Only computing
faculty enter through the existing census rules. Joint appointments require their
own UIUC faculty evidence; a center membership alone does not create a PI.

`oa_institutions.py search 'University of Illinois' --country US` and
`lineage I157725225` verified the primary OpenAlex identifier and ROR
`https://ror.org/047426m28` against the local 2026-10-14 institutions snapshot.
The live ROR API was inaccessible through the web tool; no live ROR verification
is claimed. The charter records the full retained/excluded lineage rationale.

Biohub Chicago and CloudBank have multiple parent institutions and are excluded;
NCSA and its XSEDE child remain inside the primary UIUC lineage. No separately
related institution is swept. The existing atlas site key was checked against
`SITE_DATA/universities/university-of-illinois-at-urbana-champaign.json.gz`.

## Configuration and source checks

`atlas charters uiuc` passes. The charter embeds 11 positive and 16 negative
affiliation cases, including both campus-name spellings, current and legacy
domains, the UIUC abbreviation, and other-campus/system look-alikes.

The Siebel School/previous CS department is the full-coverage unit. Fourteen
other departments and research units are discovery sources for computing-related
faculty, not automatic faculty admissions. Historical CS and current Siebel URLs
are separate source eras; no founding-date exemption is claimed for the rename.
Every historical roster year still needs dated source evidence.

`school_hosts.py uiuc` checked 17 hosts: 15 permitted live directory probes
returned HTTP 200 and two hosts are archival-only; zero inconsistent hosts.
Results are in `hierarchy/uiuc/raw/hosts.json`; fetched robots and page bodies
are held by the standard school capture store (`atlas_paths.CAPTURES`).

- `cs.illinois.edu` redirects (301); the current directory is on
  `siebelschool.illinois.edu`. The old host is used only for historical captures.
- IDEALS (`www.ideals.illinois.edu`) returned HTTP 403 for robots.txt. It is
  archival-only under the owner access rule of 2026-11-05, with no live thesis
  adapter enabled. Public OpenAlex/CORE metadata remain alternative routes.
  Repository records must explicitly name the adviser; no student relation is
  inferred from an author or committee membership alone.

The standard `new-school` tool created an empty UIUC catalog, object-store
directories and a creation receipt. No other school's data was copied.

## Remaining onboarding

Stage 0 remains open until the UIUC OpenAlex snapshot extension finishes; the
existing filtered snapshot has zero works indexed under UIUC's primary lineage.
Use the standard `snapshot-ext` pipeline for the existing 2026-10-14 snapshot,
then recheck stage 0. No API-credit sweep is needed for that extension.
Subsequent work is dated roster collection, faculty census and identity/window
review, lab/student evidence, paper collection and the existing independent
audits. Publication follows the normal per-PI release process.
