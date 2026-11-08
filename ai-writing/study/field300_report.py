"""Field-300 report: figures and FIELD300.md for the owner, generated from the tables (no hand-edited numbers).

  field300_report.py [--models specter2_proximity,scincl]  -> results/field300-2026-11-08/{figures/*.png, FIELD300.md}
"""
import argparse
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import field300_common as F  # noqa: E402

BLUE, ORANGE, GREEN, AMBER, PINK, PURPLE = '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#8a5cc2'
INK, INK2, MUTED, GRID, SURF = '#1d2a33', '#46525a', '#68747c', '#e3e5e0', '#fcfcfb'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.facecolor': SURF, 'figure.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
                     'axes.titlecolor': INK, 'legend.labelcolor': INK2, 'axes.spines.top': False, 'axes.spines.right': False})

R = F.results_dir()
T = R / 'tables'
FIG = R / 'figures'


def rd(name):
    """One table, or (name with a * wildcard) the concatenation of all matching files."""
    fs = sorted(T.glob(name)) if '*' in name else ([T / name] if (T / name).exists() else [])
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def fmt(e, lo, hi, scale=1.0, nd=2, sign=True):
    if not np.isfinite(e):
        return 'n/a'
    f = f'{{:+.{nd}f}}' if sign else f'{{:.{nd}f}}'
    return f'{f.format(e * scale)} [{f.format(lo * scale)}, {f.format(hi * scale)}]'


def row(con, contrast):
    r = con[con.contrast == contrast]
    return r.iloc[0] if len(r) else None


def verdict(post, plc, direction):
    """'toward sameness' / 'toward diversity' / 'no change detectable', and whether the placebo (pre-period drift) is of the same sign and size."""
    if post is None or not np.isfinite(post.est):
        return 'not computed'
    if direction == 0:
        return 'rose' if post.lo > 0 else ('fell' if post.hi < 0 else 'no change detectable')
    if post.lo <= 0 <= post.hi:
        return 'no change detectable'
    d = np.sign(post.est) * direction
    word = 'toward sameness' if d > 0 else 'toward diversity'
    if plc is not None and np.isfinite(plc.est) and not (plc.lo <= 0 <= plc.hi) and np.sign(plc.est) == np.sign(post.est) and abs(plc.est) >= abs(post.est):
        word += ' (continues the pre-2023 drift)'
    return word


def headline_rows():
    """[(layer, measure, direction, scale, nd, unit, contrasts DataFrame)] in report order."""
    out = []

    def add(layer, name, con, direction, scale=1.0, nd=3, unit=''):
        if len(con):
            out.append((layer, name, direction, scale, nd, unit, con))
    c = rd('f300_ai_contrasts.csv')
    add('AI share', 'abstract flagged (v1 detector)', c[(c.measure == 'abs_flag') & (c.counting == 'full')], 0, 100, 2, 'pp')
    c = rd('f300_llm_contrasts.csv')
    add('Topics', 'papers on LLM topics (title/abstract regex)', c[c.counting == 'full'], 0, 100, 2, 'pp')
    c = rd('f300_topics_contrasts.csv')
    for m, nm, dr in (('entropy_subfield_m50', 'institution topic entropy, OpenAlex subfield (bits, 50 papers)', -1), ('entropy_topic_m100', 'institution topic entropy, OpenAlex topic (bits, 100 papers)', -1),
                      ('jsd_subfield_m50', 'cross-institution topic JSD, subfield (bits)', -1), ('jsd_topic_m100', 'cross-institution topic JSD, topic (bits)', -1)):
        add('Topics', nm, c[(c.measure == m)], dr, 1, 4)
    for model in MODELS:
        c = rd(f'f300_embed_{model}_contrasts.csv')
        for lv, nm in (('within', 'within institution'), ('cross', 'across institutions')):
            add('Embeddings', f'{nm} mean pairwise distance ({model})', c[c.measure == f'emb_{lv}_{model}_raw'], -1, 1, 4)
        if model == 'specter2_proximity':
            for lv, nm in (('within', 'within institution'), ('cross', 'across institutions')):
                add('Embeddings', f'{nm}, topic-residual ({model})', c[c.measure == f'emb_{lv}_{model}_topic_residual'], -1, 1, 4)
    for s, nm in (('journal', 'journal papers, primary'), ('refs10', 'papers with >= 10 references, secondary')):
        c = rd(f'f300_overlap_{s}_ALL-tier-english-region-size_contrasts.csv')
        if len(c):
            add('References', f'Jaccard ratio obs/null across institutions ({nm})', c[(c.scope == 'ALL') & (c.measure == 'ref_jac_ratio') & (c.pairs == 'across')], 1, 1, 4)
            add('References', f'bibliographic-coupling cosine ratio obs/null ({nm})', c[(c.scope == 'ALL') & (c.measure == 'ref_cos_ratio') & (c.pairs == 'across')], 1, 1, 4)
        c = rd(f'f300_concentration_{s}_*_contrasts.csv')
        if len(c):
            add('Citations', f'share of references on the top 1% of cited works ({nm})', c[(c.scope == 'ALL') & (c.measure == 'cite_top1pct') & (c.variant == 'full')], 1, 1, 4)
            add('Citations', f'Gini of cited-work frequency ({nm})', c[(c.scope == 'ALL') & (c.measure == 'cite_gini') & (c.variant == 'full')], 1, 1, 4)
    c = rd('f300_bench_ALL-tier-english_contrasts.csv')
    if len(c):
        for g, nm in (('bench_data', 'benchmarks and datasets'), ('meth', 'methods')):
            for k, kn, dr in (('hhi', 'HHI of the entry mix', 1), ('entropy', 'entropy of the entry mix (bits)', -1), ('top5_cond', 'share of institutions using a top-5 entry, among users', 1)):
                add('Benchmarks', f'{kn}, {nm}', c[(c.scope == 'ALL') & (c.measure == f'bench_{g}_{k}')], dr, 1, 4)
    return out


MODELS = ['specter2_proximity', 'scincl']


def headline_table():
    lines = ['| layer | measure | pre | post | post minus pre [95% CI] | placebo 2019-21 minus 2016-18 [95% CI] | verdict |', '|---|---|---|---|---|---|---|']
    for layer, name, direction, scale, nd, unit, con in headline_rows():
        p = row(con, 'post_minus_pre')
        pl = row(con, 'placebo_2019_21_minus_2016_18')
        if p is None:
            continue
        u = f' {unit}' if unit else ''
        lines.append(f'| {layer} | {name} | {p.pre * scale:.{nd}f} | {p.post * scale:.{nd}f} | {fmt(p.est, p.lo, p.hi, scale, nd)}{u} | '
                     f'{fmt(pl.est, pl.lo, pl.hi, scale, nd) if pl is not None else "n/a"}{u} | {verdict(p, pl, direction)} |')
    return '\n'.join(lines)


def reading():
    """The headline verdicts grouped, generated from the table by the fixed rule of verdict() (no hand-written numbers)."""
    groups = {}
    for layer, name, direction, scale, nd, unit, con in headline_rows():
        p, pl = row(con, 'post_minus_pre'), row(con, 'placebo_2019_21_minus_2016_18')
        if p is None:
            continue
        groups.setdefault(verdict(p, pl, direction), []).append(f'{layer}: {name}')
    return '\n'.join(f'- **{v}** ({len(xs)}): ' + '; '.join(xs) for v, xs in sorted(groups.items(), key=lambda kv: -len(kv[1])))


def series_fig(ax, s, color, label, scale=1.0):
    s = s[s.year <= F.LAST]
    ax.plot(s.year, s.est * scale, color=color, lw=1.6, marker='o', ms=3, label=label)
    ax.fill_between(s.year, s.lo * scale, s.hi * scale, color=color, alpha=0.18, lw=0)


def chat(ax):
    ax.axvline(2022.92, color=MUTED, lw=0.8, ls=':')
    ax.set_xticks(range(2016, 2026))
    ax.set_xticklabels([str(y)[2:] for y in range(2016, 2026)])


def fig_series():
    FIG.mkdir(parents=True, exist_ok=True)
    panels = []
    s = rd('f300_ai_series.csv')
    if len(s):
        panels.append(('Abstract flagged by the v1 detector (%)', [(s[(s.measure == 'abs_flag') & (s.counting == 'full')], BLUE, 'all 300', 100)]))
    s = rd('f300_llm_series.csv')
    if len(s):
        panels.append(('Papers on LLM topics (%)', [(s[s.counting == 'full'], ORANGE, 'all 300', 100)]))
    s = rd('f300_topics_series.csv')
    if len(s):
        panels.append(('Topic entropy per institution-year (bits)', [(s[s.measure == 'entropy_subfield_m50'], GREEN, 'subfield, 50 papers', 1), (s[s.measure == 'entropy_topic_m100'], PURPLE, 'topic, 100 papers', 1)]))
        panels.append(('Cross-institution topic JSD (bits)', [(s[s.measure == 'jsd_subfield_m50'], GREEN, 'subfield', 1), (s[s.measure == 'jsd_topic_m100'], PURPLE, 'topic', 1)]))
    for model, c in zip(MODELS, (BLUE, ORANGE)):
        s = rd(f'f300_embed_{model}_series.csv')
        if len(s):
            panels.append((f'Embedding distance, {model}', [(s[s.measure == f'emb_within_{model}_raw'], c, 'within institution', 1), (s[s.measure == f'emb_cross_{model}_raw'], GREEN, 'across institutions', 1)]))
    s = rd('f300_overlap_journal_ALL-tier-english-region-size_series.csv')
    if len(s):
        panels.append(('Reference overlap, obs/null (journal papers)', [(s[(s.scope == 'ALL') & (s.measure == 'ref_jac_ratio') & (s.pairs == 'across')], BLUE, 'Jaccard', 1), (s[(s.scope == 'ALL') & (s.measure == 'ref_cos_ratio') & (s.pairs == 'across')], ORANGE, 'coupling cosine', 1)]))
    s = rd('f300_concentration_journal_*_series.csv')
    if len(s):
        panels.append(('Citation concentration (journal papers)', [(s[(s.scope == 'ALL') & (s.measure == 'cite_top1pct') & (s.variant == 'full')], BLUE, 'top-1% share', 1)]))
    s = rd('f300_bench_ALL-tier-english_series.csv')
    if len(s):
        panels.append(('Benchmark / dataset entry mix', [(s[(s.scope == 'ALL') & (s.measure == 'bench_bench_data_entropy')], GREEN, 'entropy (bits)', 1)]))
    if not panels:
        return []
    n = len(panels)
    cols = 3
    rows = (n + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(11, 3.0 * rows), squeeze=False)
    for ax, (title, ss) in zip(axs.ravel(), panels):
        for d, c, lab, sc in ss:
            if len(d):
                series_fig(ax, d, c, lab, sc)
        ax.set_title(title, fontsize=8.5)
        chat(ax)
        if len(ss) > 1:
            ax.legend(frameon=False, fontsize=7)
    for ax in axs.ravel()[n:]:
        ax.axis('off')
    fig.tight_layout()
    fig.savefig(FIG / 'fig1_yearly_series.png', dpi=160)
    plt.close(fig)
    return ['fig1_yearly_series.png']


def fig_hetero():
    g = rd('f300_hetero_groups.csv')
    if not len(g):
        return []
    outs = [('abs_flag', 'Abstract flagged, change (pp)', 100), ('llm_topic', 'LLM-topic share, change (pp)', 100),
            ('emb_within_specter2_proximity_raw', 'Within-institution distance, change', 1), ('emb_cross_specter2_proximity_raw', 'Across-institution distance (within group), change', 1)]
    fig, axs = plt.subplots(1, len(outs), figsize=(12, 6.2), sharey=True)
    labels = None
    for ax, (m, t, sc) in zip(axs, outs):
        d = g[(g.measure == m) & g.dimension.isin(['tier', 'english', 'region', 'size'])].reset_index(drop=True)
        if labels is None:
            labels = [f'{a}: {b}' for a, b in zip(d.dimension, d.group)]
        y = np.arange(len(d))[::-1]
        ax.errorbar(d.change * sc, y, xerr=[(d.change - d.lo) * sc, (d.hi - d.change) * sc], fmt='o', color=BLUE, ms=3.5, lw=1.2)
        ax.scatter(d.placebo * sc, y, marker='x', color=MUTED, s=18, label='placebo')
        ax.axvline(0, color=MUTED, lw=0.8)
        ax.set_title(t, fontsize=8)
    axs[0].set_yticks(np.arange(len(labels))[::-1])
    axs[0].set_yticklabels(labels, fontsize=7)
    axs[0].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / 'fig2_heterogeneity.png', dpi=160)
    plt.close(fig)
    return ['fig2_heterogeneity.png']


def size_table():
    f = F.work_dir() / 'corpus' / 'counts_by_year.csv'
    if not f.exists():
        return '(corpus counts not found)'
    d = pd.read_csv(f)
    cols = ['year', 'papers', 'cs_primary', 'venue_only', 'abstract50', 'english_abstract50', 'journal', 'with_refs', 'not_cs_but_cs_secondary_topic', 'not_cs_other']
    d = d[[c for c in cols if c in d.columns]]
    head = '| ' + ' | '.join(d.columns) + ' |\n|' + '---|' * len(d.columns)
    body = '\n'.join('| ' + ' | '.join(str(int(v)) if isinstance(v, (int, float, np.integer, np.floating)) and c != 'year' else str(v) for c, v in zip(d.columns, r)) + ' |' for r in d.itertuples(index=False))
    return head + '\n' + body


def hetero_tables():
    g = rd('f300_hetero_groups.csv')
    c = rd('f300_hetero_contrasts.csv')
    fam = json.loads((T / 'f300_hetero_family.json').read_text()) if (T / 'f300_hetero_family.json').exists() else {}
    if not len(g):
        return '(heterogeneity not run)', fam
    lab = {'abs_flag': 'abstract flagged (pp)', 'llm_topic': 'LLM-topic share (pp)', 'emb_within_specter2_proximity_raw': 'within-institution distance',
           'emb_cross_specter2_proximity_raw': 'across-institution distance, pairs inside the group', 'entropy_subfield': 'topic entropy (bits)', 'jsd_subfield': 'cross-institution topic JSD (bits)'}
    scale = {'abs_flag': 100, 'llm_topic': 100}
    out = []
    for m, nm in lab.items():
        d = g[(g.measure == m) & g.dimension.isin(['tier', 'english', 'region', 'size'])]
        if not len(d):
            continue
        sc = scale.get(m, 1)
        out.append(f'\n**{nm}: post minus pre by group**\n\n| dimension | group | institutions | pre | post | change [95% CI] | placebo [95% CI] |\n|---|---|---|---|---|---|---|')
        for r in d.itertuples():
            out.append(f'| {r.dimension} | {r.group} | {r.n_inst} | {r.pre * sc:.3f} | {r.post * sc:.3f} | {fmt(r.change, r.lo, r.hi, sc, 3)} | {fmt(r.placebo, r.placebo_lo, r.placebo_hi, sc, 3)} |')
    out.append(f"\n**Contrasts and multiplicity.** {fam.get('contrasts_per_outcome', '?')} contrasts per outcome ({', '.join(f'{k} {v}' for k, v in fam.get('groups_per_dimension', {}).items())} groups); "
               f"primary family = {len(fam.get('primary_outcomes', []))} outcomes x contrasts = **{fam.get('primary_family', '?')}** tests; Holm survivors **{fam.get('holm_survivors', '?')}**, "
               f"Benjamini-Hochberg survivors **{fam.get('bh_survivors', '?')}** (adjusted p < 0.05). All contrasts, including secondary outcomes, are in `tables/f300_hetero_contrasts.csv`.\n")
    if len(c):
        s = c[c.primary & (c.bh_survives | c.holm_survives)].copy()
        s['a'] = s['diff'].abs()
        out.append('Largest surviving contrasts (group change minus comparator change; BH q < 0.05):\n\n| outcome | dimension | group | versus | difference [95% CI] | p | Holm | BH |\n|---|---|---|---|---|---|---|---|')
        for r in s.sort_values('a', ascending=False).head(25).itertuples():
            sc = scale.get(r.measure, 1)
            out.append(f'| {lab.get(r.measure, r.measure)} | {r.dimension} | {r.group} | {r.versus} | {fmt(r.diff, r.lo, r.hi, sc, 3)} | {r.p:.4f} | {r.holm:.3f} | {r.bh:.3f} |')
    return '\n'.join(out), fam


def group_ref_tables():
    """Reference overlap and citation concentration by institution group (scopes of sameness_refs: pairs inside the group), journal papers, post minus pre."""
    ov = rd('f300_overlap_journal_ALL-tier-english-region-size_contrasts.csv')
    co = rd('f300_concentration_journal_*_contrasts.csv')
    out = []
    for nm, d, meas, extra in (('Jaccard ratio obs/null (pairs inside the group)', ov, 'ref_jac_ratio', 'across'), ('share of references on the top 1% of cited works', co, 'cite_top1pct', 'full')):
        if not len(d):
            continue
        key = 'pairs' if extra == 'across' else 'variant'
        d = d[(d.measure == meas) & (d[key] == extra)]
        out.append(f'\n**{nm}, journal papers, post minus pre**\n\n| group | pre | post | change [95% CI] | placebo [95% CI] |\n|---|---|---|---|---|')
        for sc in sorted(d.scope.unique()):
            x = d[d.scope == sc]
            p, pl = row(x, 'post_minus_pre'), row(x, 'placebo_2019_21_minus_2016_18')
            if p is None:
                continue
            out.append(f'| {sc} | {p.pre:.4f} | {p.post:.4f} | {fmt(p.est, p.lo, p.hi, 1, 4)} | {fmt(pl.est, pl.lo, pl.hi, 1, 4) if pl is not None else "n/a"} |')
    return '\n'.join(out)


def consistency_tables():
    e = rd('f300_consistency_estimates.csv')
    p = rd('f300_consistency_papers.csv')
    out = []
    if len(e):
        names = {'abs_flag': ('abstract flagged (pp)', 100), 'llm_topic': ('LLM-topic share (pp)', 100), 'emb_within_specter2_proximity_raw': ('within-unit distance (SPECTER2)', 1),
                 'emb_cross_specter2_proximity_raw': ('across-unit distance (SPECTER2; deep: across schools)', 1), 'entropy_subfield': ('topic entropy (bits)', 1)}
        out.append('| measure | estimate | post minus pre [95% CI] |\n|---|---|---|')
        for r in e.itertuples():
            nm, sc = names.get(r.measure, (r.measure, 1))
            out.append(f'| {nm} | {r.estimate} | {fmt(r.est, r.lo, r.hi, sc, 3)} |')
    if len(p):
        r = p.iloc[0]
        out.append(f"\nPaper-level check: {int(r.papers_scored_by_both):,} papers were scored by both pipelines; their abstract flags agree for {r.flag_agreement:.4f} of them "
                   f"(flag rate {r.deep_flag_rate:.4f} in the 12-school scores, {r.field300_flag_rate:.4f} here; same threshold {r.threshold_deep:.3g}).")
    return '\n'.join(out) if out else '(consistency not run)'


def dir_bytes(p, seen=None):
    """Bytes under p; a hard-linked file counts once (inodes in `seen`, shared between calls)."""
    import os
    seen = set() if seen is None else seen
    tot = 0
    for r, _, fs in os.walk(p):
        for f in fs:
            try:
                st = os.lstat(os.path.join(r, f))
            except OSError:
                continue
            if (st.st_dev, st.st_ino) not in seen:
                seen.add((st.st_dev, st.st_ino))
                tot += st.st_size
    return tot


def storage_table():
    snap = F.snapshot_dir()
    w = F.work_dir()
    seen = set()
    rows = []
    if snap.exists():
        emb = snap / 'embeddings'
        for m in sorted(emb.iterdir()) if emb.exists() else []:
            rows.append(f'| embeddings {m.name} (fp16 abstract vectors) | {dir_bytes(m, seen) / 2**30:.2f} GiB |')
        rows.append(f'| rest of the sealed snapshot (corpus, tables, references, scores, mentions) | {dir_bytes(snap, seen) / 2**30:.2f} GiB |')
    if w.exists():
        rows.append(f'| work/ only (GPU text store, statistics, sameness inputs; files shared with the snapshot are hard links and counted once above) | {dir_bytes(w, seen) / 2**30:.2f} GiB |')
    return '| item | size |\n|---|---|\n' + '\n'.join(rows)


def build_md(models):
    fig = fig_series() + fig_hetero()
    inst = pd.read_parquet(F.work_dir() / 'institutions.parquet') if (F.work_dir() / 'institutions.parquet').exists() else pd.DataFrame()
    pap = pd.read_parquet(F.work_dir() / 'papers.parquet', columns=['work', 'year', 'abs_ok']) if (F.work_dir() / 'papers.parquet').exists() else pd.DataFrame()
    npap = len(pap)
    nabs = int(pap['abs_ok'].sum()) if len(pap) else 0
    het, fam = hetero_tables()
    md = f"""# Homogenization across the field: 300 universities, abstract level (snapshot {F.ID})

Owner decision 2026-11-08. The 12 deep schools stay the lab-level deep dive; this extension asks the same questions at the abstract level for **all 300 universities of the ShanghaiRanking GRAS 2025 Computer Science & Engineering ranking**, so that prestige tier and country can be examined and the key finding can be tested across the field. Window 2016-2025, **post = 2023-2025, pre = 2016-2022**, no 2026. The unit of resampling is the **institution** (cluster bootstrap, 400 draws, stratified by GRAS tier, 95% percentile intervals); no count of institutions is used as evidence. Placebo = 2019-21 minus 2016-18. Association, not causation.

## 1. The corpus

All works of 2016-2025 of type article, conference paper, preprint, review or book chapter, with at least one authorship at one of the 300 institutions (OpenAlex institution id of the GRAS map plus the related ids of merged institutions, matched through the institution lineage), that are **computer science**: OpenAlex primary topic in the field Computer Science, or primary source one of the 548 reviewed CS venues. Source: the public OpenAlex bulk snapshot 2026-10-14, streamed (no API credits). **{npap:,} papers**, of which **{nabs:,}** have an English abstract of at least 50 words (the detector's minimum) and enter the abstract layers.

**Attribution.** A paper counts in **each** cohort institution on its byline (full counting, the same rule as a paper of two labs in the 12-school study). Fractional weights (authorships of the institution / cohort-attributed authorships) are stored and reported as a sensitivity in the series tables (`counting = fractional`).

Size by year (`not_cs_*` columns count cohort works that were NOT stored, for the scale sensitivity: `not_cs_but_cs_secondary_topic` have a CS field only in a secondary topic):

{size_table()}

## 2. Headline: pre (2016-22) against post (2023-25)

{headline_table()}

**Reading** (rule: the post-minus-pre interval excludes zero; 'continues the pre-2023 drift' when the placebo has the same sign and is at least as large; more alike = overlap and concentration up, distance and entropy down):\n\n{reading()}\n\nFigure 1 (`figures/fig1_yearly_series.png`): yearly series with 95% bands.

![yearly series](figures/fig1_yearly_series.png)

## 3. Who is affected: tier, country, region, English-speaking, size

Groups: GRAS tier (top 10, 11-50, 51-100, 101-200, 201-300), region and country (OpenAlex institution country; countries with at least {10} cohort institutions), English-speaking country (US, GB, CA, AU, NZ, IE by institution country; names are never used), size (quartile of median papers per year).
{het}

### Reference overlap and citation concentration by group
{group_ref_tables()}

![heterogeneity](figures/fig2_heterogeneity.png)

## 4. Consistency with the 12 deep schools

{consistency_tables()}

## 5. Compute and storage

{storage_table()}

## 6. Caveats

- Preprints and their published versions can both appear (OpenAlex merges many, not all); the journal-only sample is the primary one for reference lists, because the lists of repository records vanish from 2022.
- The abstract flag is the v1 detector at its fixed operating point (1% of validation human abstracts); the pre-2023 level (about 2%) is its floor. It is a share of abstracts the detector calls AI-like, not a share of AI-written abstracts.
- OpenAlex field assignment (primary topic) and institution lineage are machine-made; mislabels in either move papers in or out of the corpus. Institutions that contain others in their lineage bring those in (a hospital under a university).
- Embedding distances are on centred unit vectors; AI-polished wording moves vectors mechanically (the 12-school paired rewrite control is not repeated here); the topic-residual rows are the check.
"""
    (R / 'FIELD300.md').write_text(md)
    print('FIELD300.md', len(md))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', default='specter2_proximity,scincl')
    a = ap.parse_args()
    MODELS[:] = a.models.split(',')
    R.mkdir(parents=True, exist_ok=True)
    build_md(MODELS)
