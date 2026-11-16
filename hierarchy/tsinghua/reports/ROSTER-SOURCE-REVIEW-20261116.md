# Tsinghua roster source review, 2026-11-16

Reviewed 72 additional student records from two PI-owned institutional homepages: 51 for 刘知远 (Zhiyuan Liu), 21 for 唐杰 (Jie Tang). Each name, role, explicit date and source hash was checked against the stored original bytes. Finite graduate intervals are represented as alumni; undated Tang entries were held. Earlier reviewed roster rows are unchanged.

Cheng Yang is held because the source describes collaboration. The two Yan Wang entries are held because they are distinct people with the same name and require an explicit identity treatment.

These are manual R-STU-01 roster evidence rows, not a student-recall acceptance or signoff. The source body for Liu is inline Vue data in the original HTML; it was parsed as strings and never executed.

The previous census refresh was stopped by its duplicate-profile guard. Tsinghua uses the documented 120-byte additions-backed census (`PROVENANCE.md`); the reviewed native trial retains that input. The initial private build was cancelled before completion when the evidence correction set was finalized. A new build must use a frozen copy of the committed inputs. No canonical package has been promoted.

```json
{
  "school": "tsinghua",
  "date": "2026-11-16",
  "reviewer": "codex-tsinghua-finish-1116",
  "target": "hierarchy/tsinghua/reviewed/roster-evidence.json",
  "before_sha256": "7a0de30afda62b1d36f708671b7816897a467e7a5e0093080ca37142a9085ded",
  "after_sha256": "7a22d1af6e455e0ea14a978c7912aee37d9b7b5267cdc7a3fe735a027d309704",
  "added": {
    "刘知远": 51,
    "唐杰": 21
  },
  "held": [
    {
      "pi": "刘知远",
      "name": "Cheng Yang",
      "reason": "Source states collaboration, which does not establish advising."
    },
    {
      "pi": "唐杰",
      "name": "Yan Wang (M) (graduated in 2020)",
      "reason": "Two distinct source entries share Yan Wang; preserve M/F disambiguation for an identity review before native within-lab merging."
    },
    {
      "pi": "唐杰",
      "name": "Yan Wang (F) (graduated in 2019)",
      "reason": "Two distinct source entries share Yan Wang; preserve M/F disambiguation for an identity review before native within-lab merging."
    }
  ],
  "sources_database": "/n/fs/resemble/homogenizing-science/code/hierarchy/tsinghua/tmp/sources-1116/hierarchy/tsinghua/raw/school-captures.sqlite",
  "caveat": "Source review of two rosters; not a school-wide recall signoff or paper-acceptance decision."
}
```

## Additional institutional roster

The linked English/Chinese student pages of Yang Yuan (the reviewed PI key `Yuan Yang`) add six dated graduate/alumni rows. Kangping Xu also has an explicit co-adviser statement for 姚期智 / Andrew Yao, yielding seven additional lab-student pairs. The English source is https://people.iiis.tsinghua.edu.cn/~yuanyang/student-en.html (SHA256 `0e5ee415cb4a06832c30a910ef5b8e9c2234aea2a9631781635cb6c4128473f6`); its Chinese counterpart is https://people.iiis.tsinghua.edu.cn/~yuanyang/student.html (SHA256 `2616c71b5415ddc7ca1c31f26392faeade77b7a67a9b01c1e4d0057fd48d90cb`). The homepage identifies the current Tsinghua IIIS associate professor at https://people.iiis.tsinghua.edu.cn/~yuanyang/index.html (SHA256 `5c2d286620e9b6581742abdf49339efa4555b94c2ea7879dcd670bf2c77d196f`).

Jingqin Yang remains held: the personal roster states 2021 onward, whereas the official Structural Intelligence group page states 2024 onward. Chao Li is a postdoc and is excluded from this graduate-student delta. No other shared group members were assigned to either PI. Total reviewed delta: **79 lab-student pairs across four PIs**.
