# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-listings-20261022/scripts/match.py (sha256 a87377b8816f5a23e8b9abcd21e84c4b630b1d5655f6a6aa471906edd15cd097); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Find each PI on each captured listing page (offline, from captures/listings.sqlite)."""
import json
import re
import sys
import unicodedata

sys.path.insert(0, ".")
import extract

NICK = {
    "thomas": ["tom"], "tom": ["thomas"], "matthew": ["matt"], "matt": ["matthew"],
    "benjamin": ["ben"], "ben": ["benjamin"], "daniel": ["dan"], "dan": ["daniel"],
    "edward": ["ed"], "ed": ["edward"], "michael": ["mike"], "mike": ["michael"],
    "robert": ["rob", "bob"], "andrew": ["andy"], "david": ["dave"],
    "alexander": ["alex"], "alex": ["alexander"], "zachary": ["zach", "zack"],
    "jennifer": ["jen"], "jen": ["jennifer"], "nicholas": ["nick", "nic"],
    "nick": ["nicholas", "nic"], "nic": ["nick", "nicholas"], "samuel": ["sam"],
    "jonathan": ["jon"], "christopher": ["chris"], "william": ["bill", "will"],
    "szymon": ["szymon"], "warren": ["warren"], "brian": ["brian"],
}

TITLE_RX = re.compile(r"\b(Professor|Lecturer|Faculty|Emerit\w*|Scholar|Instructor|Chair|Dean|Director|Fellow|"
                      r"Researcher|Provost|President|Preceptor|Chief|Head|Co-?director|Member|Associate|Assistant|"
                      r"Senior|Visiting)\b", re.I)
NOT_TITLE_RX = re.compile(r"^(Research (Interests|Areas|Topics)|Tags:|E-?mail|Office|Phone|Tel|Fax|Homepage|Website|"
                          r"Web|Ph\.?\s?D|M\.?S\.?|B\.?S\.?|Profile|Room|Lab\b|Read more|More info|Learn more|"
                          r"Open in new window|P:|Download|CV)", re.I)
SECTION_RX = re.compile(r"^(Faculty|Associated|Associate|Emerit\w*|Visiting|Visitors|Affiliated|Joint|Core|Senior|"
                        r"Junior|Lecturers?|Researchers?|Research Faculty|Research Scholars?|Research Staff|Staff|"
                        r"Teaching|Adjunct|People|Professors|In Memoriam|Postdoc\w*|Graduate|Instructors|Fellows|"
                        r"Members|Directory|Our Faculty|All Faculty|Former|Primary|Secondary|Courtesy|Ladder|"
                        r"Tenure|Administrative)\b", re.I)
NOT_SECTION_RX = re.compile(r"^(Research (Areas|Interests|Topics)|People Menu|Faculty Spotlight|Faculty & Research$|"
                            r"Faculty Resources|Faculty Books|Faculty Awards)", re.I)
NONFAC_RX = re.compile(r"Postdoc|Post-?doctoral|Graduate Student|Ph\.?D\.? (Student|Candidate)|Doctoral Student|"
                       r"\bStaff\b|Undergraduate|Alumni|In Memoriam|Memorial|Spotlight|\bNews\b|\bEvents?\b|"
                       r"Research (Associate|Collaborator|Specialist|Scholar)|Visiting (Fellow|Researcher|Scholar)|Student", re.I)
FAC_RX = re.compile(r"Professor|Lecturer|Faculty|Instructor|Emerit|Dean\b|Chair\b|Provost|President", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9\-' ]+", " ", s)
    s = s.replace("'", "")
    return s.split()


def core(tokens):
    """drop initials (single letters) and parenthetical nicknames already removed by norm"""
    return [t for t in tokens if len(t) > 1]


def variants(pi):
    out = set()
    for a in [pi["pi"]] + pi.get("aliases", []):
        toks = core(norm(a))
        if len(toks) < 2:
            continue
        out.add(tuple(toks))
        first = toks[0]
        for n in NICK.get(first, []):
            out.add(tuple([n] + toks[1:]))
        # drop middle names: "Adji Bousso Dieng" -> "Adji Dieng" only if alias says so (kept via aliases)
    return out


def split_name_prefix(block, vset):
    """If block starts with a PI name (possibly 'Last, First'), return (name_as_written, remainder)."""
    raw = block.strip()
    # strip leading honorific
    m = re.match(r"^(Prof\.?|Professor|Dr\.?)\s+", raw)
    if m and not re.match(r"^Professor\s+of\b", raw):
        raw2 = raw[m.end():]
    else:
        raw2 = raw
    words = raw2.split()
    # try "First [M.] Last ..." prefixes
    for k in range(min(7, len(words)), 1, -1):
        pref = " ".join(words[:k])
        pref_clean = pref.rstrip(",;:")
        toks = core(norm(pref_clean))
        if tuple(toks) in vset:
            rem = raw2[len(pref_clean):]
            return pref_clean, rem
    # try "Last, First [M.]"
    m = re.match(r"^([^,]{2,40}),\s*([^,;]{2,40})(.*)$", raw2)
    if m:
        last, first, rest = m.group(1), m.group(2), m.group(3)
        toks = core(norm(first)) + core(norm(last))
        if tuple(toks) in vset:
            return f"{m.group(1)}, {m.group(2)}".strip(), rest
        # first part may carry trailing title words: try shrinking 'first'
        fw = first.split()
        for k in range(len(fw) - 1, 0, -1):
            toks = core(norm(" ".join(fw[:k]))) + core(norm(last))
            if tuple(toks) in vset:
                return f"{last}, {' '.join(fw[:k])}", " " + " ".join(fw[k:]) + rest
    return None


def remainder_ok(rem):
    r = rem.strip()
    if not r:
        return True
    if r[0] == "(":
        return True  # "(on leave)", "(appointment starts July 1, 2017)"
    if r[0] in ",;:|-–—/":
        rest = r.lstrip(",;:|-–—/ ")
        if not rest:
            return True
        return bool(re.match(r"^\S*\s*\S*\s*\S*", rest)) and bool(TITLE_RX.match(rest) or re.match(r"^(\S+\s+){0,3}" + TITLE_RX.pattern, rest, re.I)) and len(rest) <= 300
    if r[0].islower():
        return False  # bio sentence: "X is a composer ..."
    # title in the same block as the name ("Dan Trueman Professor of Music"): first words must be a title
    return bool(re.match(r"^(\S+\s+){0,4}" + TITLE_RX.pattern, r, re.I)) and len(r) <= 300


def find(blocks, pi):
    vset = variants(pi)
    hits = []
    n = len(blocks)
    i = 0
    while i < n:
        kind, text = blocks[i]
        if len(text) > 400:
            i += 1
            continue
        r = split_name_prefix(text, vset)
        if not r or not remainder_ok(r[1]):
            i += 1
            continue
        name_written, rem = r
        start = i
        # skip duplicate name blocks (e.g. h2 name then link name)
        j = i
        while j + 1 < n and split_name_prefix(blocks[j + 1][1], vset) and not split_name_prefix(blocks[j + 1][1], vset)[1].strip():
            j += 1
        if j != i:
            start = j
            kind, text = blocks[j]
            name_written, rem = split_name_prefix(text, vset)
        title_lines = []
        if rem.strip():
            title_lines.append(rem.strip(" ,;:|-–—"))
        k = start + 1
        while k < n and len(title_lines) < 4:
            kk, tt = blocks[k]
            if kk.startswith("h") and kk <= "h4" and (not TITLE_RX.search(tt) or
                                                      (SECTION_RX.search(tt) and len(tt.split()) <= 4)):
                break
            if NOT_TITLE_RX.search(tt) or len(tt) > 220 or not TITLE_RX.search(tt):
                break
            if split_name_prefix(tt, vset):
                break
            title_lines.append(tt)
            k += 1
        end = k - 1 if k - 1 >= start else start
        quote = extract.collapse(" ".join(t for _, t in blocks[start:end + 1]))
        # section heading: nearest preceding heading that reads like a section label
        name_level = kind if kind.startswith("h") else None
        section = None
        for b in range(start - 1, -1, -1):
            bk, bt = blocks[b]
            if not bk.startswith("h"):
                continue
            if name_level and bk > name_level:
                continue
            if split_name_prefix(bt, vset):
                continue
            if len(bt.split()) <= 8 and SECTION_RX.search(bt) and not NOT_SECTION_RX.search(bt):
                section = bt
                break
        hits.append({"block_index": start, "name_as_written": name_written, "quote": quote,
                     "title_lines": title_lines, "section_heading": section})
        i = end + 1
    return hits


def classify(hit, page_slot):
    tl = " | ".join(hit["title_lines"])
    sec = hit["section_heading"] or ""
    ctx = tl + " || " + sec
    emer_listing = bool(re.search(r"emerit", page_slot, re.I)) and "incl." not in page_slot
    emeritus = bool(re.search(r"emerit", ctx, re.I)) or emer_listing
    visiting = bool(re.search(r"\bvisiting\b|\bvisitors?\b", ctx, re.I))
    memoriam = bool(re.search(r"memoriam|memorial|deceased", ctx, re.I))
    has_fac_title = bool(FAC_RX.search(tl))
    nonfac_title = bool(NONFAC_RX.search(tl)) and not re.search(r"Professor|Lecturer|Faculty|Emerit", tl, re.I)
    sec_fac = bool(re.search(r"facult|emerit|professor|lecturer|directory|people", sec, re.I))
    sec_nonfac = bool(NONFAC_RX.search(sec)) and not re.search(r"facult", sec, re.I)
    slot_fac = bool(re.search(r"facult|emerit", page_slot, re.I))
    if memoriam:
        return False, "in memoriam", emeritus, visiting
    if nonfac_title:
        return False, f"non-faculty title: {tl}", emeritus, visiting
    if sec_nonfac and not has_fac_title:
        return False, f"non-faculty section: {sec}", emeritus, visiting
    if has_fac_title or sec_fac or (slot_fac and not tl):
        return True, None, emeritus, visiting
    return False, f"no faculty title or faculty section (title={tl!r}, section={sec!r})", emeritus, visiting
