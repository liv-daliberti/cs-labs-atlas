"""Identifier and alias fields of pis.json for id-first matching (2026-11-18, built-recall item 3).

A recall checker or a cross-school join should match a built PI by identifier first and by name only as a fallback.
CJK-named schools (hit, seu, zju, sjtu, tsinghua, ustc) carry the PI under the listed Chinese name, so the Latin
spelling and the person identifiers must be readable from the row without parsing `names`, URLs or `oaAuthorIds`.

`add(pis, school)` only ADDS four keys to each PI record and changes no existing key:
  latinAliases  every Latin-script spelling the build already holds for the person: the census name and its aliases,
                reviewed overrides (aliases, display_name), merged census rows and the reviewed census-name-aliases
                pairs of the school; never invented (no transliteration)
  dblpPids      DBLP person ids as `84/3894` (from `dblp`, whatever URL form the census or the identity stage wrote)
  orcidIds      ORCIDs as bare ids (from `orcid`)
  openalexIds   OpenAlex author ids as `A...` (reviewed ids and the ids the identity stage anchored; the reviewed
                `mixedOpenAlex` and `notOpenAlex` ids are another person's records and never appear here)
The id lists are exactly what the row's own fields hold (a PI under an identity hold has none, and none is added).
"""
import re

LATIN = re.compile(r"^[A-Za-zÀ-ɏ][A-Za-zÀ-ɏ' .,\-]*$")
DBLP_PID = re.compile(r'dblp\.org/pid/([^\s?#]+)')
ORCID = re.compile(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])')
OA_ID = re.compile(r'(A\d{4,})')


def latin(name):
    """The name if it is written in Latin script and has two or more words (a family name and a given name), else None."""
    s = ' '.join(str(name or '').split())
    return s if LATIN.match(s) and len(s.split()) >= 2 else None


def dblp_pid(v):
    s = str(v or '').strip()
    m = DBLP_PID.search(s)
    s = m.group(1) if m else s
    s = re.sub(r'\.(html|xml)$', '', s).strip('/')
    return s if re.match(r'^[\w-]+/[\w-]+$', s) else None


def orcid_id(v):
    m = ORCID.search(str(v or ''))
    return m.group(1) if m and m.group(1) != '0000-0000-0000-0000' else None


def oa_id(v):
    m = OA_ID.search(str(v or ''))
    return m.group(1) if m else None


def uniq(items):
    return list(dict.fromkeys(x for x in items if x))


def add(pis, pairs=()):
    """Add the four keys to every record of `pis` (in place). `pairs`: the school's reviewed (name_a, name_b) alias pairs."""
    other = {}
    for a, b in pairs:
        other.setdefault(a, []).append(b)
        other.setdefault(b, []).append(a)
    for p in pis:
        spellings = [p.get('pi'), p.get('censusName')] + list(p.get('names') or []) + list(p.get('mergedCensusRows') or [])
        spellings += [x for s in list(spellings) for x in other.get(s, [])]
        p['latinAliases'] = uniq(latin(s) for s in spellings)
        p['dblpPids'] = uniq(dblp_pid(v) for v in p.get('dblp') or [])
        p['orcidIds'] = uniq(orcid_id(v) for v in p.get('orcid') or [])
        p['openalexIds'] = uniq(oa_id(v) for v in list(p.get('reviewedOpenAlex') or []) + list(p.get('oaAuthorIds') or []))
    return pis
