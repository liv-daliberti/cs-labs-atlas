"""Figures of the three design layers (matplotlib; the py310 env). Palette, type and the ChatGPT marker follow study_figures.py. Series end at 2025; no 2026.
usage: study_design_figures.py [--id 2026-11-08]   -> <results>/designs/figures/fig7..fig11 *.png and tables/headline.md
"""
import argparse

import pandas as pd

import study_common as C
import study_figures as F

plt = F.plt
BLUE, ORANGE, GREEN, PURPLE, MUTED = F.BLUE, F.ORANGE, F.GREEN, F.PURPLE, F.MUTED
PCT = {'heavy_main': 100, 'abs_flag': 100, 'within_lab_distance': 1, 'school_centroid_distance': 1}
LAB = {'heavy_main': 'Heavy-AI main body (pts)', 'abs_flag': 'Abstract flag (pts)', 'within_lab_distance': 'Within-lab distance', 'school_centroid_distance': 'Distance to school centroid'}


def ev_axis(ax):
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.axvline(2022.5, color=MUTED, lw=0.8, ls=':')
    ax.set_xticks(range(2016, 2026)); ax.set_xticklabels([str(y)[2:] for y in range(2016, 2026)])


def fig_panel_event(T, out):
    e = pd.read_csv(T / 'panel_fe_event.csv')
    e = e[(e['sample'] == 'all') & (e.brk == 'real')]
    fig, ax = plt.subplots(1, 4, figsize=(13, 3.1))
    for a, o in zip(ax, PCT):
        k = PCT[o]
        d = e[(e.outcome == o) & (e.spec == 'S3_event') & e.term.str.match(r'y\d{4}$')].copy()
        d['year'] = d.term.str[1:].astype(int)
        d = pd.concat([d, pd.DataFrame({'year': [2022], 'est': [0.0], 'lo': [0.0], 'hi': [0.0]})]).sort_values('year')
        a.plot(d.year, k * d.est, color=BLUE, marker='o', ms=3, lw=1.4, label='year effects, PI FE (2022 = 0)')
        a.fill_between(d.year, k * d.lo, k * d.hi, color=BLUE, alpha=0.18, lw=0)
        s2 = e[(e.outcome == o) & (e.spec == 'S2_pi_trend_event')].copy()
        s2['year'] = s2.term.str[1:].astype(int)
        a.errorbar(s2.year + 0.12, k * s2.est, yerr=[k * (s2.est - s2.lo), k * (s2.hi - s2.est)], fmt='s', color=ORANGE, ms=4, lw=1.1, capsize=2, label='departure from PI-specific pre-trend')
        p = e[(e.outcome == o) & (e.term == 'pretrend_wald')]['p']
        a.set_title(LAB[o] + (f'\npre-trend p={p.iloc[0]:.3f}' if len(p) else ''), fontsize=8.5)
        ev_axis(a)
    ax[0].legend(frameon=False, fontsize=6.5, loc='upper left')
    fig.tight_layout(); fig.savefig(out / 'fig7_design1_panel_event.png', dpi=170); plt.close(fig)


def fig_panel_forest(T, out):
    t = pd.read_csv(T / 'panel_fe.csv')
    rows = [('S0 naive: PI FE + post', 'all', 'real', 'S0_pi_fe', BLUE), ('S1 common trend', 'all', 'real', 'S1_common_trend', BLUE),
            ('S2 PI-specific trend', 'all', 'real', 'S2_pi_trend', BLUE), ('S2, both periods', 'balanced1', 'real', 'S2_pi_trend', GREEN),
            ('S2, >=3 per period', 'balanced3', 'real', 'S2_pi_trend', GREEN), ('S2, excl. harvard/jhu/washu', 'excl_partial', 'real', 'S2_pi_trend', GREEN),
            ('placebo 2020, S0', 'all', 'fake2020', 'S0_pi_fe', MUTED), ('placebo 2020, S2', 'all', 'fake2020', 'S2_pi_trend', MUTED)]
    fig, ax = plt.subplots(1, 4, figsize=(13, 3.4))
    for a, o in zip(ax, PCT):
        k = PCT[o]
        ys, labs = [], []
        for i, (lab, smp, brk, spec, col) in enumerate(rows):
            r = t[(t.outcome == o) & (t['sample'] == smp) & (t.brk == brk) & (t.spec == spec) & t.term.isin(['post', 'post_avg'])]
            if r.empty:
                continue
            r = r.iloc[0]
            y = len(rows) - i
            a.errorbar(k * r.est, y, xerr=[[k * (r.est - r.lo)], [k * (r.hi - r.est)]], fmt='o', color=col, ms=4, lw=1.2, capsize=2)
            ys.append(y); labs.append(lab)
        a.axvline(0, color=MUTED, lw=0.8); a.set_yticks(ys); a.set_yticklabels(labs if a is ax[0] else [''] * len(ys)); a.set_title(LAB[o], fontsize=8.5)
    fig.tight_layout(); fig.savefig(out / 'fig8_design1_forest.png', dpi=170); plt.close(fig)


def fig_exposure_event(T, out):
    e = pd.read_csv(T / 'exposure_event.csv')
    d = pd.read_csv(T / 'exposure_did.csv')
    exps = ['style_distance', 'kobak_distance', 'lang_share']
    fig, ax = plt.subplots(2, 3, figsize=(11.5, 5.4), sharex=True)
    for i, o in enumerate(('heavy_main', 'abs_flag')):
        for j, x in enumerate(exps):
            a = ax[i, j]
            for cfg, col, dx in (('main', BLUE, -0.1), ('crossfit', ORANGE, 0.1)):
                r = e[(e.outcome == o) & (e.exposure == x) & (e.cfg == cfg)]
                r = pd.concat([r, pd.DataFrame({'year': [2022], 'est': [0.0], 'lo': [0.0], 'hi': [0.0]})]).sort_values('year')
                a.errorbar(r.year + dx, 100 * r.est, yerr=[100 * (r.est - r.lo), 100 * (r.hi - r.est)], fmt='o-', color=col, ms=3, lw=1, capsize=1.5, label=cfg.replace('crossfit', 'cross-fit exposure'))
            p = d[(d.outcome == o) & (d.exposure == x) & (d.cfg == 'main') & (d['sample'] == 'all') & (d.fe == 'school_year')]['pretrend_p']
            a.set_title(f'{o.replace("_", " ")} x {x.replace("_", " ")}' + (f'\npre-trend p={p.iloc[0]:.2f}' if len(p) else ''), fontsize=8)
            ev_axis(a)
            if i == 1:
                a.set_xlabel('year')
            if j == 0:
                a.set_ylabel('points per SD of exposure')
    ax[0, 0].legend(frameon=False, fontsize=6.5)
    fig.tight_layout(); fig.savefig(out / 'fig9_design2_event.png', dpi=170); plt.close(fig)


def fig_exposure_forest(T, out):
    d = pd.read_csv(T / 'exposure_did.csv')
    exps = ['style_distance', 'kobak_distance', 'lang_share', 'lang_share_wide', 'lang_share_team']
    specs = [('school x year FE', 'main', 'all', 'school_year', BLUE), ('cross-fit exposure', 'crossfit', 'all', 'school_year', BLUE), ('year FE only', 'main', 'all', 'year', GREEN),
             ('+ subfield x year', 'main', 'all', 'school_topic_year', GREEN), ('excl. harvard/jhu/washu', 'main', 'excl_partial', 'school_year', GREEN),
             ('placebo 2020', 'placebo2020', 'all', 'school_year', MUTED)]
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.6), sharey=True)
    for a, o in zip(ax, ('heavy_main', 'abs_flag')):
        y = 0
        yt, yl = [], []
        for x in exps[::-1]:
            for lab, cfg, smp, fe, col in specs[::-1]:
                r = d[(d.outcome == o) & (d.exposure == x) & (d.cfg == cfg) & (d['sample'] == smp) & (d.fe == fe)]
                y += 1
                if r.empty:
                    continue
                r = r.iloc[0]
                a.errorbar(100 * r.est, y, xerr=[[100 * (r.est - r.lo)], [100 * (r.hi - r.est)]], fmt='o', color=col, ms=3.5, lw=1.1, capsize=1.5)
                yt.append(y); yl.append(f'{x.replace("_", " ")}: {lab}')
            y += 1
        a.axvline(0, color=MUTED, lw=0.8); a.set_yticks(yt); a.set_yticklabels(yl, fontsize=6.3); a.set_title(LAB[o] + ' per SD of exposure, post 2023 x exposure', fontsize=8.5)
    fig.tight_layout(); fig.savefig(out / 'fig10_design2_forest.png', dpi=170); plt.close(fig)


def fig_revision(T, out):
    e = pd.read_csv(T / 'revision_effects.csv')
    e = e[(e['sample'] == 'all') & (e.outcome == 'flagged_share') & (e.kind.isin(['A', 'S']))]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
    items = [('pre_post - pre_pre', 'real', 'v1 before, final after minus both before', BLUE), ('post_post - pre_pre', 'real', 'both after minus both before', GREEN),
             ('post_post - pre_post', 'real', 'both after minus v1 before/final after', PURPLE), ('fake_cross - fake_pre', 'fake2020', 'placebo: fake break 2020', MUTED)]
    for a, scope in zip(ax, ('main', 'main_appendix')):
        y = 0
        yt, yl = [], []
        for kind in ('S', 'A'):
            for lab_c, design, lab, col in items[::-1]:
                r = e[(e.scope == scope) & (e.kind == kind) & (e.contrast == lab_c) & (e.design == design)]
                y += 1
                if r.empty:
                    continue
                r = r.iloc[0]
                a.errorbar(100 * r.est, y, xerr=[[100 * (r.est - r.lo)], [100 * (r.hi - r.est)]], fmt='o', color=col, ms=4, lw=1.2, capsize=2)
                yt.append(y); yl.append(f'kind {kind}: {lab}')
            y += 1
        a.axvline(0, color=MUTED, lw=0.8); a.set_yticks(yt); a.set_yticklabels(yl, fontsize=6.8)
        a.set_title(('Main body' if scope == 'main' else 'Main body + appendix') + ': change in flagged share, final minus v1 (pts)', fontsize=8.5)
    fig.tight_layout(); fig.savefig(out / 'fig11_design3_revision.png', dpi=170); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-08')
    a = ap.parse_args()
    res = C.results_dir(a.id) / 'designs'
    T = res / 'tables'
    out = res / 'figures'
    out.mkdir(exist_ok=True)
    for fn in (fig_panel_event, fig_panel_forest, fig_exposure_event, fig_exposure_forest, fig_revision):
        try:
            fn(T, out)
            print(fn.__name__, 'ok')
        except FileNotFoundError as e:
            print(fn.__name__, 'skipped', e.filename)


if __name__ == '__main__':
    main()
