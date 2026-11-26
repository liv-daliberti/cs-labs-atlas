# KAIST onboarding, stage 2 - 2026-11-24 (IN PROGRESS: stopped before the audit draw)

Not complete. The stage-2 gate has not been recorded and no 50-row audit has been drawn: the affiliated-unit search (`cs_related_school.py units kaist`, job 32542312) is still on the shared Wayback clock (about 4-5 min per CDX query or capture; EE alone is a paged directory). All 16 units are in the charter (EE, GSAI, KDS, ISYSE, MAS, GSIS, CT, ME, SEMI, AISEMI, BIOENG, AE, PHYS, CEE, NQE, CBE); the draw must wait for all of them (D-0003, coordinator 2026-11-24).

## Done so far
- Census (`census_build.py`, commit e135055f): 273 listing-name rows merged on the School of Computing's own profile id (`[census].profile_id_pattern`, `/people/view?idx=N`) into 166 persons, 77 PIs (53 ladder, 17 emeritus, 7 courtesy). The earlier 129 "PIs" were duplicate spellings of 77 persons. Sung-Eui Yoon (idx 20: 'Sungeui Yoon', 'Sung-Eui Yoon', '윤성의') is one ladder PI, years 2016-2026. No name-similarity merge exists anywhere.
- Hangul-only persons (no Latin spelling in any capture): 18 now (the coordinator counted 19 before the merge). The Latin name is taken only from the same profile page when it states `<Hangul>(<Latin>)` (`tools/profile_romanization_school.py`, reviewed/profile-romanization.json, quote + url + sha256): 1 found, 17 `romanization_missing`.
- Sweep from the snapshot extension: 56,613 papers, sweep check pass; DBLP dump persons naming KAIST: 542; OpenAlex candidate rule: 345 author ids (264 not matching a census name). All three feed `cs_related_school.py candidates|review` after the units land.
- Stage 3 preview on the corrected PIs (live-first, no Wayback): 77 PIs, homes School of Computing for all 77 (listing-row evidence, status accepted), website discovery done; 10 PIs open (9 `website archive evidence pending`, 1 `website official discovery link not recorded`); the homes audit draw is not taken.

## Still to do
units search -> `candidates` -> `review` (decide every candidate; unresolved = `excluded_unresolved` with reason) -> census-refresh/homes/build/discover for the added PIs -> `excluded_audit.py draw kaist --worker claude-kaist-1124` (stop; independent reviewer).

## Update 2026-11-24 evening (D-0064, D-0065)
- Held courtesy people (55 on the CS page): home-unit evidence from live unit pages, name = census name or its Hangul alias (same-string match, never romanized), title = Korean or English ladder title (`faculty_evidence` now reads Hangul names and 조교수/부교수/정교수/교수). Proven now: 9 (Yongdae Kim EE+GSIS, Woontack Woo CT, Junyong Noh CT, Jaewoong Chung EE, Insu Yun EE+GSIS, Sang Ho Yoon CT, Hye Won Chung EE, 노용만 EE, 원유집 EE). The other 46 are in no live unit directory text we hold (EE pages 5+, GSAI and ISE are wayback-only, most unit pages are Hangul-only); none is marked "no page" until the units job and the wayback-only hosts are done.
- Stage 4 (live-only): `periods_school.py fetch --live-only` (env `PERIODS_FETCH_ARGS`), 77 PIs, 71 live pages fetched; `extract`: 11 periods proven from the person's own page (Korean phrasing: "1991년부터 KAIST 전산학부 교수로 재직", "2008년에 카이스트 교수로 부임", "2024년 2월 KAIST 부임"), 66 holds (no appointment statement on the live pages; gaps/extend wait for the Wayback clock). No `faculty_end_moved` found.
- captures/kaist.sqlite is opened with `sqlite3.connect(timeout=120)` and every write is a short autocommit, so a live write beside the units job waits for the lock instead of losing a row.

## Update 2026-11-24 night (coordinator: unit list incomplete)
- Charter: the Data Science school is gsds.kaist.ac.kr (robots Crawl-delay 30; faculty directory /people, entries carry no title text); kds.kaist.ac.kr was the dormitory site. Added units ID (Industrial Design, React/Firebase SPA: needs the browser render, routes /people/Faculty, /OtherFaculty, /OldFaculty), DHCSS, BUS (경영공학부 on www.business.kaist.ac.kr + 기술경영학부 on btm.kaist.ac.kr; the Wayback-era English names there appear as 'Kwon, Seokbeom' with the title BEFORE the name, which faculty_evidence does not read) and STP. 20 affiliated units, 27 hosts, gate 0 passes. The central directory findpeople.kaist.ac.kr needs a login and is not used.
- Live match of the 55 held courtesy people: 14 proven (+ So-Yeon Ahn, Jeong-woo Jang, Lanu Kim, 정서현 on DHCSS), 41 pending_wayback, 0 excluded. A matcher false positive (Hyung Chan Kim vs 'Hyung Seok Kim', STP) was rejected by hand.
- `cs_related candidates`: 498 (326 DBLP, 158 OpenAlex rule, 14 official-profile ladder). `review` refuses until units-done.json covers all 20 units' listings, so per-unit new-candidate counts wait for the units job and its rerun.
- ID render job: Slurm 32545710 (js_render_capture, 3 URLs), pending.

## Update 2026-11-24 night 2 (GSDS, BTM, ID)
- GSDS: gsds.kaist.ac.kr/people lists 55 people with name, focus area, e-mail and phone only; there are no per-person detail pages on that host (the only links are external 홈페이지 sites of other hosts) and the /eng/people page has no titles either. Proven by title: 0 of 55. All stay pending; the heading "교수진" is not rank evidence (coordinator).
- BTM/Business: `faculty_evidence` reads `| <title> <Hangul>(<Latin>)` on btm.kaist.ac.kr only (host-scoped; ladder = 교수/부교수/조교수/정교수/석좌교수; 겸임/명예/초빙/연구 and other prefixed 교수 are not ladder; the Latin name is returned as `latin_alias`). Fixture test in tests/test_cs_related_korean_titles.py. Proven: Jihee Kim, Youngsun Kwon.
- ID: browser render job 32545710 stored /people/Faculty (16 ladder faculty: 5 Professor, 9 Associate, 2 Assistant), /OtherFaculty (Adjunct Professor only) and /OldFaculty (Emeritus only). Proven: Andrea Bianchi (Associate Professor). Ian Oakley is on no ID page.
- Courtesy people: 17 proven live, 38 pending_wayback, 0 excluded.

## Update 2026-11-24 night 3 (js_render unit pages, GSDS as a discovery roster)
- `cs_related_school.unit_pages()` now also reads the newest ok `js_render` row of any charter listing URL (rendered DOM text, dom_sha256 as the page hash) and drops the live shell of the same URL, so `candidates` and `review` see browser-rendered listings generally. ID's listings are now the three rendered URLs (/people/Faculty, /OtherFaculty, /OldFaculty). Test: tests/test_unit_pages_js_render.py.
- `[cs_related].discovery_units = { GSDS = "kaist_gsds_people" }`: the GSDS roster names are candidates (source `unit_roster_discovery`, 40 not already known out of 55), never proof of rank; `review` proves each by a ladder title on a home-unit page or profile, and nobody is excluded for the missing GSDS title. Format `kaist_gsds_people` + fixture test.
- `candidates` now: 541 (326 DBLP, 158 OpenAlex rule, 40 GSDS roster, 17 official-profile ladder).
