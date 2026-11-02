# Decision log

Every owner decision the project works under, dated, with the rule, file or commit it changed. Newest last within each
section. Rule ids are in `docs/RULES.md`; the lab-page decisions are in `docs/LAB-PAGES.md`. A decision that is only a
working practice (not a rule of the data) names the document that holds it. Coordinator-side decisions are added in their own
section by the coordinator.

## Scope and structure (owner)
| date | decision | where it lives |
|---|---|---|
| 2026-10-21 | A lab is a PI plus their advisees; every PI has one own lab; the hierarchy is school, department, PI labs, papers and students | `docs/RULES.md` R-HIER-01; `docs/ADDING-A-SCHOOL.md` |
| 2026-10-21 | A dated department faculty listing in a year proves the appointment for that year | `docs/RULES.md` R-PAP-01 |
| 2026-10-21 | Researched advisees named on a lab page are lab members | `docs/RULES.md` R-STU-01 |
| 2026-10-22 | The site is the CS atlas plus departments only; scope is CS-related faculty in any department | `docs/RULES.md` (scope), site source |
| 2026-10-27 | Stanford is the 6th school; the repository is public (cs-labs-atlas) | `docs/CONTRIBUTING.md` |
| 2026-10-27 | Name-variant merges of students happen only within one PI's lab; the same name under two PIs stays two people | `docs/RULES.md` R-HIER-03 |
| 2026-10-28 | Stanford Profiles `Doctoral (Program)` and `Reader` listings are not advising without co-authorship | `docs/RULES.md` R-STU-02 |
| 2026-10-29 | Michigan is the 7th school, added by the standard staged protocol | `docs/ADDING-A-SCHOOL.md`; `schools/michigan.toml` |
| 2026-10-29 | Stale listings after an evidenced move are not appointments (a reviewed `faculty_end_moved` period closes the appointment) | `docs/RULES.md` R-PAP-03 |
| 2026-10-30 | Every uncopied lab paper gets an evidence-backed reason; the development history is public on `cs-labs-atlas` | `docs/UNAVAILABLE.md`; `docs/CONTRIBUTING.md` |

## Lab pages (owner and coordinator)
| date | decision | where it lives |
|---|---|---|
| 2026-10-30 | Every lab has a lab page or a documented reason; every student and paper on it is in the build or has a reason | owner request quoted in `docs/LAB-PAGES.md`; `tools/labpage_audit.py` |
| 2026-10-31 | Additions enter the build only after a hand check of 20 students and 20 papers per school: at most 1 membership error, at most 2 role/year errors, at most 1 paper error; doubtful counts half; fresh seed each round; kinds accepted separately | `docs/LAB-PAGES.md` (acceptance bar); `hierarchy/<school>/.../labpage-acceptance.json` |
| 2026-10-31 | After 3 failed rounds for a kind at a school the work stops and that kind is not wired (Princeton had a 4th round) | `docs/LAB-PAGES.md`; commit e3e88e4 |
| 2026-10-31 | Undated names in labs older than the window need an explicit current marker; `current and former` headings are no marker | `docs/LAB-PAGES.md`; commit 0924419 |
| 2026-10-31 | Pages of labs at another institution are excluded | `docs/LAB-PAGES.md` (`site_at_other_institution`) |
| 2026-10-31 | Departures found by the audit come from reviewed `faculty_end_moved` periods (five CMU PIs) | `docs/RULES.md` R-PAP-03; commit 6ea8b88 |
| 2026-10-31 | Michigan: Deep Blue, news.umich.edu and record.umich.edu are never used (Wayback included); challenged umich.edu hosts are read only from Wayback `id_` captures | `schools/michigan.toml`; `docs/LAB-PAGES.md` |
| 2026-10-31 | A host's robots.txt is honoured, including groups naming ClaudeBot / anthropic-ai; no logins, paywalls or bot challenges | `docs/LAB-PAGES.md` (Fetching) |
| 2026-10-31 | Paper additions are re-checked against each PI's current appointment periods, overrides included; a regenerated additions file keeps its acceptance only if the set only shrank (`restamp`) | commits fd97e21, b329aac |
| 2026-11-01 | A final students round that passes membership but fails role/year wires the kind membership-only (roles withheld) | `docs/LAB-PAGES.md`; commit 5a3106e (Berkeley) |
| 2026-11-01 | Stanford and CMU students get rounds 4 and 5 (recorded exception to the 3-round limit); Princeton is not included; Michigan keeps its limit | `docs/LAB-PAGES.md`; `round_limit_extended_by_owner` in the acceptance files; commit 9ed4030 |
| 2026-11-01 | Repairs apply to all schools: committee words, reference blocks, co-advised-with names, parenthetical roles, other-institution markers, older-lab undated rule for every plan, administrative staff and affiliates | `tools/labpage_audit.py` (`repair_reason`); commits ee5b9f4, f3a38f9, 468d2a1, 0706082 |
| 2026-11-01 | After any rule change, 10 students are re-sampled at every accepted school | `docs/LAB-PAGES.md` (acceptance bar 3) |

## Working practice
| date | decision | where it lives |
|---|---|---|
| 2026-10-27 | OpenAlex: the shared key allows 10,000 credits a UTC day; stop at 6,000 left (the downloads agent uses the rest) | `docs/OPENALEX-SNAPSHOT.md`; `docs/LAB-PAGES.md` |
| 2026-10-31 | Subagents run on Sonnet | `docs/CONTRIBUTING.md`, agent definitions |
| 2026-10-31 | Slurm jobs run from a code snapshot of one commit; submit with `atlas submit` | `docs/CONTRIBUTING.md`; commit 7fb0cdb |
| 2026-11-01 | Direct commits to main are refused; work in a worktree and land with `tools/agent_worktree.sh land` | `docs/CONTRIBUTING.md` (ROADMAP #16) |
| 2026-11-01 | The data tree is split into raw / reviewed / derived / work, reached only through `atlas_paths.data()` | `docs/DATA-LAYOUT.md`; commit 7407588 |
| 2026-11-01 | The site reader hosts a copy only with a redistribution licence (CC / public domain); the rest get read-at-source links | `docs/CHANNELS.md`, reader export |

## Coordinator-side decisions
(To be added by the coordinator: reader licence rule detail, quarantine, identity rule, P0/P1/P2.)
