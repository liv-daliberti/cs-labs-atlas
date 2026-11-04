"""Roster pair verdicts (UChicago Statistics + CAM rosters, deep dive 2026-11-04).

Source of the 75 old-rule pairs: hierarchy/uchicago/reports/ROSTER-ETD-CROSSCHECK.json (git-ignored data; student, pi, joint_papers, pi_last,
old_rule, r_star). Every verdict here quotes a page (URL + capture date); nothing is from memory. Writes
hierarchy/uchicago/reviewed/roster-pair-verdicts.json (tracked) and prints the rule table.

  python3 tools/roster_pair_verdicts.py            # rebuild the JSON and print the measurements

verdict: true (listed/stated as this PI's (co-)advisee) | not (a different adviser is named and this PI does not list the student, or the
paired person is a namesake) | unsettled (no page found either way). basis: 'listing' (a positive statement), 'other-adviser' (the student's
adviser is named elsewhere), 'absence' (absent from this PI's page that lists personnel for those years: weaker), 'namesake', 'none'.
Not used: Mathematics Genealogy Project (robots.txt names ClaudeBot and anthropic-ai: Disallow /), LinkedIn, Scholar, ProQuest, OpenReview.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

WT = Path(__file__).resolve().parent.parent
SRC = Path(P.HIERARCHY) / 'uchicago' / 'reports' / 'ROSTER-ETD-CROSSCHECK.json'
if not SRC.exists():
    SRC = WT / 'hierarchy' / 'uchicago' / 'reports' / 'ROSTER-ETD-CROSSCHECK.json'
OUT = WT / 'hierarchy' / 'uchicago' / 'reviewed' / 'roster-pair-verdicts.json'

# evidence sources: key -> (url, capture date, quote)
S = {
    'barber': ('https://rinafb.github.io/group/', '2026-11-03 (Wayback 20260618181709 and live)',
               'Aabesh Bhattacharyya (PhD 2026) ... Ruiting Liang (PhD 2026, Computational & Applied Math) ... Raphael Rossellini , PhD student (co-advised with Rebecca Willett) ... Ran Dai (PhD 2020) ... Haoyang Liu (PhD 2020, co-advised with Chao Gao) ... Byol Kim (PhD 2021, co-advised with Mladen Kolar) ... Yonghoon Lee (PhD 2023) ... Wanrong Zhu (PhD 2024, co-advised with Wei-Biao Wu) ... Yu Gui (PhD 2025, co-advised with Cong Ma) ... Rohan Hore (PhD 2025)'),
    'willett': ('https://voices.uchicago.edu/willett/research/group-members/', '2026-11-04',
                'Current members: ... Sue Parkinson , Committee on Computational and Applied Mathematics; Raphael Rossellini , Department of Statistics ... Former members: ... Melissa Adrian , Postdoc at Purdue University Mechanical Engineering ... Abby Stevens , Argonne National Laboratory'),
    'sanz': ('https://sites.google.com/a/uchicago.edu/sanz-alonso/mentoring', '2026-11-04',
             'PhD Students, Committee on Computational and Applied Mathematics, University of Chicago Ruiyi Yang, graduated Spring 2022 ... Yuming Chen, graduated Spring 2023 ... Hwanwoo Kim, graduated Spring 2024 ... Nathan Waniorek, graduated Spring 2026 ... Jiaheng Chen (current student). Wenwen Li (current student). PhD Students, Department of Statistics, University of Chicago Omar Al-Ghattas, graduated Spring 2025.'),
    'stephens': ('https://stephenslab.uchicago.edu/people.html', '2026-11-04',
                 'Previous personnel ... Dongyue Xie , Graduate student (2019-2023) ... Yuxin Zou , Graduate student (2018-2022); current graduate students Junming Guan, Karl Tayeb, Annie Xie (no Lin Chen, no Zihao Wang in any year)'),
    'lim': ('https://www.stat.uchicago.edu/~lekheng/work/people.html', '2026-11-03',
            'PhD students Thomas Rongbiao Wang (Computational and Applied Mathematics): 2022- ; Zehua Lai (Computational and Applied Mathematics): 2018-2023 ; Zhen Dai (Computational and Applied Mathematics): 2018-2023 ; Aaron Chen (CAM, joint with Tingran Gao) ; Gregory Naitzat (Statistics) ... (no Yian Chen)'),
    'zli': ('https://zhiyuanli.ttic.edu/People/', '2026-11-03 (Wayback 20250717064733 and 20260613003457)',
            'PhD Students Shuo Xie (TTIC, 3rd year) ... Beining Wu (Uchicago Stats, 3rd year) ...'),
    'tulsiani': ('https://home.ttic.edu/~madhurt/', '2026-11-03',
                 'Alumni June Wu (U. Chicago, co-advised with Shmuel Weinberger) . PhD 2025.'),
    'srebro': ('https://nati.ttic.edu/group.html', '2026-11-03 (Wayback 20260210232918)',
               'Alumni Former PhD Students Lijia Zhou (Quantitative Researcher, Chicago Trading Company) Thesis: A Statistical Learning Theory for Models with High Complexity (April 2023)'),
    'ma': ('https://congma1028.github.io/group.html', '2026-11-04',
           'Alumni Hugh (Rong) Jiang (now at Fireworks AI) Yuepeng Yang (now postdoc, UPenn) Yu Gui (co-advised with Rina Foygel Barber, now postdoc, UPenn)'),
    'donnat': ('https://signal-lab-uchicago.github.io/people.html', '2026-11-04',
               'Graduate Students Yeo Jin Jung PhD Student ... Yating Liu PhD Student Topic Modeling with sparsity. Zixuan Wu PhD Student Efficient sparse CCA ...'),
    'kondor': ('http://people.cs.uchicago.edu/~risi/', '2026-08-20 (Wayback capture, stored 2026-11-03)',
               'Su Hyeong Lee (CCAM PhD, 4th year)  [on Risi Kondor group page, not on Tian Li\'s]'),
    'park': ('https://kihopark.github.io/', '2026-11-04',
             'I recently received my PhD in Statistics from the University of Chicago, where I was advised by Victor Veitch .'),
    'nek': ('https://peter-nekrasov.github.io/', '2026-11-04',
            'I recently completed my PhD in Computational and Applied Mathematics at the University of Chicago, under the supervision of Jeremy Hoskins and Douglas MacAyeal.'),
    'senna': ('https://senna1128.github.io/uploads/CV_SenNa.pdf', '2026-11-04',
              'Ph.D. in Statistics ... Thesis: Towards Solving Long-Horizon Nonlinear Dynamic Programs ... Advisors: Prof. Mihai Anitescu and Prof. Mladen Kolar'),
    'xiao': ('https://xavierxiao.github.io/files/CV_small.pdf', '2026-11-04',
             'The University of Chicago July 2018-Present Supervised by Professor Yali Amit'),
    'bonner': ('https://sohamb01.github.io/', '2026-11-04',
               'I earned my PhD in the Department of Statistics at the University of Chicago , where I was advised by Prof. Wei Biao Wu .'),
    'kotekal': ('https://skotekal.github.io', '2026-11-04',
                'I obtained my Ph.D. from the Department of Statistics at the University of Chicago in June 2025. My advisor was Chao Gao.'),
    'oag': ('https://sites.google.com/view/omaralghattas', '2026-11-04',
            'I completed my PhD in Statistics at the University of Chicago under the supervision of Daniel Sanz-Alonso .'),
    'ygw': ('https://sites.google.com/view/yuguanwang/home', '2026-11-04',
            'I was extremely fortunate to have Yuehaw Khoo and Jeremy Hoskins as my Ph.D. advisors. ... Ph.D., University of Chicago, 2026.'),
    'liang': ('https://tyliang.github.io/Liang-CV.pdf', '2026-11-04',
              'Mentoring & Advising 2018- Doctoral Students. ... YoonHaeng Hur [2025, PhD, UChicago Stat -> Postdoc, Columbia] ... Xialiang Dou [2021, PhD, UChicago Stat -> Two Sigma].'),
    'cs_liu': ('https://people.cs.uchicago.edu/~shanlu/', '2026-11-03 (Wayback)',
               'Students: Jiayi Yao, Yuhan Liu, Former Students: ... [a CS PhD student; the Statistics roster\'s Yuhan Liu is the Statistics PhD alumnus "Yuhan Philip Liu" (stat.uchicago.edu/alumni/phd-alumni/, 2024, Quantitative Researcher, Cubist Systematic Strategies)]'),
    'amit_alumni': ('https://stat.uchicago.edu/alumni/phd-alumni/', '2026-11-03 (Wayback)',
                    'lists PhD alumni by year without advisers (used for namesake and status checks only)'),
}

# (index in the source rows) -> (verdict, basis, [source keys], note)
V = {
    0: ('true', 'listing', ['barber'], 'PhD student on Barber group page; alumni PhD 2026'),
    1: ('not', 'other-adviser', ['willett'], 'Stevens is Willett\'s member; Chard is an Argonne collaborator (alumni list: Argonne)'),
    2: ('true', 'listing', ['willett'], 'also Willett group page 2019 and 2021 captures: "Statistics grad student"'),
    3: ('true', 'listing', ['zli'], ''),
    4: ('true', 'listing', ['barber'], 'co-advised with Mladen Kolar'),
    5: ('true', 'listing', ['stephens'], ''),
    6: ('unsettled', 'none', [], 'dissertation defense listed by the department (no adviser named); no group or homepage found'),
    7: ('true', 'listing', ['barber'], 'co-advised with Chao Gao: true for Gao and for Barber'),
    8: ('true', 'listing', ['barber'], ''),
    9: ('unsettled', 'none', [], 'no page names Zhao\'s adviser'),
    10: ('true', 'listing', ['sanz'], ''),
    11: ('true', 'listing', ['sanz'], ''),
    12: ('not', 'other-adviser', ['sanz'], 'Chen is Sanz-Alonso\'s CAM student; Jiang (CS) co-authored two papers'),
    13: ('unsettled', 'none', [], 'dissertation proposal talk (Nov 2025) on tensor models fits Schein, but no page names the adviser'),
    14: ('true', 'listing', ['tulsiani'], 'on Tulsiani\'s page, co-advised with Weinberger; PhD 2025'),
    15: ('true', 'listing', ['park'], ''),
    16: ('true', 'listing', ['srebro'], 'thesis 2023'),
    17: ('not', 'absence', ['stephens'], 'Stephens\' personnel list names every graduate student 2003-present and has no Lin Chen'),
    18: ('unsettled', 'none', [], 'dissertation defense in Statistics (Apr, no year/adviser shown); no Nicolae group page'),
    19: ('unsettled', 'none', [], 'Bal has no student list; Frazier joined CAM as MS 2024'),
    20: ('not', 'other-adviser', ['willett', 'sanz'], 'Adrian is on Willett\'s former-members list and absent from Sanz-Alonso\'s mentoring page'),
    21: ('true', 'listing', ['willett'], ''),
    22: ('true', 'listing', ['sanz'], ''),
    23: ('true', 'listing', ['sanz', 'oag'], ''),
    24: ('true', 'listing', ['nek'], 'co-supervised with Douglas MacAyeal'),
    25: ('unsettled', 'none', [], 'CAM 2020-2025 per roster captures; no adviser line found'),
    26: ('unsettled', 'none', [], 'dissertation defense "Full Ranking" listed (no adviser named)'),
    27: ('unsettled', 'none', [], 'co-author of Xiao (Amit student) but no own page found'),
    28: ('true', 'listing', ['barber'], ''),
    29: ('true', 'listing', ['willett', 'barber'], 'co-advised by Barber and Willett'),
    30: ('true', 'listing', ['barber'], ''),
    31: ('true', 'listing', ['ma'], 'listed as "Hugh (Rong) Jiang" (alias match; roster Rong Jiang is a CAM student 2023-2026)'),
    32: ('true', 'listing', ['barber'], 'PhD 2026, Computational & Applied Math'),
    33: ('true', 'listing', ['sanz'], ''),
    34: ('true', 'listing', ['senna'], 'co-advised with Mladen Kolar'),
    35: ('true', 'listing', ['bonner'], ''),
    36: ('unsettled', 'none', [], 'no student list on Bal\'s page'),
    37: ('unsettled', 'none', [], 'co-author of Hoskins; no adviser line found'),
    38: ('not', 'other-adviser', ['kondor'], 'listed on Kondor\'s group page, not Li\'s'),
    39: ('true', 'listing', ['kotekal'], ''),
    40: ('true', 'listing', ['willett'], '"Sue Parkinson" on Willett\'s page; Liang\'s CV lists a 2026 CAM committee seat for her'),
    41: ('true', 'listing', ['barber'], 'co-advised with Wei-Biao Wu: true for Wu and for Barber'),
    42: ('not', 'other-adviser', ['liang'], 'Liang\'s CV lists Dou as his doctoral student'),
    43: ('true', 'listing', ['liang'], ''),
    44: ('unsettled', 'none', [], 'roster 2025 only; no page'),
    45: ('true', 'listing', ['donnat'], 'also lab news 2026-10-27: "Yating successfully defended her PhD thesis"'),
    46: ('true', 'listing', ['donnat'], ''),
    47: ('unsettled', 'none', [], 'Stats PhD 2024 (TikTok); no adviser page'),
    48: ('not', 'absence', ['lim'], 'Lim\'s page lists all his CAM and Statistics PhD students 2013-present; no Yian Chen'),
    49: ('unsettled', 'none', [], 'no Khoo student list'),
    50: ('not', 'absence', [], 'absent from every stored Livescu capture; roster student is a CAM PhD (thesis 2026 "Fast Numerical Linear Algebra For Generative Modeling")'),
    51: ('unsettled', 'none', [], 'CAM PhD 2026 (cam.uchicago.edu/people/profile/yifan-peng/, 2026-11-04: thesis "Fast Numerical Linear Algebra For Generative Modeling"); no page names the adviser'),
    52: ('true', 'listing', ['barber'], ''),
    53: ('unsettled', 'other-adviser', ['liang'], 'Liang\'s CV lists Hur as his doctoral student; Khoo co-authored 3 papers; co-advising not shown'),
    54: ('unsettled', 'none', [], 'no page found'),
    55: ('true', 'listing', ['ma', 'barber'], 'co-advised with Barber'),
    56: ('true', 'listing', ['barber', 'ma'], ''),
    57: ('true', 'listing', ['ma'], ''),
    58: ('true', 'listing', ['ygw'], 'co-advised with Hoskins'),
    59: ('not', 'namesake', ['cs_liu'], 'the papers are the CS PhD student Yuhan Liu (Lu / Jiang lab pages); the Statistics roster entry is Yuhan Philip Liu'),
    60: ('not', 'namesake', ['cs_liu'], 'CS namesake (Junchen Jiang page: "Yuhan Liu (with Shan Lu)")'),
    61: ('not', 'namesake', ['cs_liu'], 'CS namesake'),
    62: ('not', 'namesake', ['cs_liu'], 'CS namesake'),
    63: ('true', 'listing', ['sanz'], ''),
    64: ('not', 'other-adviser', ['sanz'], 'Chen is Sanz-Alonso\'s student; no Willett listing'),
    65: ('unsettled', 'none', [], 'no group page found for Xu'),
    66: ('true', 'listing', ['stephens'], ''),
    67: ('true', 'listing', ['lim'], ''),
    68: ('true', 'listing', ['lim'], ''),
    69: ('not', 'other-adviser', ['lim', 'srebro'], 'Dai is Lim\'s student; absent from every Srebro group capture'),
    70: ('true', 'listing', ['xiao'], 'own CV: supervised by Amit'),
    71: ('not', 'absence', ['stephens'], 'absent from Stephens\' complete personnel list'),
    72: ('unsettled', 'none', [], 'Veitch has no group page'),
    73: ('true', 'listing', ['donnat'], ''),
    74: ('unsettled', 'none', [], 'no Wu student list; Wu\'s papers page only'),
}


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0, c - h), 3), round(min(1, c + h), 3))


def build():
    rows = json.load(open(SRC))['rows']
    out = []
    for i, r in enumerate(rows):
        v, basis, keys, note = V[i]
        out.append(dict(index=i, student=r['student'], pi=r['pi'], roster_years=r['roster_years'], joint_papers=r['joint_papers'],
                        pi_last=r['pi_last'], old_rule=r['old_rule'], r_star=r['r_star'], verdict=v, basis=basis, note=note,
                        sources=[dict(url=S[k][0], captured=S[k][1], quote=S[k][2]) for k in keys]))
    return out


def metrics(out):
    res = {}
    rules = {
        'old (PI last, or 2+ papers)': lambda r: r['old_rule'],
        'R* (3+ papers, or 2+ with PI last)': lambda r: r['r_star'],
        'PI last on 1+ paper': lambda r: r['pi_last'] >= 1,
        '3+ papers': lambda r: r['joint_papers'] >= 3,
        '3+ papers or PI last on 2+': lambda r: r['joint_papers'] >= 3 or r['pi_last'] >= 2,
        '2+ papers and PI last 1+': lambda r: r['joint_papers'] >= 2 and r['pi_last'] >= 1,
    }
    # rule 3: R* minus pairs whose student has a different named adviser / namesake (needs the evidence: oracle upper bound)
    rules['R* minus other-adviser/namesake evidence'] = lambda r: r['r_star'] and r['basis'] not in ('other-adviser', 'namesake')
    for scope, keep in (('all settled', lambda r: r['verdict'] in ('true', 'not')),
                        ('listing/other-adviser/namesake only (no absence verdicts)',
                         lambda r: r['verdict'] in ('true', 'not') and r['basis'] != 'absence')):
        S_ = [r for r in out if keep(r)]
        T = sum(1 for r in S_ if r['verdict'] == 'true')
        tab = {}
        for name, f in rules.items():
            kept = [r for r in S_ if f(r)]
            tp = sum(1 for r in kept if r['verdict'] == 'true')
            tab[name] = dict(kept=len(kept), tp=tp, fp=len(kept) - tp, fn=T - tp, precision=round(tp / len(kept), 3) if kept else None,
                             precision_ci=wilson(tp, len(kept)), recall=round(tp / T, 3), recall_ci=wilson(tp, T))
        res[scope] = dict(n=len(S_), true=T, rules=tab)
    return res


if __name__ == '__main__':
    out = build()
    cnt = {k: sum(1 for r in out if r['verdict'] == k) for k in ('true', 'not', 'unsettled')}
    m = metrics(out)
    OUT.write_text(json.dumps(dict(date='2026-11-04', counts=cnt, rules_note=__doc__.split('\n')[7:9], pairs=out, metrics=m), indent=1, ensure_ascii=False))
    print(cnt)
    for scope, d in m.items():
        print('##', scope, 'n', d['n'], 'true', d['true'])
        for k, v in d['rules'].items():
            print(f"  {k:45s} kept {v['kept']:2d} tp {v['tp']:2d} fp {v['fp']:2d} fn {v['fn']:2d} P {v['precision']} {v['precision_ci']} R {v['recall']} {v['recall_ci']}")
