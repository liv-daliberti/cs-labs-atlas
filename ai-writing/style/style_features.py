"""Writing-style features of one text (pure Python + numpy; no spaCy: it is not in the study environment, so no POS profile).

features(text, kobak=set()) -> dict:
  sent_mean, sent_sd         words per sentence (mean, standard deviation)
  mtld                       measure of textual lexical diversity (McCarthy & Jarvis 2010, TTR threshold 0.72, mean of forward and backward passes);
                             length-robust; NaN under 50 tokens; at most MTLD_CAP tokens are used
  word_len, long_share       mean letters per word; share of words with 7+ letters
  flesch, fk_grade           Flesch reading ease and Flesch-Kincaid grade (vowel-group syllable count)
  p_comma .. p_slash         punctuation per 1,000 characters
  hedge                      hedging words per 1,000 words
  kobak                      Kobak et al. (2024) style-word rate per 1,000 words (one feature, not the whole story)
  fw_<word>                  frequency of each of the FUNCTION_WORDS per 1,000 words
"""
import re

import numpy as np

MTLD_CAP = 5000
MARKUP = re.compile(r'<[^>]+>|\*\*|__')
ABBR = re.compile(r'\b(e\.g|i\.e|et al|fig|figs|eq|eqs|vs|etc|cf|approx|resp|ref|refs|no|sec|dr|prof|st|inc)\.', re.I)
SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9(\[])')
WORD = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*")
VOWELS = re.compile(r'[aeiouy]+')
PUNCT = {'p_comma': ',', 'p_semicolon': ';', 'p_colon': ':', 'p_paren': '(', 'p_dash': '—–', 'p_quote': '"“”', 'p_question': '?',
         'p_percent': '%', 'p_slash': '/'}
FUNCTION_WORDS = ('the a an and or but nor so yet of in on at by for with without from to into onto over under about above below between among through during '
                  'before after since until while as than that which who whom whose what when where why how this these those it its they them their we our us '
                  'i you he she his her there here is are was were be been being am do does did have has had can could may might will would shall should must '
                  'not no also only such each both either neither any all some many much most more less few other another same own very just still even then '
                  'thus hence however therefore moreover furthermore if whether because although though unless once both per via within across against '
                  'toward towards upon whereas whilst').split()
FUNCTION_WORDS = tuple(dict.fromkeys(FUNCTION_WORDS))
HEDGES = frozenset('may might could possibly perhaps probably likely unlikely potentially presumably apparently seemingly suggest suggests suggested suggesting '
                   'appear appears appeared seem seems seemed indicate indicates tend tends generally typically often usually somewhat relatively roughly '
                   'approximately partly partially arguably conceivably'.split())
FW_INDEX = {w: i for i, w in enumerate(FUNCTION_WORDS)}


def clean(text):
    t = MARKUP.sub(' ', str(text or ''))
    t = re.sub(r'(?<=[a-z])-\s*\n\s*(?=[a-z])', '', t)       # words hyphenated at a line break (full-text extraction)
    return re.sub(r'\s+', ' ', t).strip()


def syllables(w):
    n = len(VOWELS.findall(w.lower()))
    if w.lower().endswith('e') and n > 1 and not w.lower().endswith(('le', 'ee')):
        n -= 1
    return max(n, 1)


def mtld(tokens, thr=0.72):
    def one(seq):
        factors, types, count = 0.0, set(), 0
        for t in seq:
            count += 1
            types.add(t)
            if len(types) / count <= thr:
                factors += 1
                types, count = set(), 0
        if count:
            ttr = len(types) / count
            factors += (1 - ttr) / (1 - thr)
        return len(seq) / factors if factors else float('nan')
    if len(tokens) < 50:
        return float('nan')
    tokens = tokens[:MTLD_CAP]
    a, b = one(tokens), one(tokens[::-1])
    return (a + b) / 2


def feature_names():
    return (['sent_mean', 'sent_sd', 'mtld', 'word_len', 'long_share', 'flesch', 'fk_grade'] + list(PUNCT) + ['hedge', 'kobak'] + ['fw_' + w for w in FUNCTION_WORDS])


def features(text, kobak=frozenset()):
    t = clean(text)
    toks = [w.lower() for w in WORD.findall(t)]
    n = len(toks)
    out = dict.fromkeys(feature_names(), float('nan'))
    if n < 20:
        return out
    sents = [s for s in SENT.split(ABBR.sub(lambda m: m.group(0).replace('.', ''), t)) if WORD.search(s)]
    sl = np.array([len(WORD.findall(s)) for s in sents], float)
    syl = sum(syllables(w) for w in toks)
    out['sent_mean'], out['sent_sd'] = float(sl.mean()), float(sl.std())
    out['mtld'] = mtld(toks)
    lens = [len(w.replace('-', '').replace("'", '')) for w in toks]
    out['word_len'], out['long_share'] = float(np.mean(lens)), float(np.mean([x >= 7 for x in lens]))
    out['flesch'] = 206.835 - 1.015 * (n / len(sents)) - 84.6 * (syl / n)
    out['fk_grade'] = 0.39 * (n / len(sents)) + 11.8 * (syl / n) - 15.59
    for k, chars in PUNCT.items():
        out[k] = 1000.0 * sum(t.count(c) for c in chars) / max(len(t), 1)
    out['hedge'] = 1000.0 * sum(w in HEDGES for w in toks) / n
    out['kobak'] = 1000.0 * sum(w in kobak for w in toks) / n
    cnt = np.zeros(len(FUNCTION_WORDS))
    for w in toks:
        j = FW_INDEX.get(w)
        if j is not None:
            cnt[j] += 1
    for w, c in zip(FUNCTION_WORDS, cnt):
        out['fw_' + w] = 1000.0 * c / n
    return out
