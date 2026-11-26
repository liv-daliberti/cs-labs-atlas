# KAIST onboarding, stage 0 - 2026-11-24

KAIST is registered as `kaist` (Korea Advanced Institute of Science and Technology), status `onboarding`, order 1000 (provisional). This registers the school and its sources; no PI, student, paper or website coverage is claimed.

## Scope (owner decision D-0059, `leases/coord/DECISIONS.md`)
- Campus I157485424, ROR https://ror.org/05apxxy63 (GRAS 2025 CS&E band 76-100), plus lineage children National NanoFab Center I4210164985 and Intelligent Synthetic Biology Center I4210110126.
- Verified against the local OpenAlex institutions snapshot: `oa_institutions.py search 'Korea Advanced Institute'` (one hit) and `lineage I157485424` (two associated children, both kept; KIAS I125608817 and STEPI I1306601404 listed as 'related' associates and deliberately not used). `children-counts` returned 0 works everywhere because the institutions snapshot has no per-institution work counts; the measured count is the snapshot extension below. Live ROR API not queried.
- KIAS and STEPI: never swept, not related, never add a PI. No hospital class (no medical school). Census 2016-2026 including departed and retired faculty (D-0045).

## Charter
`school_config.py --check kaist`: ok. 19 must_match and 29 must_not_match cases. Look-alike traps are all negative cases: KIST (Korea Institute of Science and Technology, English and Hangul), KIAS, STEPI, GIST, DGIST, UNIST, KISTI, ETRI, UST (University of Science and Technology), SNU, POSTECH, their e-mail domains, a spoof host, and the Korea Science Academy of KAIST (the main regex carries a lookbehind `(?<!academy of )`, `excluded_regex` repeats it). Positive cases cover the English name variants (`Korean ...`, `Inst.`, `Adv.`, `&`), KAIST, `kaist.ac.kr` / `kaist.edu` strings and URLs, and the Hangul names (한국과학기술원, 카이스트). No Han-name (pinyin) machinery is enabled: `census.han_suffix_merge` is unset.
CS (School of Computing) is the only full-coverage department. 16 affiliated units are discovery sources (EE, GSAI, KDS, ISysE, MAS, GSIS, CT, ME, Bio and Brain Eng, AE, Semiconductor, AI Semiconductor, Physics, CEE, NQE, CBE), never automatic admissions.

## Host gate
`school_hosts.py kaist`: 22 hosts, 0 inconsistent. 16 live (probes ok), 5 wayback-only, 1 none.
- `gsai.kaist.ac.kr` / `ai.kaist.ac.kr` answer a JavaScript cookie challenge (cupid.js) to a plain request: wayback-only (2026-11-05 owner rule).
- `ise.kaist.ac.kr` / `ie.kaist.ac.kr`: robots.txt answers HTTP 500 (unreachable): wayback-only. `civil.kaist.ac.kr` 301s to cee.kaist.ac.kr: wayback-only alias.
- `mobility.kaist.ac.kr`: robots.txt `Disallow: /` for all agents: use = none.
- Several hosts return 404 for robots.txt (treated as allowed). No host names ClaudeBot / anthropic-ai. `library.kaist.ac.kr` was dropped from the host list (probe redirects); thesis `kind = "none"`.

## Snapshot extension (no API credits)
`OA_DATE=2026-10-14 atlas pipeline snapshot-ext SCHOOLS=kaist --from-worktree`. First submission 32539160/32539161 failed in 2 s on node012/node016 (full /tmp, `database or disk is full`). Resubmitted excluding those nodes: filter array 32539184 (tasks 0,1,2,4,5,6,8-15 finished; 0 at 59:13 of 59 min; 3 and 7 TIMEOUT), merge 32539185 cancelled; tasks 3 and 7 rerun as 32540359 (--time=01:00:00, still partition `all`), merge 32540361 completed. `ext-kaist.sqlite`: 118,782 works, 58,400 authors.

## Gate
`atlas stage-gate kaist 0`: pass (exit 0), 22 hosts, snapshot_works 118782. `--traps`: one finding (lab-page capture store not created; belongs to stage 3).
