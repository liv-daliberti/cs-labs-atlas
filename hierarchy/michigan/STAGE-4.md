# Michigan, stage 4: appointment periods

Date: 2026-10-29. Gate: **not passed (in progress)**. 6 PIs are open; homepage fetching is still running.

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
