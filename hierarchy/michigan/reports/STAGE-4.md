# Michigan, stage 4: appointment periods

Date: 2026-10-29, updated 2026-10-30. Gate: **passed** (see the update at the end).

## What was done
- `tools/periods_school.py fetch michigan` is running in the background (`hierarchy/michigan/tmp/periods_fetch.log`).
  - It fetches each PI's homepage from the department listing.
  - umich.edu hosts are read from Wayback, using the captures nearest 2026 and nearest the PI's first listed year.
    Other hosts are fetched live, with robots honoured and challenges detected.
  - All Wayback requests share the 6-second lock.
- `periods_school.py extract` reuses `faculty_periods.candidates()`. It needed one fix: the school pattern must be
  case-insensitive (`(?i:...)`).
- First results on about 30 fetched PIs:
  - Valeria Bertacco: start 2003 ("Professor ... at the University of Michigan since 2003").
  - Michael Cafarella: 2009–2020 ("a professor of Computer Science and Engineering at the University of Michigan from
    2009 to 2020", from his MIT page). This is an evidenced move-out.

## Gate (`tools/stage_gate.py michigan 4`)
- 242 of 248 PIs pass now: 240 on contiguous yearly listings, 2 on periods.
- The 6 open PIs have a gap year in their listings:

| PI | listing years | reason |
|---|---|---|
| Peter M. Chen | 2016–2021, 2023–2026 | not on the 2022 CSE captures (on leave, or a listing omission) |
| Ziyou Song | 2020, 2024–2026 | gap 2021–2023 |
| Christopher Brooks, Lionel Robert, Xi Jessie Yang, Yan Chen | UMSI / Robotics years with gaps | the unit listings have missing Wayback years (one capture a year at most) |

Each needs a period statement from a CV or bio, or a reviewed period in `census-overrides.json`. The fetch running now
covers most of them.

## To finish
```
/usr/local/anaconda3/2024.02/bin/python -I tools/periods_school.py fetch michigan     # resumable; cached pages are not refetched
/usr/local/anaconda3/2024.02/bin/python -I tools/periods_school.py extract michigan
/usr/local/anaconda3/2024.02/bin/python -I tools/stage_gate.py michigan 4
```
- **R-PAP-03 (stale listings after a move).** Every extracted end year must be checked against the listings. Cafarella
  is listed until 2020, which is consistent.

## Update, 2026-10-29 21:40 UTC
- **Fetch finished.** 263 Wayback captures and 42 live pages. 51 homepage URLs have no capture.
- **Extraction:** 8 periods and 240 holds. The holds are 134 PIs whose pages state no appointment year and 106 with no
  page (the 37 additions have no homepage in their unit listing).
- **Two rules learned:**
  - A closed range followed by later professor-rank listings is a rank step, not a departure. Viswanath Nagarajan's
    "2014-2020: Assistant Professor" kept no end.
  - A closing statement that says the PI moved becomes `faculty_end_moved` evidence. Michael Cafarella: MIT from 2020.
    The builder then set his 6 adjunct listing years 2021–2026 aside as `listingsAfterMove` (R-PAP-03 confirmed in the
    Michigan build).
- **Gate:** `stage_gate.py` still shows 6 open: Peter M. Chen, Ziyou Song, Christopher Brooks, Lionel Robert, Xi
  Jessie Yang, Yan Chen.
  - Each has a gap year in the listings. For the four from other units, the gap is in the Wayback captures of their
    unit listing: the UMSI 2024 capture is a shell, and the 2021–2025 UMSI pages are paginated.
  - No page states their appointment years. They need a reviewed period, or listing captures for the gap years.

## Update, 2026-10-30: gap years, profile years, ISO dates. Gate passed
- **The gate now uses the professor-rank span.** It runs from the first to the last ladder or courtesy year, and every
  year in it needs a listing of any rank (`stage_gate.pi_years`/`span_gaps`).
  - Ziyou Song passes: research scientist in 2020, visiting in 2024, ladder from 2025.
  - Jason Corso passes: adjunct in 2021, which is a listed year.
- **Gap years** (`periods_school.py gaps`). Each missing year is proven by a dated Wayback capture naming the PI with a
  professor title: homepage, unit listing, or unit profile page (charter `[periods].profile_patterns`).
  - Closed: Christopher Brooks 2024–25, Lionel P. Robert Jr. 2023, Xi Jessie Yang 2023–24, Yan Chen 2021–25, Raed Al
    Kontar 2025, James D. Weiland 2023–25 (BME profile `bme.umich.edu/people/weiland-james/`), Huei Peng 2023–24.
  - Huei Peng's 2025 is not proven: the 2025 Robotics captures are 2.4 KB script shells, and no ME or Robotics profile
    capture exists. He has two periods, and his 2025 papers stay outside them.
- **Profile years** (`periods_school.py extend`). UMSI's directory is paginated in Wayback for 2021–2025, so most UMSI
  PIs were listed in 2020 and 2026 only. Each addition's unlisted window years were checked against its unit profile
  page.
  - 155 PI-years were proven for 35 of 54 additions with a profile URL, for example Elizabeth Yakel 2016–2025, Joyojeet
    Pal, Julie Hui and Gabriela Marcu 2019/2020–2025, and Andrea Forte 2024–25 (she joined in 2024).
  - Each contiguous run of proven years became a reviewed period (`reviewed: periods_school_extend_20261030`).
  - Evidence: `hierarchy/michigan/profile-year-evidence.json`.
- **Peter M. Chen, 2022: unproven.**
  - He is in no CSE capture from 2021-09 to 2022-09. The three captures parse completely, with 144–149 entries each.
  - His homepage has no 2022 capture and states no dates.
  - `census-overrides.json` records `unproven_years: [2022]` with the search made (`why_unproven`). The gate accepts a
    reviewed unproven year. His 2022 papers stay outside the appointment; nothing is inferred.
- **Two fixes.**
  - Periods written by the tools carried `asof: 20261029`, which `contains()` cannot read. They now use ISO dates, and
    the four already written were repaired.
  - The builder looked for 'Jr.' as the family name in listing quotes (R-PAP-08). It is fixed in `pi_hierarchy.py`, so
    Lionel P. Robert Jr.'s 203 identified works count.
- **Not usable:** `pub.orcid.org/robots.txt` disallows all agents, so ORCID employments are not a period source here.
- **Gate:** `tools/stage_gate.py michigan 4` **passes**. 288 PIs: contiguous listings 239, reviewed periods 48, one
  reviewed unproven year.
