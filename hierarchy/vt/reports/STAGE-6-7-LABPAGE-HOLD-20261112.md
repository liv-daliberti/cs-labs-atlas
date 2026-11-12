# Virginia Tech lab-page audit hold — 2026-11-12

Job `32227019` completed discovery follow-up, recovery, and audit on the 93-PI
trial package. The audit recorded 15 lab sites and 45 PI homepages used as lab
pages; 17 PIs still have no found web presence. It proposed 126 student rows
and 499 paper rows in `labpage-additions.json` (SHA-256
`34192d910e70dd15dca05a44de5e0e7c8a5f6d5adfcac749a0c89ae19b68a940`).
These are candidates only. Neither kind has a hand-check acceptance receipt.

The first reproducible sample used seed `20261112` for 20 student candidates
and seed `20261113` for 20 paper candidates. Preliminary review found:

- Student row 18: `Robert Bosch RTC` on Thang Hoang's page is the employer in
  the PI's Experience section, not a person. The captured phrase is “Robert
  Bosch RTC Pittsburgh, PA.” The reviewed `student-decisions.json` now marks
  that exact organization-name candidate `not`.
- Paper row 8: Peng Gao's claimed publication title is *Enabling Efficient
  Attack Investigation via Human-in-the-Loop Security Analysis*, but the
  selected lab-page listing text is “code and demo video.”
- Paper row 16: Eli Tilevich's claimed title is *Win with What You Have:
  QoS-Consistent Edge Services with Unreliable and Dynamic Resources*, but
  the selected listing text is “Song and Eli Tilevich.”

The two paper rows do not substantiate their claimed titles under LP-PAP-01.
The paper sample therefore cannot pass the at-most-one-error acceptance bar.
The remaining sample rows have not been fully scored; this is a diagnostic
hold, not a completed hand-check round. Repair the publication-page parser or
source-specific extraction, rerun the audit, then draw **new** random samples
for both kinds before any acceptance. Keep Stage 6 and Stage 7 open.

After excluding the organization-name row, a new 20-student diagnostic sample
(seed `20261114`) found Austin Kuo in Dan Williams's page news: the cited
PhD-candidacy event was at UIUC, and the person is absent from the VT current
members list. The reviewed decision now excludes that exact pre-VT row. The
sample also labels Yueyan Gu `other` despite the source saying `MS`; role
parsing needs review. The full captured phrase, “Yueyan Gu (MS, 2024 Fall),”
supports a bounded direct `masters` row in `few-students-evidence.json` for
Xuan Wang's VT period. This does not repair the extractor or approve its
remaining candidates. No student acceptance was stamped from this sample.
An isolated branch build then contained 10 students, 11 lab–student pairs,
14 student–paper links and 6 complete PI chains; these are trial counts, not
frozen release counts.
