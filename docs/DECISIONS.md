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

## Coordinator-side and owner decisions (from the coordinator, 2026-11-02)
| date | decision | where it lives |
|---|---|---|
| 2026-10-30 | Every lab paper without a local copy gets a recorded, evidence-backed reason | unavailable ledger; `docs/UNAVAILABLE.md`; rebuild `ledger` stage; R-AUD-10 |
| 2026-10-30 | Development history is public on liv-daliberti/cs-labs-atlas branch `dev` (main to dev after tests and scans); the old email hash in history was accepted, not rewritten | 6ea0309; `secret_scan_allow.tsv` |
| 2026-10-30 | Everything lives under /n/fs/resemble/homogenizing-science | project move 619d8e3; `archive/migrations/relocate-2026-10-30.jsonl` |
| 2026-10-30 | Michigan: Mert Pilanci is not a Michigan PI; the 13 flagged DBLP acceptances stand; Berkeley's 2026 PNNL datasets are a sweep-check exception | `schools/michigan.toml` [census].not_pi (6e75a20); STAGE-2.md; `schools/berkeley.toml` [sweep_check] |
| 2026-10-30 | Copies taken from paths whose robots.txt disallows ClaudeBot or anthropic-ai are quarantined, not deleted | 4e18b85; `stores/<school>/quarantine/robots-ai/` with a manifest |
| 2026-10-30 | Only identity-confirmed copies count toward coverage; the identity rule rejects only on positive evidence of another document and the middle band stays pending | 58d42cf `fulltext-push/identity_rule.py`; download-time use 02b6fe5 |
| 2026-10-31 | The lab-page audit stops at 6k OpenAlex credits left; downloads take the rest | `docs/LAB-PAGES.md`; `docs/OPENALEX-SNAPSHOT.md` |
| 2026-10-31 | Subagents run on Sonnet; long-running Opus agents are replaced, not resumed | `~/.claude/settings.json` CLAUDE_CODE_SUBAGENT_MODEL=sonnet; `.claude/agents/atlas-worker.md` |
| 2026-10-31 | Lab-page acceptance bar: at most 1 membership, 2 role/year, 1 paper error per 20; doubtful 0.5; fresh seed per round; 3 rounds; kinds accepted separately; re-check 10 after rule changes; restamp when a regenerated set is a subset | `docs/LAB-PAGES.md` |
| 2026-10-31 | R-PAP-03 generalised: reviewed `faculty_end_moved` departures, with dated quotes, for every lab page found at another institution (CMU: 5 PIs) | `docs/RULES.md` R-PAP-03; 6ea8b88 |
| 2026-11-01 | A final round that passes membership but fails role/year wires the students membership-only, roles withheld (Berkeley) | `docs/LAB-PAGES.md`; d8cc85a |
| 2026-11-01 | The site hosts a copy only under a redistribution licence (CC-BY family, CC0, PD); every other confirmed copy is a "Read at source" link shown as readable (green); a candidate without a confirmed copy becomes a link only when confirmed to be the paper, by a basis that passes a 1-in-20 hand check | reader export d9ed021 |
| 2026-11-01 | The takedown of not-permitted hosted files goes to Codex inside the release handoff; `atlas release` fails without the "Take down" section | e1d1f60 |
| 2026-11-01 | The data-layout move to raw/reviewed/derived/work is applied at a forced quiet moment | 7407588; leftovers 8d02026 / `relocate-data-2026-11-02.jsonl` |
| 2026-11-01 | ROADMAP section 6 (#16 to #41): P0 (24, 16, 32, 37, 34), P1 (30, 18, 17, 22, 20), P2 (25, 26, 28, 29, 19, 33, 21, 27, 38, 23, decided 2026-11-02); all of P1 and P2 come before the release | `docs/ROADMAP.md` |
| 2026-11-01 | Direct commits to main are refused; Slurm jobs run only from a code snapshot; agents run an auto-resume check every 30 minutes after usage limits | `docs/CONTRIBUTING.md` (atlas.mainCommits enforce); session cron |
| 2026-11-02 | The download loops restart themselves at their time limit (#18); restarted onto that code as array 32065276 | `docs/ROADMAP.md` #18 |
| 2026-11-02 | One more students round each, with repairs first: Stanford round 6, Michigan round 4, CMU round 6 (after a failed round 5), on a 30-row sample per round at the same rates (membership <= 1.5, role/year <= 3, doubtful 0.5); an extended round that fails ends the work without the owner; `round_limit_extended_by_owner` and `sample_size: 30` in the acceptance files | `docs/LAB-PAGES.md`; acceptance files |
