# Identity coverage disclosure, 2026-11-10

Of the 207 census PIs, **52 have an owned DBLP binding** (17 earlier + 35 from the 2026-11-09 expansion: 9 with a source-stated English name, 26 under R-PAP-44) and can have attributed papers. **155 PIs have no attributed papers** because no source-bound identity has been admitted for them; each carries a reviewed `no_identity` hold with its reason in `reviewed/census-overrides-school.json`. The hold records the true state; it is not a finding that these people have no publications, and no admission claim for Tsinghua may omit it.

| Group | PIs | Meaning |
|---|---:|---|
| owned DBLP binding | 52 | papers attributable (appointment, affiliation and type gates still apply) |
| held: thin title evidence | 7 | name-compatible Tsinghua DBLP person with 2-9 credited exact titles on the PI's own page (唐杰 3, 朱文武 5, 邓志东 9, 刘斌 3, 梁斌 2, 张和明 7, 杨帆 5); R-PAP-44 needs 10 |
| held: unlinked candidate | 51 | a name-compatible Tsinghua-affiliated DBLP person exists but no source tie was found; first backlog for identity work |
| held: none found | 97 | no name-compatible Tsinghua-affiliated DBLP person in the 2026-09-01 dump extract (pinyin via Text::Unidecode is a candidate generator only; polyphonic or unusual names and records not tagged Tsinghua are missed) |

Other open limits stated with the native package: anchored OpenAlex ids of the 52 PIs are all marked mixed (Chinese-name collisions), so about 560 anchored rows of run 1 are not admitted and need per-work evidence to restore (`scratch/tsinghua-native52-1110/anchored-restore-candidates.json`); 5 environmental-emissions works are held for 李振华; pre-2021 department listings are not captured, so 2016-2020 papers are admitted only through typed periods (刘奕群, 翟季冬, 李振华 earlier periods, 陶建华 from 2022-12). 130 of the 207 prepared home-department entries rest on a listing row that carries the name only (no title line).
