# Tsinghua historical faculty-source review, 2026-11-16

Stage 1 currently has 20 unresolved department-years across 11 configured departments. This review records the missing evidence; it does not waive a gate or infer faculty appointments from current rosters.

| Finding |
|---|
| SW 2021: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| AIR 2016: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| AIR 2017: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| AIR 2018: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| AIR 2019: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| AIR 2020: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| AIR 2021: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| INSC 2016: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| INSC 2026: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| BME 2016: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| BME 2021: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| PI 2018: unusable: listing format tsinghua_banded_text parses 0 person entries (< 5) |
| PI 2019: nocapture: no archived 200 capture of the listing URL(s) in this half-year; unusable: listing format tsinghua_banded_text parses 0 person entries (< 5) |
| PI 2020: nocapture: no archived 200 capture of the listing URL(s) in this half-year; unusable: listing format tsinghua_banded_text parses 0 person entries (< 5) |
| PI 2021: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| PI 2022: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| PI 2023: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| PI 2024: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| PI 2025: nocapture: no archived 200 capture of the listing URL(s) in this half-year |
| PI 2026: nocapture: no archived 200 capture of the listing URL(s) in this half-year |

## Sources and corrections to the search plan

The old Precision Instrument listing has real roster content in 2016, but the failed 2018–2020 captures below contain only a 90-byte JavaScript redirect to `http://faculty.dpi.tsinghua.edu.cn/index.html`. They are not parser regressions. The successor site needs its own archived roster sources.

- https://web.archive.org/web/20180401035333id_/http://www.dpi.tsinghua.edu.cn:80/publish/dpi/5135/index.html — SHA256 `f2ce6de380a1a2c49ec2c67a753f404c5ad0df790fc5b45b7043d30b836f88e8`, 90 bytes; literal source `<script>window.location.href='http://faculty.dpi.tsinghua.edu.cn/index.html ';</script>`.
- https://web.archive.org/web/20181018002455id_/http://www.dpi.tsinghua.edu.cn:80/publish/dpi/5135/index.html — SHA256 `f2ce6de380a1a2c49ec2c67a753f404c5ad0df790fc5b45b7043d30b836f88e8`, 90 bytes; literal source `<script>window.location.href='http://faculty.dpi.tsinghua.edu.cn/index.html ';</script>`.
- https://web.archive.org/web/20190925075100id_/http://www.dpi.tsinghua.edu.cn:80/publish/dpi/5135/index.html — SHA256 `f2ce6de380a1a2c49ec2c67a753f404c5ad0df790fc5b45b7043d30b836f88e8`, 90 bytes; literal source `<script>window.location.href='http://faculty.dpi.tsinghua.edu.cn/index.html ';</script>`.
- https://web.archive.org/web/20191223032918id_/http://www.dpi.tsinghua.edu.cn:80/publish/dpi/5135/index.html — SHA256 `ef2bb6c06eef5e7889f75c26355669679af999144177beaeb0954f891c09d967`, 611 bytes; literal source `<!DOCTYPE html><script type="text/javascript" defer="defer" src="https://dfp2.bangruitech.com/public/downloads/frms-fingerprint.js?custID=157&version=4.3.6&cookieDomain=current&timestamp=1577059200&serviceUrl=https://dfp2.bangruitech.com/public/generate/jsonp"></script><script type="application/javascript" src="https://asmgr2.bangruitech.com/js/downloads/extra.js?includes=rd2,ajaxInject,env&version=1&timestamp=1577059200"></script><script type="application/javascript" src="/welcome.js?timestamp=1577059200"></script> <script>window.location.href='http://faculty.dpi.tsinghua.edu.cn/index.html ';</script>`.
- https://web.archive.org/web/20200221152809id_/http://www.dpi.tsinghua.edu.cn:80/publish/dpi/5135/index.html — SHA256 `f2ce6de380a1a2c49ec2c67a753f404c5ad0df790fc5b45b7043d30b836f88e8`, 90 bytes; literal source `<script>window.location.href='http://faculty.dpi.tsinghua.edu.cn/index.html ';</script>`.

AIR’s own institutional history states: “AIR于2020年由多媒体及人工智能领域的世界级科学家、企业家张亚勤院士创建。” Source: https://air.tsinghua.edu.cn/gyair/AIRjj.htm, SHA256 `de95e97690d503395817b97be8e53f18fff6c8db261a2bc61b5a63c5d5dbe47b`, captured 2026-11-16 in the private source store. Thus 2016–2019 precede this unit’s existence. The school window remains 2016–2026; the current gate has no source-backed unit-active-window mechanism. A narrow, evidenced scope correction would be a policy/schema change, not a fabricated roster or a reason to waive 2020/2021. No such change was made.

The exact current INSC faculty-directory URL already named in the charter (`https://www.insc.tsinghua.edu.cn/szdw_/zzjs.htm`) returned HTTP 404. The nmgroup page is a team roster, and has not been substituted for a full departmental roster. The current DPI page is a JavaScript shell; its public script identifies `advancesearch.jsp` as the data endpoint. The whole roster has not yet been captured and reviewed.

The new archive-era probe stopped at the repository’s shared Wayback cooldown (job 32342881). No cooldown, challenge, robots restriction or access control was bypassed. Cached indexes were also checked for the particular SW 2021, INSC 2016 and BME 2016 gaps; no usable roster for those gap years was recovered.
