# Tsinghua stage 2 open-item holds (2026-11-10)

146 candidates in hierarchy/tsinghua/reviewed/cs-related-review.json are recorded as `not_faculty_listed` with `hold: true`, `kind: "open_item_hold"` and a batch id. Each reason starts `[OPEN ITEM, NOT A CLAIM]`: it records that evidence is missing, not that the person is not faculty (ZJU/HKUST/NTU precedent). To turn one into a real decision, supply any of: a captured faculty directory or official profile of the person's unit that lists the name with a rank; an owned page or ORCID tie; or an OpenAlex/DBLP record naming a Tsinghua unit from 2023 on. Filter: `kind == "open_item_hold"`, grouped by `batch`.

Selection (least likely faculty first, from local data only: DBLP dump affiliation notes and record counts, OpenAlex sweep raw affiliation strings of the person's own works):
- OIH-A-least-likely (90): last Tsinghua-bearing OpenAlex string 2023 or earlier, or no DBLP record after 2022, or under 10 DBLP records, or a center/lab-only DBLP affiliation with no recent string.
- OIH-B-no-unit-string-few-records (19): no Tsinghua-bearing OpenAlex string at all and under 20 DBLP records.
- OIH-C-no-department-string-since-2022 (37): no Tsinghua department-level string since 2022 and no directory hit.
Never held: candidates with a name hit in a captured directory, the strong candidates, anyone with a 2022+ department-level Tsinghua string, a Tsinghua string in 2024+ with 15+ records, or a department/school-level DBLP affiliation with 40+ records (14 such records were removed after the fresh reviews).

Fresh-reviewer samples (separate subagents, 40 each): first A 36 ok/1 obvious/3 unsure, first B+C 29 ok/11 wrong wording (template bug)/1 obvious; after fixes A 33 ok/7 wrong wording, B+C 29 ok/7 wrong wording/2 obvious; final mixed sample 38 ok/0 wrong/0 obvious/2 unsure. The two final unsure are Kai Sun [09/1171-4] and Lan Yang (priority candidates for a directory capture).

| name | DBLP pid | batch | DBLP records | last Tsinghua string |
|---|---|---|---|---|
| Bo Li [50/3402-79] | 50/3402-79 | A | 5 | 2022 |
| Chao Zhu | 76/445-2 | A | 31 | 2017 |
| Cheng Xue | 35/8195-1 | A | 8 | 2025 |
| Di Wang | 18/5410-39 | A | 6 | 2023 |
| Dong Li [47/4826-40] | 47/4826-40 | A | 5 | - |
| Fan Yang [29/3081-106] | 29/3081-106 | A | 7 | - |
| Fang Zhang | 79/1363-3 | A | 8 | 2018 |
| Feng Gao [10/2674-14] | 10/2674-14 | A | 63 | 2020 |
| Hao Wen [57/77-10] | 57/77-10 | A | 7 | - |
| Hong Liu | 29/5010-24 | A | 16 | 2023 |
| Hongmin Li | 118/6414-2 | A | 8 | 2019 |
| Hui Li | 66/3387-75 | A | 8 | - |
| Huizhi Liang | 02/5302-3 | A | 5 | 2026 |
| Jian Zhang [07/314-49] | 07/314-49 | A | 27 | - |
| Jianguo Chen | 18/733-5 | A | 16 | 2021 |
| Jianhui Yang | 35/10764-1 | A | 7 | 2026 |
| Jianwei Zhang | 144/1628-4 | A | 44 | - |
| Jiao Zhang | 04/527-2 | A | 118 | 2021 |
| Jiawei Gao | 124/9335-4 | A | 6 | - |
| Jiawei Li | 12/3242-12 | A | 6 | 2025 |
| Jie Wang | 29/5259-22 | A | 40 | 2016 |
| Jing Chang | 30/2583-1 | A | 7 | 2021 |
| Jing Lin | 80/2054-4 | A | 5 | - |
| Jing Wei | 54/3517-1 | A | 27 | 2018 |
| Jing Wu [88/3604-18] | 88/3604-18 | A | 8 | - |
| Jiyuan Zhang | 93/7807-1 | A | 9 | 2017 |
| Kai Wang | 78/2022-14 | A | 57 | 2019 |
| Kaiwen Zhang | 364/1450-15 | A | 6 | 2024 |
| Ke Sun [69/476-3] | 69/476-3 | A | 15 | 2019 |
| Lan Yang | 52/1313-2 | A | 8 | - |
| Lei Ding | 59/2353-9 | A | 6 | - |
| Liang Li [14/1395-12] | 14/1395-12 | A | 8 | - |
| Liang Xu | 54/3420-10 | A | 14 | - |
| Liang Zeng [09/2922-6] | 09/2922-6 | A | 5 | - |
| Liang Zhao | 63/5422-23 | A | 21 | 2019 |
| Lin Song | 49/1217-4 | A | 5 | 2017 |
| Liyan Zhang | 54/4596-5 | A | 6 | 2018 |
| Ming Xu [43/3362-22] | 43/3362-22 | A | 7 | - |
| Ming Yuan | 37/449-3 | A | 5 | 2023 |
| Ming Zeng | 52/2761-10 | A | 9 | 2019 |
| Mingyuan Zhong | 146/9730-1 | A | 23 | 2018 |
| Mo Li | 87/4982-12 | A | 8 | 2025 |
| Na Liu | 82/385-6 | A | 8 | - |
| Nan Jiang | 06/4489-23 | A | 9 | 2020 |
| Nicholas Clinton | 138/8675 | A | 16 | - |
| Peng Li [83/6353-31] | 83/6353-31 | A | 43 | 2017 |
| Peng Wan | 07/4221-2 | A | 8 | 2020 |
| Pengfei Yu | 73/8078-1 | A | 27 | 2018 |
| Ping Zhang | 13/4682-18 | A | 7 | - |
| Qi Wang [19/1924-94] | 19/1924-94 | A | 6 | 2026 |
| Qi Xin | 77/2901-2 | A | 8 | 2026 |
| Qiang Wang | 64/5630-40 | A | 6 | - |
| Qingquan Li | 64/1170-3 | A | 5 | 2023 |
| Rui Kang | 89/1167-4 | A | 5 | 2025 |
| Shuang Song | 86/4211-6 | A | 7 | - |
| Shuming Liu | 181/1700-2 | A | 5 | 2020 |
| Shuo Wang [63/1591-28] | 63/1591-28 | A | 7 | - |
| Tao Chen [69/510-15] | 69/510-15 | A | 37 | 2016 |
| Tao Chen [69/510-38] | 69/510-38 | A | 12 | - |
| Tao Li [75/4601-27] | 75/4601-27 | A | 8 | - |
| Tao Zhao | 62/6776-2 | A | 17 | 2016 |
| Tian Wu | 02/4795-2 | A | 5 | - |
| Wei Li [64/6025-262] | 64/6025-262 | A | 7 | 2026 |
| Wei Wang [35/7092-207] | 35/7092-207 | A | 9 | 2019 |
| Wei Xiao | 20/4794-2 | A | 9 | - |
| Weichen Zhang | 151/8859-1 | A | 5 | 2025 |
| Weihao Lu | 44/9720-2 | A | 8 | - |
| Weijie Zheng | 174/2123 | A | 65 | 2020 |
| Xiao Sui | 320/2137-3 | A | 5 | 2025 |
| Xiaoqian Wang | 151/3215-4 | A | 5 | 2019 |
| Xiaoyu Li | 18/6855-6 | A | 8 | 2021 |
| Xiaoyu Zhang | 12/5927-18 | A | 5 | 2026 |
| Xin Gao [56/2203-14] | 56/2203-14 | A | 6 | - |
| Xin Liang | 31/7475-4 | A | 15 | - |
| Xinran Zhang [115/6420-1] | 115/6420-1 | A | 11 | 2021 |
| Xiong Zhang | 06/2161-5 | A | 6 | - |
| Xun Liang | 93/2940-1 | A | 144 | 2020 |
| Yan Wang [59/2227-42] | 59/2227-42 | A | 24 | - |
| Yang Zhang | 06/6785-52 | A | 5 | 2021 |
| Yi Gao | 38/4304-4 | A | 8 | - |
| Yifan Qiao [200/8215-1] | 200/8215-1 | A | 24 | 2019 |
| Ying Zhang | 13/6769-69 | A | 7 | - |
| Yiwei Li | 48/9884-4 | A | 8 | 2025 |
| Yu Gao | 46/2974-27 | A | 7 | 2021 |
| Yu Gu | 15/4208-13 | A | 5 | - |
| Yunyi Chen | 208/7906-1 | A | 8 | 2026 |
| Yushuo Chen | 45/4693-1 | A | 7 | 2026 |
| Zhaoyang Wang | 41/8315-1 | A | 7 | - |
| Zhen Li [74/2397-29] | 74/2397-29 | A | 5 | - |
| Zheng Chen [33/2592-13] | 33/2592-13 | A | 5 | 2016 |
| Chen Chen [65/4423-83] | 65/4423-83 | B | 11 | - |
| Hang Yin | 81/7626-8 | B | 19 | - |
| Hao Fei | 389/9728 | B | 11 | - |
| Hao Hu [67/6924-15] | 67/6924-15 | B | 13 | - |
| Haobo Zhang | 151/9860-4 | B | 16 | - |
| He Zhang [24/2058-34] | 24/2058-34 | B | 15 | - |
| Jiayu Chen [80/8422-1] | 80/8422-1 | B | 11 | - |
| Jin Chen | 03/5287-13 | B | 12 | - |
| Kai Ni | 46/3815-5 | B | 16 | - |
| Lin Hou | 87/8247-3 | B | 11 | - |
| Ming Yu | 42/1562-3 | B | 14 | - |
| Sijie Chen | 201/3118-1 | B | 16 | - |
| Siqi Li [34/180-3] | 34/180-3 | B | 17 | - |
| Tao Huang | 34/808-10 | B | 13 | - |
| Xiaoping Zhang [38/3901-6] | 38/3901-6 | B | 11 | - |
| Xudong Zhang [58/6205-8] | 58/6205-8 | B | 14 | - |
| Yu Wang [02/5889-96] | 02/5889-96 | B | 10 | - |
| Zhao Zhang [87/6853-14] | 87/6853-14 | B | 11 | - |
| Zhe Li [11/751-14] | 11/751-14 | B | 11 | - |
| Chao Wang [188/7759-20] | 188/7759-20 | C | 26 | - |
| Fang Wen | 66/1922-1 | C | 107 | - |
| Fei Wang | 52/3194-61 | C | 29 | - |
| Hongming Lyu | 188/3631-2 | C | 21 | - |
| Hu He | 48/4498-1 | C | 36 | - |
| Hui Liu | 93/4010-14 | C | 29 | - |
| Junbo Wang | 17/5974-2 | C | 55 | - |
| Kai Sun [09/1171-1] | 09/1171-1 | C | 78 | - |
| Kai Sun [09/1171-4] | 09/1171-4 | C | 38 | - |
| Kun Li | 75/1458-1 | C | 138 | - |
| Lei Zhang [64/5666-33] | 64/5666-33 | C | 38 | - |
| Libin Liu | 59/8294-2 | C | 47 | - |
| Lin Dai | 00/2420-1 | C | 104 | - |
| Ming Yang [98/2604-2] | 98/2604-2 | C | 206 | - |
| Nan Li | 84/3795-14 | C | 29 | - |
| Peng Liu | 21/6121-30 | C | 23 | - |
| Peng Lu | 86/241-2 | C | 22 | - |
| Ping Luo | 54/4989-4 | C | 23 | - |
| Qi Lu | 41/4012-1 | C | 13 | 2026 |
| Qiang Fu | 17/1352-17 | C | 30 | - |
| Rui Chen [02/1003-6] | 02/1003-6 | C | 35 | - |
| Rui Liu | 42/469-14 | C | 23 | - |
| Wayne Zhang | 239/6045 | C | 136 | - |
| Wei Wu | 95/6985-22 | C | 62 | - |
| Xinyi Tong | 171/0531-2 | C | 22 | - |
| Xueyi Liu | 47/10627-3 | C | 11 | 2025 |
| Yang Liu [51/3710-228] | 51/3710-228 | C | 32 | - |
| Yi Wang [17/221-0018] | 17/221-0018 | C | 34 | - |
| Yibo Wang [25/4764-2] | 25/4764-2 | C | 26 | - |
| Yin Sun | 07/863-1 | C | 169 | - |
| Yong Zhao | 14/1356-5 | C | 83 | - |
| Yujia Liu | 42/10221-4 | C | 14 | 2025 |
| Yujie Wu | 02/3699-2 | C | 37 | - |
| Yun Tian | 85/4928-2 | C | 37 | - |
| Yuqing Xie | 346/2254 | C | 10 | 2025 |
| Zhenhua Xu | 126/7726-3 | C | 33 | - |
| Zhenyu Huang | 57/3207 | C | 41 | - |
