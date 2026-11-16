# Precision Instrument successor roster source review, 2026-11-16

The old publish/dpi/5135 archive captures from 2018 onward redirect to this portal. Exact successor-URL CDX queries found six missing-year rosters; their saved bytes show institute-grouped faculty and staff cards. The new explicitly selected `tsinghua_dpi_archive` reader preserves each card’s written title, profile link and institute. The charter’s faculty-title filter excludes administrative/technical staff; no rank is invented and no professor is admitted to the computing census by this source review.

| Year | All named cards | Faculty-title cards | Capture SHA256 |
|---|---:|---:|---|
| 2018 | 103 | 81 | `3935236c1231e70f825b304c103a5d1747a47b1f19b63e772e7f1fc1ca2fc3a9` |
| 2019 | 102 | 82 | `54b08ca726e9d605df4045e29e71590015233a34642141c7d0e253c922d4f538` |
| 2021 | 109 | 88 | `a578c84343615d927a7e1a662b55319410af3bac8e75a39b73c826495b10ada8` |
| 2022 | 109 | 87 | `b4bd29184b889cd884b01f9bd45c8896a4097ade25205eee79e50fc5297f2753` |
| 2024 | 108 | 88 | `f33f189f2e00c6bc673ee86c046f52e1099d8e8b878447d42d7ebd89ce53ba1a` |
| 2025 | 106 | 86 | `c216611e97e8b2c952f8753e3b0bb6061596f6804a0f991e06e0b70489acbfab` |

All six source bodies were rehashed and parsed; all named cards have unique written names in their source. Total: 637 cards, of which 512 carry the charter’s faculty-title words. The first requested April 2018 capture redirected to May 2018; the actual final capture timestamp stays in the same calendar year and is retained as the observation date.

| Year | Requested capture | Final capture |
|---|---|---|
| 2018 | https://web.archive.org/web/20180418122943id_/http://faculty.dpi.tsinghua.edu.cn:80/index.html | https://web.archive.org/web/20180523132510id_/http://faculty.dpi.tsinghua.edu.cn/index.html |
| 2019 | https://web.archive.org/web/20190207051824id_/http://faculty.dpi.tsinghua.edu.cn:80/index.html | https://web.archive.org/web/20190207051824id_/http://faculty.dpi.tsinghua.edu.cn:80/index.html |
| 2021 | https://web.archive.org/web/20211024030201id_/http://faculty.dpi.tsinghua.edu.cn/index.html | https://web.archive.org/web/20211024030201id_/http://faculty.dpi.tsinghua.edu.cn/index.html |
| 2022 | https://web.archive.org/web/20220501160058id_/http://faculty.dpi.tsinghua.edu.cn/index.html | https://web.archive.org/web/20220501160058id_/http://faculty.dpi.tsinghua.edu.cn/index.html |
| 2024 | https://web.archive.org/web/20240706191038id_/http://faculty.dpi.tsinghua.edu.cn/index.html | https://web.archive.org/web/20240706191038id_/http://faculty.dpi.tsinghua.edu.cn/index.html |
| 2025 | https://web.archive.org/web/20250326023753id_/https://faculty.dpi.tsinghua.edu.cn/index.html | https://web.archive.org/web/20250326023753id_/https://faculty.dpi.tsinghua.edu.cn/index.html |

Validation: 54 related listing, quote and stage-1 category-group tests passed, plus source-byte checks on every capture, scoped lint and the Tsinghua charter check. The new reader does not auto-detect unrelated pages. Tests retain staff titles as `other`, require a real profile link and an individual name/title, preserve spaced-name quote anchors, and exclude adjacent contact details.

This records source coverage only. Historical profile identity, computing scope and appointment periods remain later-stage reviews. No gate exception, canonical package, release or website was changed. Source captures and acquisition receipts remain in `code/hierarchy/tsinghua/tmp/sources-1116/`; the two archive jobs are 32343560 and 32343684.

## Normal pipeline replay

The private normal listing importer produced 512 additional faculty-year rows, each with a literal captured quote and SHA256. Total school listing rows rose from 13,350 to 13,862. Stage 1 findings fell from 20 to 14, with zero waived items. The uncollected halves remain `pending`; neither an archive search nor an uncollected half substitutes for a roster. Raw card completeness checks found no omitted faculty card with a missing or placeholder link; one 2019 non-faculty card was intentionally excluded by the link guard. The other 13,350 prior person rows are unchanged.

Replay root: `/n/fs/resemble/homogenizing-science/code/hierarchy/tsinghua/tmp/dpi-stage1-1116`. These rows have not been folded into the additions-backed faculty census or used to expand appointment intervals.
