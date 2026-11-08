# Tsinghua computing expansion: first reviewed batch (2026-11-08)

Status: onboarding, incomplete. No stage or release gate is claimed.

## Scope and results

The existing source ledger contains 120 supported PI-role rows for 119 distinct names (Hu Shimin appears twice), covering CS, IIIS and AIR. It contains no Software faculty rows, despite the captured current Software directory naming 41 people. This batch independently checked every one of the 41 linked official profiles and admits 27 current professors with explicit computing research. Fourteen research appointments remain open. None of these 27 names occurs in the previously supported set: strict distinct supported roles increase from 119 to 146.

The baseline website ledger contains 55 verified rows for 54 distinct names, including sites whose PI role remains pending. This first batch adds no website verification. A professor admission creates a provisional PI-centered lab only; 27 new independently evidenced named labs are not claimed. Six existing PI-owned group rosters were independently reviewed for the student batch.

## Manually reviewed student memberships

| PI | current | alumni |
|---|---:|---:|
| Xu Wei | 5 | 0 |
| Hou Pan-Yu | 6 | 0 |
| Xu Mengdi | 5 | 0 |
| Zhang Huanchen | 9 | 0 |
| Li Jian | 4 | 15 |
| Ma Xiongfeng | 0 | 11 |

Total: 55 student-lab memberships across six labs: 29 current (28 PhD, one undergraduate), 26 doctoral alumni. Incoming students, current generic graduate students with unspecified degree, postdocs, generic alumni and other-institution doctoral students are excluded. Mengdi Xu roster start labels predating her Tsinghua appointment are preserved only inside literal quotes; current membership uses the 2026 capture observation, with no start interval inferred. Jin Kai retains explicit co-advising with Andrew Yao.

## Software research-role holds

| Name | rank | profile |
|---|---|---|
| 张荷花 | 副研究员 | https://www.thss.tsinghua.edu.cn/faculty/zhanghehua.htm |
| 万海 | 副研究员 | https://www.thss.tsinghua.edu.cn/faculty/wanhai.htm |
| 周旻 | 副研究员 | https://www.thss.tsinghua.edu.cn/faculty/zhoumin.htm |
| 刘璘 | 研究员 | https://www.thss.tsinghua.edu.cn/faculty/liulin.htm |
| 刘英博 | 副研究员 | https://www.thss.tsinghua.edu.cn/faculty/liuyingbo.htm |
| 金涛 | 副研究员 | https://www.thss.tsinghua.edu.cn/faculty/jintao.htm |
| 黄向东 | 副研究员 | https://www.thss.tsinghua.edu.cn/faculty/huangxiangdong.htm |
| 沈恩亚 | 副研究员 | https://www.thss.tsinghua.edu.cn/faculty/shenenya.htm |
| 裴忠一 | 助理研究员 | https://www.thss.tsinghua.edu.cn/faculty/peizhongyi.htm |
| 王彦凯 | 助理研究员 | https://www.thss.tsinghua.edu.cn/faculty/wangyankai.htm |
| 张慧 | 副研究员 | https://www.thss.tsinghua.edu.cn/faculty/zhanghui.htm |
| 陈莉 | 研究员 | https://www.thss.tsinghua.edu.cn/faculty/chenli.htm |
| 苗欣 | 助理研究员 | https://www.thss.tsinghua.edu.cn/faculty/miaoxin.htm |
| 丁旋 | 副研究员 | https://www.thss.tsinghua.edu.cn/faculty/dingxuan.htm |

A project PI/lead, software project chair, patent or publication count does not establish an independent academic lab. Zhang Hui has a research rank in the current dedicated field and older ambiguous 副教授/副研究员 wording, so remains held. Deng Yangdong has a current dedicated 副教授 field and an explicitly 博导 (doctoral supervisor) work-history clause; both are retained.

## Evidence and reproducibility

Reviewed native inputs: `reviewed/census-additions.json` and `reviewed/few-students-evidence.json`. Each source-bound fact preserves its original URL, capture SHA256, literal quote and observation date. Student role headings and current/alumni sections were manually checked against the same original bytes. No network name search or DBLP request was made.

Source container: `/n/fs/resemble/homogenizing-science/scratch/tsinghua-expansion-1108/hierarchy/tsinghua/raw/school-captures.sqlite`, initially copied from the prior top25 cache without mutating that shared ledger. Reproduction scripts and holds live next to the isolated container. The 54-target official capture job 32147099 finished with 54 HTTP-200 captures; capture success alone admitted no one. Automation job 32147112 reviews up to 100 exact directory-linked profiles, and subsequent website job 32147124 is serialized after it. All jobs specify CPU/memory/time and passed `sbatch --test-only` without Preempts.

## Open work

Automation, EE, Shenzhen Data and Information, the School of Artificial Intelligence, Institute for Network Sciences and Cyberspace, and computing faculty in other units remain incompletely inventoried. Automation collection is active; neither 41 Software captures nor 100 Automation targets is a supported-PI count. EE and Shenzhen cached pages are JavaScript shells without named faculty cards. Historical leavers and 2016-2025 appointments are also incomplete.

The existing 119 supported identities and this 27-person addition still need one native census/charter integration. Current reviewed inputs can be landed without a canonical package promotion. School-local original source bytes must be preserved during that integration. Next paper work: independently anchor compatible local DBLP person records to owned-site exact links or personally credited citations, then check appointment and school affiliation per work. Career bibliography counts must never be presented as Tsinghua lab-paper counts.

Validation: all 27 admitted role clauses, all 27 computing descriptions, all 41 directory links and all 55 selected student quotes reproduced from original SHA256-checked HTTP-200 bytes. Native build not run in this first batch.
