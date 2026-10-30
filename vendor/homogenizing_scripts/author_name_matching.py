# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/author_name_matching.py (sha256 35c5e7967898ba8010955227e0eebbf86c69076341695b9baa99d6ec4233972a); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Unicode-preserving, full-token name corroboration.

Reviewed source: cs17_author_name_normalization_audit, manifest
7a66e6343c7b859fdd1cb125f6a7a52f15282c828b06d7566ff844ab6af8a82e.

Names remain source evidence, not sufficient identity proof. Callers must separately
verify named ownership, full given/surname semantics, exact ID and institution.
No transliteration, nickname expansion, substring, or initial expansion is used.
"""
from collections import Counter
import unicodedata as U


def name_tokens(value, *, fold_latin_diacritics=True):
    """Preserve letters/scripts; punctuation is a boundary, never deletion.

    Case/compatibility/canonical normalization handles typography. The optional
    Latin-only diacritic fold preserves the existing José/Jose corroboration
    convention; marks in other scripts are retained. Ø/Ł/ı and cross-script
    lookalikes are not transliterated. Original source strings remain untouched.
    """
    if not isinstance(value, str):
        return ()
    text=U.normalize('NFD', U.normalize('NFKC',value).casefold())
    words=[];current=[];latin_base=False
    for c in text:
        cat=U.category(c)
        if cat.startswith('L') or cat.startswith('N'):
            current.append(c)
            latin_base=cat.startswith('L') and U.name(c,'').startswith('LATIN ')
        elif cat.startswith('M') and current:
            if not(fold_latin_diacritics and latin_base):current.append(c)
        else:
            if current:words.append(U.normalize('NFC',''.join(current)))
            current=[];latin_base=False
    if current:words.append(U.normalize('NFC',''.join(current)))
    return tuple(words)


def full_atom(token):
    letters=[c for c in token if U.category(c).startswith('L')]
    if len(letters)>=2:return True
    # A one-character ideograph or syllabic name component is not a Latin initial.
    return len(letters)==1 and U.name(letters[0],'').startswith(('CJK ','HIRAGANA ','KATAKANA ','HANGUL '))


def requirements(tokens, *, fold_latin_diacritics=True):
    if not isinstance(tokens,(list,tuple)) or not tokens:return (), 'empty_or_invalid_requirement'
    required=[]
    for raw in tokens:
        if not isinstance(raw,str) or not raw.strip():return (), 'empty_or_invalid_review_component'
        parts=name_tokens(raw,fold_latin_diacritics=fold_latin_diacritics)
        if not parts:return (), 'review_component_has_no_name_tokens'
        if any(not any(U.category(c).startswith('L') for c in p) or any(U.category(c).startswith('N') for c in p) for p in parts):return (), 'nonletter_review_component'
        required.extend(parts)
    if len(required)<2 or sum(full_atom(x) for x in required)<2:return (), 'full_given_and_surname_not_lexically_supported'
    return tuple(required), None


def match_name(name,tokens,*,fold_latin_diacritics=True):
    required,error=requirements(tokens,fold_latin_diacritics=fold_latin_diacritics)
    if error:return False
    available=Counter(name_tokens(name,fold_latin_diacritics=fold_latin_diacritics))
    return all(available[token]>=count for token,count in Counter(required).items())


def author_name_evidence(candidate,tokens,*,fold_latin_diacritics=True):
    if not isinstance(candidate,dict):return []
    names=[candidate.get('display_name','')]
    alternatives=candidate.get('display_name_alternatives') or []
    if isinstance(alternatives,list):names.extend(alternatives)
    return [name for name in names if isinstance(name,str) and match_name(name,tokens,fold_latin_diacritics=fold_latin_diacritics)]
