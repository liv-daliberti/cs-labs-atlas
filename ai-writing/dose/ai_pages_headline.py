"""headline.json: 4 to 6 findings. Each sentence is rendered by a function of the finding's stored `values` (RENDER[id](values)), and the values are copied from the other v2
files, so the sentence cannot drift from the numbers: tests/test_ai_pages_data.py re-renders every stored claim."""
import gzip
import json

import ai_pages as A

PAGES = dict(how_much='how-much', given_ai='given-ai', all_rewritten='all-rewritten')


def pct(v, d=1):
    return f'{100 * v:.{d}f}%'


def sg(v, d=3):
    return f'{v:+.{d}f}'


def verdict(lo, hi, neg, pos, zero):
    return neg if hi < 0 else pos if lo > 0 else zero


def r_rise(v):
    return (f"In 2025, {pct(v['y2025'])} of lab papers had at least a quarter of their passages flagged as AI-written (95% interval {pct(v['lo2025'])}-{pct(v['hi2025'])}, {v['n2025']:,} papers with full text), "
            f"against {pct(v['pre_share'], 2)} in 2016-2022, where such flags are detector false positives.")


def r_where(v):
    return (f"In 2025, {pct(v['llm'])} of papers in LLM topics (interval {pct(v['llm_lo'])}-{pct(v['llm_hi'])}) and {pct(v['non'])} of papers in all other topics ({pct(v['non_lo'])}-{pct(v['non_hi'])}) "
            f"had at least 25% AI passages, a ratio of {v['ratio']:.1f}; LLM topics hold {pct(v['llm_of_all'], 0)} of 2025 papers and {pct(v['llm_of_ai'], 0)} of the AI-flagged ones.")


def r_matched_novelty(v):
    word = verdict(v['lo'], v['hi'], 'less novel than', 'more novel than', 'not distinguishable from')
    return (f"Within the same topic, year and school, AI papers (at least 25% AI passages) are {word} non-AI papers in embedding novelty: {sg(v['effect'], 4)} ({sg(v['lo'], 4)} to {sg(v['hi'], 4)}; SPECTER2 proximity, "
            f"{v['n_ai']:,} AI papers, novelty sd {v['sd']:.3f}); the 2017-2021 placebo gives {sg(v['p_effect'], 4)} ({sg(v['p_lo'], 4)} to {sg(v['p_hi'], 4)}); "
            f"across the {v['models']} embedding models {v['models_neg']} intervals lie below zero and {v['models_pos']} above.")


def r_matched_diversity(v):
    dw = verdict(v['d_lo'], v['d_hi'], 'lower', 'higher', 'not different')
    vw = verdict(v['v_lo'], v['v_hi'], 'lower', 'higher', 'not different')
    placebo = 'a gap the placebo does not show' if v['pd_lo'] <= 0 <= v['pd_hi'] else 'a gap the placebo also shows'
    keep = ('survives' if v['w_hi'] < 0 or v['w_lo'] > 0 else 'does not survive')
    return (f"In size-matched sets of {v['set_size']} AI and {v['set_size']} non-AI papers with the same topic, year and school mix, AI papers are {dw} in dispersion ({sg(v['d'], 4)} [{sg(v['d_lo'], 4)}, {sg(v['d_hi'], 4)}]) "
            f"and {vw} in Vendi score ({sg(v['v'], 2)} [{sg(v['v_lo'], 2)}, {sg(v['v_hi'], 2)}]), slightly more alike, {placebo} (placebo {sg(v['pd'], 4)} [{sg(v['pd_lo'], 4)}, {sg(v['pd_hi'], 4)}] and "
            f"{sg(v['pv'], 2)} [{sg(v['pv_lo'], 2)}, {sg(v['pv_hi'], 2)}]; SPECTER2 proximity; intervals below zero in {v['disp_models_neg']} (dispersion) and {v['vendi_models_neg']} (Vendi) of 7 models). "
            f"With every abstract rewritten in AI wording the dispersion gap is {sg(v['w_rew'], 4)} [{sg(v['w_lo'], 4)}, {sg(v['w_hi'], 4)}] against {sg(v['w_orig'], 4)} [{sg(v['w_olo'], 4)}, {sg(v['w_ohi'], 4)}] on the same papers, "
            f"so wording explains {pct(v['w_share'], 0)} ({pct(v['w_slo'], 0)} to {pct(v['w_shi'], 0)}) and the gap {keep} the wording control.")


def r_lab_scatter(v):
    return (f"Across {v['labs']} labs, a one-SD higher AI dose goes with a {sg(v['beta'], 2)} SD change in dispersion after 2023 against 2016-2022 ({sg(v['lo'], 2)} to {sg(v['hi'], 2)}; SPECTER2 proximity, "
            f"Huber, size and school controls); the interval excludes zero in {v['models_pos'] + v['models_neg']} of 7 models ({v['models_pos']} above, {v['models_neg']} below); "
            f"{v['pre_out']} of {v['pre_n']} pre-ChatGPT event-study coefficients exclude zero.")


def r_figure3(v):
    ew = 'higher' if v['ext_all'] > 0 else 'lower'
    hw = 'higher' if v['ent_all'] > 0 else 'lower'
    return (f"Pooled over schools, equal-size draws of AI papers have a {ew} knowledge extent than draws of non-AI papers (median difference {sg(v['ext_all'], 3)}; the AI draw is lower in {pct(v['ext_share'], 0)} of draws) "
            f"and a {hw} topic entropy ({sg(v['ent_all'], 2)} bits; AI lower in {pct(v['ent_share'], 0)}); AI papers have the lower median extent at {v['ext_lower']} of {v['schools']} schools and the lower median entropy at {v['ent_lower']}.")


RENDER = dict(rise=r_rise, where=r_where, matched_novelty=r_matched_novelty, matched_diversity=r_matched_diversity, lab_scatter=r_lab_scatter, figure3=r_figure3)


def rd(name):
    p = A.OUT / name
    return json.loads(gzip.open(p).read() if p.suffix == '.gz' else p.read_bytes())


def find(rows, **kw):
    for r in rows:
        if all(r.get(k) == v for k, v in kw.items()):
            return r
    raise KeyError(kw)


def finding(id_, values, number, evidence, cannot):
    return dict(id=id_, claim=RENDER[id_](values), values=values, number=number, evidence=evidence, cannot_conclude=cannot)


def headline(fr, res):
    use, mt, lab, f3, ev = rd('ai_use.json.gz'), rd('matched_test.json'), rd('lab_scatter.json.gz'), rd('fig3_nine_schools.json'), rd('event_study.json')
    out = []
    Y = A.YEARS
    i25, i22 = Y.index(2025), Y.index(2022)

    allk = use['kind_series']['all']
    pre_n, pre_a = sum(allk['n'][:i22 + 1]), sum(allk['a'][:i22 + 1])
    v = dict(pre_share=pre_a / pre_n, pre_n=pre_n, y2025=allk['share'][i25], lo2025=allk['lo'][i25], hi2025=allk['hi'][i25], n2025=allk['n'][i25])
    out.append(finding('rise', v, dict(value=v['y2025'], lo=v['lo2025'], hi=v['hi2025'], unit='share of papers with dose >= 25%', compare=v['pre_share']),
                       dict(page=PAGES['how_much'], anchor='share-over-time', file='ai_use.json.gz', key='kind_series.all'),
                       ['That any one paper was written by AI: the detector scores passages, and about 1% of human passages are flagged by design.',
                        'That the rise is caused by ChatGPT-style tools rather than other changes in how papers are written or processed.',
                        'Anything about papers without usable full text (about a third of papers); they are scored by their abstract only.']))

    llm, non = use['kind_series']['llm'], use['kind_series']['non_llm']
    v = dict(llm=llm['share'][i25], llm_lo=llm['lo'][i25], llm_hi=llm['hi'][i25], non=non['share'][i25], non_lo=non['lo'][i25], non_hi=non['hi'][i25], llm_n=llm['n'][i25], non_n=non['n'][i25],
             ratio=llm['share'][i25] / non['share'][i25], llm_of_ai=use['meta']['llm_share_of_2025_ai_papers'], llm_of_all=use['meta']['llm_share_of_2025_papers'])
    out.append(finding('where', v, dict(value=v['llm'], lo=v['llm_lo'], hi=v['llm_hi'], unit='share of 2025 LLM-topic papers with dose >= 25%', compare=v['non']),
                       dict(page=PAGES['how_much'], anchor='where-ai-is-used', file='ai_use.json.gz', key='kind_series.llm / kind_series.non_llm'),
                       ['That LLM researchers use AI more for writing because of their topic: they also differ in venue, team size and norms.',
                        'That non-LLM fields are untouched: their share is also far above the pre-2023 floor.',
                        'The topic kinds are assigned by keyword rules on BERTopic labels, not by hand; a few topics sit on the border.']))

    h = find(mt['rows'], population='post', model=A.HEADLINE, measure='novelty')
    p = find(mt['rows'], population='placebo', model=A.HEADLINE, measure='novelty')
    post_rows = [x for x in mt['rows'] if x['population'] == 'post' and x['measure'] == 'novelty']
    v = dict(effect=h['effect'], lo=h['lo'], hi=h['hi'], sd=h['sd'], n_ai=h['n_ai'], n_non=h['n_non'], cells=h['cells'], p_effect=p['effect'], p_lo=p['lo'], p_hi=p['hi'],
             models_neg=sum(x['hi'] < 0 for x in post_rows), models_pos=sum(x['lo'] > 0 for x in post_rows), models=len(post_rows), raw=h['raw'])
    out.append(finding('matched_novelty', v, dict(value=h['effect'], lo=h['lo'], hi=h['hi'], unit='novelty (cosine distance), AI minus non-AI', compare=p['effect']),
                       dict(page=PAGES['given_ai'], anchor='topic-matched-test', file='matched_test.json', key='rows[population=post, measure=novelty]'),
                       ['That AI use changes what a paper is about: this compares different papers, not the same paper with and without AI.',
                        'That the effect is the same for every lab: the interval is over labs, not within them.',
                        'Anything outside the matched cells: AI papers in topics with no non-AI paper in the same year and school drop out.']))

    d = find(mt['rows'], population='post', model=A.HEADLINE, measure='dispersion')
    vd = find(mt['rows'], population='post', model=A.HEADLINE, measure='vendi')
    pd_ = find(mt['rows'], population='placebo', model=A.HEADLINE, measure='dispersion')
    pv = find(mt['rows'], population='placebo', model=A.HEADLINE, measure='vendi')
    v = dict(set_size=mt['meta']['set_size'], d=d['effect'], d_lo=d['lo'], d_hi=d['hi'], v=vd['effect'], v_lo=vd['lo'], v_hi=vd['hi'], pd=pd_['effect'], pd_lo=pd_['lo'], pd_hi=pd_['hi'],
             pv=pv['effect'], pv_lo=pv['lo'], pv_hi=pv['hi'],
             disp_models_neg=sum(x['hi'] < 0 for x in mt['rows'] if x['population'] == 'post' and x['measure'] == 'dispersion'),
             vendi_models_neg=sum(x['hi'] < 0 for x in mt['rows'] if x['population'] == 'post' and x['measure'] == 'vendi'))
    w = find(mt['wording'], model=A.HEADLINE, measure='dispersion')
    v.update(w_orig=w['original'], w_olo=w['original_lo'], w_ohi=w['original_hi'], w_rew=w['rewritten'], w_lo=w['rewritten_lo'], w_hi=w['rewritten_hi'], w_share=w['share_wording'], w_slo=w['share_lo'], w_shi=w['share_hi'],
             wording_models_surviving=sum(x['rewritten_hi'] < 0 for x in mt['wording'] if x['measure'] == 'dispersion'))
    out.append(finding('matched_diversity', v, dict(value=d['effect'], lo=d['lo'], hi=d['hi'], unit='dispersion (cosine geometry), AI minus non-AI', compare=pd_['effect']),
                       dict(page=PAGES['given_ai'], anchor='topic-matched-test', file='matched_test.json', key='rows[population=post, measure in dispersion, vendi]; wording[]'),
                       ['That AI makes research less diverse: matching on topic removes the topic channel by construction, and sets are small.',
                        'Anything about full text: these are abstract embeddings of one detector-defined group. The wording control uses one rewriting model and prompt (Qwen2.5-7B, polish).',
                        'The placebo flags are detector noise: a placebo gap of similar size means the detector alone could produce the gap.']))

    s = find(lab['slopes'], measure='dispersion', model=A.HEADLINE)
    sl = [x for x in lab['slopes'] if x['measure'] == 'dispersion']
    e = ev['models'][A.HEADLINE]['disp']['dose']
    pre_cov = [x for x in e['event'] if x['year'] <= 2020]
    v = dict(beta=s['beta'], lo=s['lo'], hi=s['hi'], labs=s['labs'], models_pos=sum(x['lo'] > 0 for x in sl), models_neg=sum(x['hi'] < 0 for x in sl),
             pre_out=sum(x['lo'] > 0 or x['hi'] < 0 for x in pre_cov), pre_n=len(pre_cov))
    out.append(finding('lab_scatter', v, dict(value=s['beta'], lo=s['lo'], hi=s['hi'], unit='standardized slope of the change in dispersion on the lab AI dose'),
                       dict(page=PAGES['given_ai'], anchor='lab-scatter', file='lab_scatter.json.gz', key='slopes[measure=dispersion]; event_study.json models.specter2_proximity.disp.dose'),
                       ['That AI use makes a lab more or less diverse: labs that use more AI differ in field and size, and placebo breaks show similar drifts before 2023 (event_study.json).',
                        'That the slope holds inside a lab across its own years: that is the within-lab design of the AI-dose report.',
                        'Anything about labs with fewer than 5 papers in either period, or fewer than 5 scored 2023-2025 papers.']))

    g = [x for x in f3['groups'] if x['variant'] == 'ft25' and 'skipped' not in x and x['school'] != 'all']
    al = find(f3['groups'], variant='ft25', school='all')
    v = dict(schools=len(g), ext_lower=sum(x['extent']['ai']['med'] < x['extent']['not']['med'] for x in g), ent_lower=sum(x['entropy']['ai']['med'] < x['entropy']['not']['med'] for x in g),
             ext_all=al['extent']['diff_median'], ent_all=al['entropy']['diff_median'], ext_share=al['extent']['ai_lower_share'], ent_share=al['entropy']['ai_lower_share'],
             n=al['n_per_draw'], flagged=al['flagged'], not_flagged=al['not_flagged'])
    out.append(finding('figure3', v, dict(value=al['extent']['diff_median'], lo=None, hi=None, unit='median difference in knowledge extent, AI minus non-AI (equal-size draws)', share_lower=al['extent']['ai_lower_share']),
                       dict(page=PAGES['given_ai'], anchor='figure-3', file='fig3_nine_schools.json', key='groups[variant=ft25]'),
                       ['That the gap is not about topics: Figure 3 does not match on topic (the matched test does).',
                        'Statistical significance beyond the draw spread: the boxes show the spread of draws, not a confidence interval over labs.',
                        'Schools with too little full text (Georgia Tech) are in the abstract-flag variant only.']))
    doc = dict(meta=dict(rule='claim = RENDER[id](values) in ai_pages_headline.py; values are copied from the named file and key', last_year=A.LAST, pages=PAGES, anchors='anchor ids are the ones the site agent is asked to create'),
               findings=out)
    (A.OUT / 'headline.json').write_text(json.dumps(doc, indent=1, allow_nan=False))
    return len(out)
