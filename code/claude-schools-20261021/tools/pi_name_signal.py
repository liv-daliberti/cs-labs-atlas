"""Does a page's text name a Han-keyed PI? One helper for the lab-page audit (labpage_audit.page_lacks_pi) and the lab-website register
(person_fetch.names_person / last_name_on_page, lab_websites.verify_websites). A SIGNAL that a page is about the PI, never identity binding or identity
evidence (owner rulings 2026-11-12). Readings, registry first: the record's own Latin names/aliases, then the pinyin of a Han name (pypinyin, optional: without
it only the registry names count). Both the family and the given part must stand together (either order, given syllables joined or spaced), so a namesake page
that holds only the family name fails, and so do bare substrings ('li', 'yong' inside other words)."""
import re
import unicodedata

HAN = re.compile(r'[\u3400-\u9fff]')


def _fold(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def _pinyin_syllables(han):
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return []
    return [x.lower() for x in lazy_pinyin(''.join(han.split())) if x.isalpha()]


def readings(pi, names=None):
    """[(family, given)] lower-case, registry Latin readings first, pinyin readings of Han names after them."""
    out, pinyin = [], []
    for n in list(names or []) + [pi]:
        n = str(n or '').strip()
        if not n:
            continue
        if HAN.search(n):
            syl = _pinyin_syllables(n)
            if len(syl) >= 2:
                pinyin.append((syl[0], ''.join(syl[1:])))
            continue
        toks = [_fold(t) for t in re.findall(r"[A-Za-z][A-Za-z'\-]*", n)]
        if len(toks) >= 2:
            out += [(toks[-1], ''.join(toks[:-1]).replace('-', '')), (toks[0], ''.join(toks[1:]).replace('-', ''))]
    return list(dict.fromkeys(out + pinyin))


def page_names_pi(text, pi, names=None):
    toks = re.findall(r'[a-z]+', _fold(text))
    for f, g in readings(pi, names):
        if len(g) < 2:
            continue
        for i in range(len(toks)):
            if toks[i] == f and any(''.join(toks[i + 1:i + 1 + k]) == g for k in range(1, 5)):
                return True    # 'Zhang Ming-Xing'
            for k in range(1, 5):
                if ''.join(toks[i:i + k]) == g and i + k < len(toks) and toks[i + k] == f:
                    return True    # 'Mingxing Zhang', 'Ming Xing Zhang'
    return False
