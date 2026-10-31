"""Papers: which works matched to a PI are the PI's lab papers. The school basis (institution, raw string, page 1, bare
unit names, an advisee at the school, an unaffiliated byline with an advisee), identity, the appointment, the recovered
rows, namesakes, not-papers, books and editions.
R-PAP-08 .. R-PAP-26 (see docs/RULES.md); R-PAP-01/02/03/13 come from periods, R-PAP-04 .. 07 from identity."""
import collections, gzip, html, json, re, unicodedata, zlib

import school_config as _S  # the school charters (R-PAP-15's foreign-title exception)
from .common import OWN_UNITS, SCHOOL_LOOSE, TODAY, WINDOW_START, ndoi, norm_title
from .names import NICK, _nick_pairs, byline_name, full_pair, toks
from .periods import contains, same_year, transition_side
from . import identity

# Recovered lab-paper rows, hierarchy/<school>/<kind>-recovered.jsonl.gz, as (kind, identity label): tools/dblp_recover.py
# and tools/labpage_recover.py. EXTENSION POINT: a new reviewed paper source (hierarchy/<school>/labpage-additions.json,
# docs/LAB-PAGES.md) is added here, by the coordinator.
RECOVERED_KINDS = [('dblp', 'dblp_person_page'), ('labpage', 'labpage_listing')]

EN_WORDS = set('the of and for in a an to with on from by at as is are its into via toward towards using'.split())
FOREIGN_WORDS = set('''der die das und eine einer einen ein einführung mit für von zur zum im über des den dem
le la les de des et une un du pour avec dans sur par aux au à
el los las del y una para con en por al
il gli della delle dei per nel nella
os da do das dos uma com'''.split()) - EN_WORDS


def foreign_title(title):
    """The title reads as German, French, Spanish, Italian or Portuguese, not English: two or more words, at least one
    of those languages' function words, and no English function word."""
    w = [x for x in re.split(r"[^\w']+", unicodedata.normalize('NFC', str(title or '')).lower()) if x and not x.isdigit()]
    return len(w) >= 2 and any(x in FOREIGN_WORDS for x in w) and not any(x in EN_WORDS for x in w)


def fold_books(rows, school):
    """Books are one work, and a translation is not new work (2026-10-29, owner: best judgement; Leiserson's lab had 131
    chapters of the German and French editions of CLRS): (a) a run of 5+ book chapters of one PI with one venue and one
    year is one book: the chapters fold into the book's own record, or into one chapter standing for the book when the
    book has no record (marked chapters_folded, in place); (b) outside EPFL (French- and German-speaking), a book or
    chapter whose title reads as German, French, Spanish, Italian or Portuguese and not English is a translated edition.
    (c) (R-PAP-21, 2026-10-29, owner: accuracy sample) a chapter with no venue is grouped by its DOI's book prefix
    ('10.1145/3241304.3241312' -> '10.1145/3241304'): every such chapter folds into the lab's own book record with that DOI
    (Aviad Rubinstein's 16 chapters of his 2019 ACM Books monograph sat beside the book), and 5+ of them with no book
    record fold into one chapter as in (a).
    Returns (rows kept, chapters folded, translated editions dropped or None at EPFL)."""
    runs = collections.defaultdict(list)
    for i, r in enumerate(rows):
        if r.get('type') == 'book-chapter' and r.get('venue'):
            runs[(r['pi'], r['venue'], r.get('year'))].append(i)
        elif r.get('type') == 'book-chapter' and doi_book_prefix(r.get('doi')):
            runs[(r['pi'], 'doi:' + doi_book_prefix(r.get('doi')), None)].append(i)
    books = {(r['pi'], r.get('venue'), r.get('year')) for r in rows if r.get('type') == 'book'} \
        | {(r['pi'], 'doi:' + ndoi(r.get('doi')), None) for r in rows if r.get('type') == 'book' and r.get('doi')}
    fold = set()
    for k, ix in runs.items():
        if len(ix) >= 5 or (k[1].startswith('doi:') and k in books):
            keep = [] if k in books else [min(ix, key=lambda i: len(rows[i].get('title') or ''))]
            if k in books:  # the book's own record says how many chapters it stands for
                for r in rows:
                    if r.get('type') == 'book' and r['pi'] == k[0] and (k[1] == r.get('venue') and k[2] == r.get('year') or k[1] == 'doi:' + ndoi(r.get('doi'))):
                        r['chapters_folded'] = r.get('chapters_folded', 0) + len(ix)
            for i in keep:
                rows[i]['chapters_folded'] = len(ix)
            fold |= set(ix) - set(keep)
    folded, translated = len(fold), None
    if not _S.field(_S.get(school), 'rules.foreign_title_exception'):  # R-PAP-15 (EPFL's French titles are originals)
        tr = {i for i, r in enumerate(rows) if i not in fold and r.get('type') in ('book', 'book-chapter') and foreign_title(r.get('title'))}
        translated = len(tr); fold |= tr
    return [r for i, r in enumerate(rows) if i not in fold], folded, translated


def doi_book_prefix(doi):
    """The book DOI a chapter DOI extends: '10.1145/3241304.3241312' -> '10.1145/3241304', '10.1007/978-3-030-1-6_5' ->
    '10.1007/978-3-030-1-6'; None when the DOI has no such suffix."""
    m = re.match(r'(10\.\d+/[^/]+?)[._]([^._/]+)$', ndoi(doi))
    return m.group(1) if m else None


# ---- not papers (R-PAP-18, R-PAP-19, R-PAP-22; 2026-10-29, owner: accuracy sample) ---------------------------------
# Each pattern was tested against every lab paper of the 2026-10-29 build (counts and samples in docs/RULES.md); the
# patterns are anchored so that research papers that merely mention the words stay ('Puzzles in Memory of Solomon
# Golomb', 'Remembering the "when"', 'Contraction theory ...: A tutorial overview', 'MedAL: ...').
SUPPLEMENT_TITLE = re.compile(r'(?i)^\s*(moesm\d+|additional file \d+|supplement \d+\s*:|supplementa(?:ry|l) (?:material|information|data|file|figure|table)s?\b|'
                              r'code and data for|data,? (?:materials,? )?and code for|data for (?:the )?paper|artifacts? (?:for|of)\b|'
                              r'reproduction package|replication (?:package|data|code)|research data for|source code for)'
                              r'|\((?:[\w ]+ )?artifact\)\s*$|\bdata (?:&|and) materials\s*$')
ERRATUM_TITLE = re.compile(r'(?i)^\s*(?:publisher|author)s?[’\']?\s+correction\b|^\s*correction(?: to)?\s*:|^\s*erratum\b|^\s*corrigendum\b')
EDITORIAL_TITLE = re.compile(r"(?i)^\s*(guest[- ]editorial|editorial\b|foreword\b|preface\b|from the (?:guest )?editors?\b|"
                             r"(?:guest )?editors?['’]? (?:introduction|note|preface|message)|editor['’]?s? note|"
                             r"introduction to the (?:\w+ )?(?:special|focus|featured|themed) (?:issue|section)|"
                             r"message from the (?:general |program |conference )?(?:co-?)?chairs?|in this issue\b|letter from the editor)")
AWARD_TITLE = re.compile(r"^\d{4} .*\b(Award|Prize|Medal)\b|\b(Award|Prize|Medal)\b\s*(given to|:)\s*[A-Z][\w.'-]+( [A-Z][\w.'-]+){1,3}\s*$")
AWARD_END = re.compile(r'\b(Award|Prize|Medal)\s*$')
WORKSHOP_TITLE = re.compile(r'(?i)^(?:the )?(?:\d+(?:st|nd|rd|th) )?(?:international |joint )?workshop on\b|^tutorial\s*:|'
                            r':\s*an? (?:collaborative |interactive |half-day |full-day |hands-on )?workshop (?:on|with|for)\b|'
                            r'\b(?:workshop|tutorial|panel) proposal\b')
TUTORIAL_ON = re.compile(r'(?i)^tutorial on\b')
HIGHLIGHTS_TITLE = re.compile(r',\s*No\.\s*\d+\s*$|^(?i:research )?(?i:highlights)\b')
TRIBUTE_TITLE = re.compile(r"(?i)^\s*(in memoriam|obituary|in memory of|a tribute to|tribute to)\b")
LIFE_DATES = re.compile(r"^\s*([A-Z][\w.'’‘\- ]{2,60}?)\s*\((?:19|20)\d\d\s*[-–]\s*(?:19|20)\d\d\)\s*$")
COMMON_WORD_NAMES = set('art ray grace hope faith joy rose may june april august bill will mark gene rich frank sky dawn crystal amber '
                        'pat sue silence lane chase cash case king page miles bob summer autumn winter spring river'.split())
NOUN_SUFFIX = re.compile(r'(?:tion|sion|ing|ity|ics|ness|ment|ology|ism|ance|ence|ure|ship|ware|s)$', re.I)
GIVEN_NAMES = None  # every given name of the nickname tables, read once


def given_names():
    global GIVEN_NAMES
    if GIVEN_NAMES is None:
        GIVEN_NAMES = {x for pr in _nick_pairs() for x in pr} | set(NICK) | set(NICK.values())
    return GIVEN_NAMES


def person_name_title(title):
    """The whole title is a person's name: two or three capitalized words (a middle initial allowed), the first a given name
    of the nickname tables that is not a common word, the last not shaped like a noun ('Derek Chiou', an IEEE Micro
    tribute; not 'Art Gallery', 'Silence Localization', 'Ray Tracing Harmonic Functions')."""
    w = str(title or '').strip().rstrip('.').split()
    if not 2 <= len(w) <= 3 or not all(re.fullmatch(r"[A-Z][a-zà-ÿ'’\-]+|[A-Z]\.", x) for x in w) or len(w[-1]) < 3:
        return False
    first = w[0].lower()
    return first in given_names() and first not in COMMON_WORD_NAMES and len(first) >= 3 and not NOUN_SUFFIX.search(w[-1])


ABSTRACT_VENUE = re.compile(r'(?i)meeting abstracts|bulletin of the american physical society|\bISMRM\b|international society for magnetic '
                            r'resonance in medicine|abstracts? (?:book|volume)|conference abstracts|EGU General Assembly')
ABSTRACT_DOI = re.compile(r'(?i)^10\.58530/|^10\.5194/(?:egusphere|epsc|wbf)|meetingabstract|supp(?:l)?[._\-]|supplement|\.am20\d\d|\.canevol|'
                          r'/ma20\d\d|^10\.1182/blood-20\d\d-')
ABSTRACT_TITLE = re.compile(r'(?i)^\s*abstract\s+[A-Z]{0,4}[-\s]?\d+\s*[:.]')
ABSTRACT_JOURNALS = re.compile(r'(?i)^(cancer research|circulation|blood|stroke|sleep|journal of clinical oncology|the journal of the acoustical society|'
                               r'biophysical journal|the journal of immunology|neuro-oncology|clinical cancer research|cancer immunology research|'
                               r'journal of the american society of nephrology|innovation in aging|arteriosclerosis|open forum infectious|'
                               r'genetics in medicine|schizophrenia bulletin|structural dynamics|academy of management proceedings|'
                               r'regular and young investigator|the faseb journal|neurology|biological psychiatry|value in health|'
                               r'annals of the rheumatic diseases|american journal of respiratory and critical care|journal of thoracic oncology)')
THESIS_REPOSITORY_DOI = re.compile(r'^10\.25740/')  # Stanford Digital Repository (purl.stanford.edu): theses, honors theses, capstones


def not_a_paper(r):
    """Why a lab-paper row is not a paper, or None (2026-10-29, owner: accuracy sample). `r` is a lab-paper row (title,
    venue, type, doi, byline, authorship.position). The tags:
      R-PAP-18 (R1) software_record, repository_supplement (incl. protocols.io), erratum, machine_translation,
               dagstuhl_report, oberwolfach_report, editorial, award_announcement, workshop_proposal, highlights_column,
               tribute
      R-PAP-19 (R2) meeting_abstract:<venue|doi|title|journal|single_author|keynote>
      R-PAP-22 (R5) dissertation (the PI is the adviser, not the author)."""
    t = str(r.get('title') or '').strip(); v = str(r.get('venue') or ''); d = ndoi(r.get('doi')); ty = r.get('type') or ''
    nb = len(r.get('byline') or [])
    pos = (r.get('authorship') or {}).get('position')
    # R5: dissertations and theses are the student's; the PI on their byline is the adviser
    if ty == 'dissertation' and not (nb == 1 and pos == 'first'):
        return 'dissertation'
    if THESIS_REPOSITORY_DOI.match(d) and pos != 'first':
        return 'dissertation'
    # R1: repository records and paratext
    if ty == 'software':
        return 'software_record'
    if SUPPLEMENT_TITLE.search(t) or d.startswith('10.17504/protocols.io'):
        return 'repository_supplement'
    if ERRATUM_TITLE.search(t):
        return 'erratum'
    if '【Powered by NICT】' in t:
        return 'machine_translation'  # JST's machine-translated Japanese record of a paper (CMU, OpenPose)
    if re.search(r'(?i)dagstuhl (?:reports|manifestos)', v) or re.match(r'10\.4230/(?:dagrep|dagman)\b', d) or re.search(r'\(Dagstuhl Seminar \d+\)\s*$', t):
        return 'dagstuhl_report'
    if re.search(r'(?i)oberwolfach', v) or d.startswith('10.4171/owr'):
        return 'oberwolfach_report'
    if EDITORIAL_TITLE.search(t):
        return 'editorial'
    if AWARD_TITLE.search(t) or (AWARD_END.search(t) and len(t.split()) <= 8):
        return 'award_announcement'
    if WORKSHOP_TITLE.search(t) or (TUTORIAL_ON.search(t) and ty in ('conference-paper', 'conference-abstract')):
        return 'workshop_proposal'
    if HIGHLIGHTS_TITLE.search(t):
        return 'highlights_column'
    m = LIFE_DATES.match(t)
    life = m and [w for w in re.sub(r"[‘’'][^‘’']*[‘’']", ' ', m.group(1)).split() if w]  # 'Sanjiv ‘Sam’ Gambhir (1962–2020)'
    if TRIBUTE_TITLE.search(t) or person_name_title(t) or (life and len(life) <= 4 and all(w[:1].isupper() for w in life)
                                                            and life[0].lower() in given_names()):
        return 'tribute'
    # R2: meeting abstracts (owner: abstracts are not papers)
    if ABSTRACT_VENUE.search(v):
        return 'meeting_abstract:venue'
    if ABSTRACT_DOI.search(d) and ty in ('conference-abstract', 'article', 'other', 'paratext'):
        return 'meeting_abstract:doi'
    if ABSTRACT_TITLE.search(t):
        return 'meeting_abstract:title'
    if ty == 'conference-abstract' and ABSTRACT_JOURNALS.search(v):
        return 'meeting_abstract:journal'
    if ty == 'conference-abstract' and nb == 1:
        return 'meeting_abstract:single_author'
    if ty == 'conference-abstract' and re.search(r'(?i)\bkeynote\b|\binvited talk\b', t):
        return 'meeting_abstract:keynote'
    return None


def doi_year_conflict(r):
    """R-PAP-23 (2026-10-29, build; the Manning row the accuracy sample found): a record that claims to be a DROPS venue
    publication (not a preprint) whose DOI names a venue year two or more years after the record's own date mixes two
    works. OpenAlex's W3011573503 (Stanza's 2020 arXiv record, Manning's ORCID authorship) carried the title and DOI
    of an unrelated SLATE 2023 paper in the 2026-10-21 sweep snapshot; the edition merge was not involved."""
    m = re.match(r'10\.4230/(?:lipics|oasics)\.[a-z0-9\-]+\.(\d{4})\.', ndoi(r.get('doi')))
    return bool(m and r.get('type') != 'preprint' and r.get('year') and int(m.group(1)) >= int(r['year']) + 2)


def norm_unit(s):
    """A unit name for comparison: lowercase ASCII, '&' as 'and', no 'Department of' / 'Dept. of' / 'School of', no
    punctuation ('Operations Research & Financial Engineering' == 'Department of Operations Research and Financial
    Engineering')."""
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower().replace('&', ' and ')
    s = re.sub(r'\b(?:the|department|dept|of|school|division|program|programme|in)\b\.?', ' ', s)
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', s).split())


PLACE = re.compile(r'^(?:[a-z]+ )?(?:nj|pa|ma|ca|ny|usa|united states|switzerland|lausanne|pittsburgh|cambridge|berkeley|stanford|princeton|'
                   r'\d{4,5}(?: \d{4})?|[a-z]{2} \d{5}|ch \d{4})$')


def units_in(raw, aff):
    """The unit names in a raw affiliation string that names the school: its comma/semicolon parts before the school's
    name, minus places and postal codes ('Center for Information Technology Policy, Princeton University, Princeton, NJ'
    -> ['center for information technology policy'])."""
    m = aff.search(raw or '')
    if not m:
        return []
    out = []
    for part in re.split(r'[,;]', raw[:m.start()]):
        u = norm_unit(part)
        if len(u.split()) >= 2 and not PLACE.match(u):
            out.append(u)
    return out


DISCIPLINE_WORDS = set('''computer science sciences electrical engineering and mathematics mathematical applied physics chemistry chemical
biology biological molecular psychology statistics statistical economics mechanical aerospace civil environmental materials
neuroscience cognitive brain linguistics philosophy sociology music architecture bioengineering biomedical industrial systems
information operations research data computing computational eecs ece cs math management business medicine medical public
health technology electronics communication communications media design energy earth astronomy geosciences genetics
genomics bioinformatics engineering ee me cee mse'''.split())


def generic_unit(u):
    """A unit name every school has ('computer science', 'electrical and computer engineering', 'psychology'): all of its
    words are discipline words. 'center for information technology policy' and 'operations research and financial
    engineering' are not generic."""
    w = norm_unit(u).split()
    return bool(w) and all(x in DISCIPLINE_WORDS for x in w)


def page1_head(text, title=None):
    """The author block of a page-1 text: the text before 'Abstract' (or its first 2500 characters), without the arXiv
    stamp ('arXiv:2410.24164v1 [cs.LG] 31 Oct 2024') and without the title."""
    flat = re.sub(r'\s+', ' ', text or '')
    m = re.search(r'\babstract\b', flat[:6000], re.I)
    head = flat[:m.start()] if m else flat[:2500]
    head = re.sub(r'arXiv:\s*\d{4}\.\d{4,5}(?:v\d+)?\s*\[[^\]]*\]\s*(?:\d{1,2} \w{3} \d{4})?', ' ', head)
    if title:
        tw = [w for w in re.findall(r'\w+', title.lower()) if len(w) > 3][:12]
        if tw:  # drop the title's words (titles say 'Foundation', 'Universal', 'Meta-RL')
            head = re.sub(r'(?i)\b(?:' + '|'.join(re.escape(w) for w in tw) + r')\b', ' ', head)
    return head


AFFILIATION_MARK = re.compile(r'univ|institut|college|polytechn|[ée]cole|laborator|\blabs?\b|\binc\b|corp|\bltd\b|gmbh|\bllc\b|hospital|'
                              r'academy|google|microsoft|\bmeta\b|amazon|\bibm\b|nvidia|openai|deepmind|anthropic|foundation|\bcnrs\b|\binria\b|'
                              r'\beth\b|max planck|company|\S@\S|https?://|www\.|\.(?:com|ai|io|company|org)\b', re.I)


def page1_elsewhere(status, text, school, title=None):
    """R3 (R-PAP-20, 2026-10-29, owner: accuracy sample): page 1 of the paper, read by tools/pi_fulltext_affiliation.py,
    names neither the school (not even loosely: 'Berkeley', 'CMU', 'Lausanne', 'CSAIL') nor ties it to anyone, while its
    author block names another institution, company, e-mail or web domain: the paper was done elsewhere (pi-0: every
    author on page 1 is Physical Intelligence's, 'physicalintelligence.company'). A page with no affiliations at all
    says nothing and is kept."""
    if status != 'ok_absent' or not text:
        return None
    flat = re.sub(r'\s+', ' ', text)
    if re.search(SCHOOL_LOOSE[school], flat, re.I):
        return None
    m = AFFILIATION_MARK.search(page1_head(text, title))
    return m.group(0) if m else None


OTHER_INST = re.compile(r'univ|institut|college|polytechn|[ée]cole|laborator|\blabs?\b|\binc\b|corp|\bltd\b|gmbh|\bllc\b|hospital|academy|'
                        r'cent(?:er|re)\b|google|microsoft|\bmeta\b|amazon|\bibm\b|nvidia|openai|deepmind|foundation|\bcnrs\b|\binria\b|'
                        r'\beth\b|max planck|national|company', re.I)  # an affiliation string that names some institution, not a department


def names_other_inst(z, school):
    u = OWN_UNITS.get(school)
    return bool(OTHER_INST.search(u.sub(' ', z) if u else z))


def venue_version_date(w, venues):
    """R9 (R-PAP-26, 2026-10-29, owner: accuracy sample): (date for the appointment check, dated_by or None). A preprint or
    repository deposit (type preprint, an arXiv DOI, or a repository as the primary source) whose title is on the PI's
    DBLP person page as a venue publication (`venues`: normalized title -> (earliest venue year, DBLP key), CoRR, ECCC
    and ePrint excluded) is dated by that venue year: Engelhardt's ML4H 2023 paper had only its October 2021 arXiv
    record; Sandholm's IJCAI 2009 paper was a 2018 KiltHub deposit."""
    date = w.get('publication_date') or str(w.get('publication_year') or '')
    src = (w.get('primary_location') or {}).get('source') or {}
    deposit = w.get('type') == 'preprint' or ndoi(w.get('doi')).startswith('10.48550/') or src.get('type') == 'repository'
    vy = venues.get(norm_title(w.get('title'))) if deposit else None
    if vy and vy[0] != w.get('publication_year'):
        return str(vy[0]), dict(oa_date=date, venue_year=vy[0], dblp_key=vy[1])
    return date, None


def bare_unit_school(raws, own_units, school_units, anchored_ok, school_co):
    """R6 (R-PAP-25, 2026-10-29, owner: accuracy sample): the PI's raw affiliation strings name only units, and count as the
    school: a generic unit name ('Computer Science', which every school has) when it is the PI's own unit and another
    author on the byline lists the school; a unit name only this school has when it is the PI's own unit (census
    department, or seen with the school on 2+ of the PI's works) and the PI's identity is anchored or a school co-author
    is on the byline ('Operations Research & Financial Engineering', Sircar), or when it is any unit of the school and a
    school co-author is on the byline ('Center for Information Technology Policy', Mittal with Bhagoji)."""
    if not raws:
        return False
    for z in raws:
        u = norm_unit(z)
        if generic_unit(z):
            if not (u in own_units and school_co):
                return False
        elif not ((u in own_units and (anchored_ok or school_co)) or (u in school_units and school_co)):
            return False
    return True


def unit_tables(ctx):
    """R-PAP-25: per PI, the PI's own units at the school (census departments, and the unit names the PI's
    school-affiliated raw strings carry on 2+ works); and every unit name of the school."""
    hits, aff, pis, C = ctx.hits, ctx.aff, ctx.pis, ctx.C
    # R6 (R-PAP-25, 2026-10-29, owner: accuracy sample): the PI's own units at the school, for raw affiliation strings that
    # name only a unit ('Center for Information Technology Policy' for Prateek Mittal, 'Operations Research & Financial
    # Engineering' for Ronnie Sircar): the PI's census departments, and the unit names the PI's school-affiliated raw
    # strings carry on 2+ other works ('Center for Information Technology Policy, Princeton University')
    seen_units = collections.defaultdict(collections.Counter)
    for pi, w, a, cw, ident, page1 in hits:
        for u in {u for z in a.get('raw_affiliation_strings') or [] for u in units_in(z, aff)}:
            seen_units[pi][u] += 1
    pi_units = {p['pi']: {norm_unit(d) for d in p.get('departments') or [] if isinstance(d, str) and len(norm_unit(d).split()) >= 1}
                | {u for u, k in seen_units[p['pi']].items() if k >= 2} for p in pis}
    school_units = {u for v in pi_units.values() for u in v} | {norm_unit(u_.get('name')) for u_ in C['units'] if u_.get('name')} \
        | {u for c_ in seen_units.values() for u in c_}
    ctx.pi_units, ctx.school_units = pi_units, school_units


def venue_tables(ctx):
    """R-PAP-26 and R-PAP-19: from the DBLP dump, per PI, each venue publication's earliest year and DBLP key by
    normalized title (not CoRR, ECCC, ePrint, theses, books), and the largest author count of each title."""
    pis = ctx.pis
    DUMP_PERSONS = identity.DUMP_PERSONS
    # R9 (R-PAP-26, 2026-10-29, owner: accuracy sample): the venue version's year on the PI's DBLP person page (a record
    # that is not a CoRR preprint), by normalized title, for dating a preprint or a repository deposit
    dblp_venue, dblp_nauth = collections.defaultdict(dict), collections.defaultdict(dict)
    if DUMP_PERSONS is not None:
        for p in pis:
            for q in p['dblp']:
                for r_ in (DUMP_PERSONS['persons'].get(q) or {}).get('pubs') or []:
                    if str(r_.get('key') or '').startswith(('journals/corr/', 'journals/eccc/', 'journals/iacr/', 'phd/', 'books/', 'persons/')) or not r_.get('year'):
                        continue
                    t_ = norm_title(html.unescape(r_.get('title') or '').rstrip('.'))
                    if t_:
                        dblp_nauth[p['pi']][t_] = max(dblp_nauth[p['pi']].get(t_, 0), len(r_.get('authors') or []))
                    if t_ and (t_ not in dblp_venue[p['pi']] or r_['year'] < dblp_venue[p['pi']][t_][0]):
                        dblp_venue[p['pi']][t_] = (int(r_['year']), r_['key'])
    ctx.dblp_venue, ctx.dblp_nauth = dblp_venue, dblp_nauth


def school_basis(ctx, pi, w, a, ident, page1):
    """Why authorship `a` of `w` ties the PI to the school, as `via` (empty: no basis), and the page-1 tie used: the
    institution lineage or raw string; page 1 (R-PAP-10); a bare unit name (R-PAP-25); an advisee at the school on the
    byline (R-PAP-11); an advisee on an unaffiliated byline (R-PAP-12). Returns (via, page1)."""
    school, n, inst, aff, tied = ctx.school, ctx.n, ctx.inst, ctx.aff, ctx.tied
    pi_units, school_units, anchored = ctx.pi_units, ctx.school_units, ctx.anchored
    advisee_names, adv_full, from_pw = ctx.advisee_names, ctx.adv_full, ctx.from_pw
    p = ctx.pid0[pi]
    via = [i.get('display_name') for i in a.get('institutions') or [] if inst == i.get('id') or inst in (i.get('lineage') or [])] \
        + ['text: ' + z for z in a.get('raw_affiliation_strings') or [] if aff.search(z)]
    if page1 and not a.get('institutions') and not a.get('raw_affiliation_strings'):
        via = [f"page 1 ({page1['how']}): " + ' … '.join(page1['quotes'])]  # the paper's own first page ties the school to the PI
    elif not via and tied.get(w['id']) and any(toks(n_)[-1] in toks(' '.join(tied[w['id']]['quotes'])) for n_ in p['names'] if toks(n_)):
        # a sweep work whose OpenAlex record gives the PI no school (none, a garbled footnote string, or a co-author's
        # institution misassigned by position) while the paper's own first page, read by tools/pi_fulltext_affiliation.py,
        # ties the school to this PI by name (2026-10-29: Chi Jin, Karthik Narasimhan, Adam Perer); the primary
        # source outranks OpenAlex's derived affiliation
        page1 = tied[w['id']]; via = [f"page 1 ({page1['how']}): " + ' … '.join(page1['quotes'])]
    raws_ = a.get('raw_affiliation_strings') or []
    if not via and not a.get('institutions') and raws_ and all(norm_unit(z) in pi_units[pi] or norm_unit(z) in school_units for z in raws_):
        # R6: the PI's raw affiliation is only the name of one of the PI's own units at the school, and no institution
        # is named for the PI; it counts as the school when the PI's identity is anchored (not the advisee route) or
        # another author on the byline lists the school ('Department of Computer Science' alone is common to every
        # school, so the unit must be the PI's own and one of the two must hold)
        aid_ = (a.get('author') or {}).get('id')
        anchored_ok = (ident not in (None, 'advisee_coauthor', 'advisee_anchored_author_id')) or bool(aid_ and anchored[pi].get(aid_, 0) >= 1)
        school_co = any(x is not a and (inst in [i.get('id') for i in x.get('institutions') or []] + [l for i in x.get('institutions') or [] for l in i.get('lineage') or []]
                                        or any(aff.search(z) for z in x.get('raw_affiliation_strings') or [])) for x in w.get('authorships') or [])
        if bare_unit_school(raws_, pi_units[pi], school_units, anchored_ok, school_co):
            via = [f'school unit on the PI authorship: {raws_[0]}']; n['school_via_bare_unit'] += 1
    if not via and not a.get('institutions') and not any(names_other_inst(z, school) for z in a.get('raw_affiliation_strings') or []):
        # the PI's authorship names no institution (none, or a department only, as recent preprints do) and a stated
        # advisee of the PI on the same byline lists the school: the paper is the lab's (identity and appointment still apply)
        co = [x.get('raw_author_name') for x in w.get('authorships') or [] if x is not a and x.get('raw_author_name')
              and (inst in [i.get('id') for i in x.get('institutions') or []] + [l for i in x.get('institutions') or [] for l in i.get('lineage') or []]
                   or any(aff.search(z) for z in x.get('raw_affiliation_strings') or []))
              and any(an.match(byline_name(x['raw_author_name'])) for an in advisee_names[pi])]
        if co:
            via = [f'advisee at the school on the byline: {co[0]}']; n['school_via_advisee_coauthor'] += 1
    if not via and (pi, w['id']) in from_pw and not any(x.get('institutions') or x.get('raw_affiliation_strings') for x in w.get('authorships') or []):
        # (2026-10-29, owner) a work of the PI's own (anchored or reviewed) OpenAlex id whose byline carries no
        # institution or affiliation at all (typically an arXiv record) is the lab's when a stated advisee of the PI
        # is on that byline by full name (first given name and family name written out); identity, the appointment
        # and the paper-type checks below still apply
        co = [x.get('raw_author_name') for x in w.get('authorships') or [] if x is not a and x.get('raw_author_name')
              and full_pair(byline_name(x['raw_author_name'])) in adv_full[pi]]
        if co:
            via = [f'advisee on an unaffiliated byline: {co[0]}']; n['school_via_unaffiliated_byline_advisee'] += 1
    return via, page1


def rows_from_hits(ctx):
    """Lab-paper rows from the matched authorships: school basis, page 1 before the unaffiliated route (R-PAP-20),
    identity, venue-version dating (R-PAP-26), the appointment (R-PAP-01, R-PAP-13); a second OpenAlex record of one
    collection work becomes an edition (R-PAP-16). Returns (rows, seen keys)."""
    school, n, hits, pid0, inst, aff = ctx.school, ctx.n, ctx.hits, ctx.pid0, ctx.inst, ctx.aff
    funnel, blocked, anchored, page_read, dblp_venue = ctx.funnel, ctx.blocked, ctx.anchored, ctx.page_read, ctx.dblp_venue
    page1_samples = []
    # lab papers
    rows, seen, row_at = [], set(), {}
    for pi, w, a, cw, ident, page1 in hits:
        p = pid0[pi]
        via, page1 = school_basis(ctx, pi, w, a, ident, page1)
        unaffiliated = bool(via) and via[0].startswith('advisee on an unaffiliated byline')
        page1_check = None
        if unaffiliated:
            # R3 (R-PAP-20, 2026-10-29, owner: accuracy sample): page 1 first. A paper whose own first page names no school
            # and puts its authors at another institution or company is not the lab's (pi-0, Physical Intelligence); with no
            # page read (no arXiv copy, no local PDF) the route stands and the row is tagged page1_unchecked
            st_, blob_, url_ = page_read.get(w['id']) or (None, None, None)
            txt_ = zlib.decompress(blob_).decode('utf-8', 'replace') if blob_ else None
            elsewhere = page1_elsewhere(st_, txt_, school, w.get('title'))
            if elsewhere:
                n['unaffiliated_page1_elsewhere'] += 1; funnel[pi]['page1_elsewhere'] += 1
                if len(page1_samples) < 40:
                    page1_samples.append(dict(pi=pi, oa=w['id'], title=w.get('title'), page1=url_, mark=elsewhere))
                continue
            page1_check = dict(status=st_ or 'unchecked', url=url_) if st_ in ('ok', 'ok_absent', 'ok_untied') else dict(status='page1_unchecked', url=url_)
            n['unaffiliated_' + ('page1_unchecked' if page1_check['status'] == 'page1_unchecked' else 'page1_read_kept')] += 1
        school_aff = bool(via)
        funnel[pi]['name_hits'] += 1
        if not school_aff:
            n['hit_without_school_affiliation'] += 1; continue
        funnel[pi]['school_affiliated'] += 1
        aid = (a.get('author') or {}).get('id')
        identity = None if aid in blocked[pi] else ident or (('anchored_author_id' if anchored[pi][aid] >= 1 else 'advisee_anchored_author_id') if aid and anchored[pi].get(aid) else None)
        if identity is None:
            n['hit_without_identity'] += 1; continue
        funnel[pi]['identity'] += 1
        date = w.get('publication_date') or str(w.get('publication_year') or '')
        # R9: a preprint or repository deposit is dated by its venue version on the PI's DBLP page
        date, dated_by = venue_version_date(w, dblp_venue[pi])
        if dated_by:
            n['dated_by_venue_version'] += 1
            if dated_by['venue_year'] < WINDOW_START:
                # the venue version predates the atlas window (2016-2026): a later deposit or preprint of an older paper
                # is not a lab paper of the window (Sandholm's IJCAI 2009 paper, a 2018 KiltHub deposit)
                n['dated_before_window'] += 1; funnel[pi]['dated_before_window'] += 1; continue
        per = next((q for q in p['periods'] if contains(q['start'], q['end'], date, q['asof'] or TODAY) == 'supported'), None)
        lst = None
        if per is None:
            y = same_year(date); lst = next((l for l in p['listings'] if l['year'] == y), None) if y else None
        if per is None and lst is None:
            n['outside_appointment'] += 1; funnel[pi]['outside_appointment_' + str(w.get('publication_year'))] += 1; continue
        if unaffiliated and per is None and transition_side(p, lst, date) == 'outside':
            # (2026-10-29, owner: best judgement) a byline with no affiliations says nothing about where the work was done,
            # so in a PI's arrival or departure year a listing proves only its own side of the capture date: Thomas
            # Griffiths's last Berkeley listing is April 2018 and he moved to Princeton that July, so an unaffiliated
            # September 2018 preprint is not a Berkeley lab paper (an affiliated one still is)
            n['unaffiliated_transition_year_outside'] += 1; funnel[pi]['transition_year_outside'] += 1; continue
        funnel[pi]['in_appointment'] += 1
        k = (pi, cw or w['id'])
        if k in seen:
            # a second OpenAlex record of the same collection work (2026-10-29): kept as an edition of the row already
            # made, with its own byline, so the lab's students on it are seen (EPFL 'Lê-Nguyên, Hoang', CMU 'Cui, Catherine')
            if k in row_at and w['id'] != rows[row_at[k]]['oa']:
                rows[row_at[k]].setdefault('_dups', []).append(dict(
                    oa=w['id'], work=cw, doi=ndoi(w.get('doi')), year=w.get('publication_year'), venue=((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
                    byline=[(x.get('raw_author_name') or (x.get('author') or {}).get('display_name')) for x in w.get('authorships') or []],
                    byline_school=[(x.get('raw_author_name') or (x.get('author') or {}).get('display_name')) for x in w.get('authorships') or []
                                   if inst in [i.get('id') for i in x.get('institutions') or []] + [l for i in x.get('institutions') or [] for l in i.get('lineage') or []]
                                   or any(aff.search(z) for z in x.get('raw_affiliation_strings') or [])]))
            continue
        seen.add(k); row_at[k] = len(rows)
        rows.append(dict(pi=pi, work=cw, oa=w['id'], doi=ndoi(w.get('doi')), title=w.get('title'), year=dated_by['venue_year'] if dated_by else w.get('publication_year'), date=date, type=w.get('type'),
                         venue=((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
                         landing=(w.get('primary_location') or {}).get('landing_page_url'),
                         byline=[(x.get('raw_author_name') or (x.get('author') or {}).get('display_name')) for x in w.get('authorships') or []],
                         byline_school=[(x.get('raw_author_name') or (x.get('author') or {}).get('display_name')) for x in w.get('authorships') or []
                                        if inst in [i.get('id') for i in x.get('institutions') or []] + [l for i in x.get('institutions') or [] for l in i.get('lineage') or []]
                                        or any(aff.search(z) for z in x.get('raw_affiliation_strings') or [])],
                         authorship=dict(position=a.get('author_position'), raw_name=a.get('raw_author_name'), author_id=aid,
                                         institutions=[i.get('display_name') for i in a.get('institutions') or []], raw_affiliations=a.get('raw_affiliation_strings') or [],
                                         school_via=via[:3], page1=dict(url=page1['url'], pdf_sha256=page1['pdf_sha256'], how=page1['how'], quotes=page1['quotes']) if page1 and via[0].startswith('page 1') else None),
                         identity=identity, appointment=dict(periodId=per['id']) if per else dict(listing=lst),
                         **({'dated_by': dated_by} if dated_by else {}),
                         **({'page1_check': page1_check} if page1_check else {}),
                         **({'flags': ['page1_unchecked']} if page1_check and page1_check['status'] == 'page1_unchecked' else {})))
    ctx.page1_samples = page1_samples
    return rows, seen


def recovered_rows(ctx, rows, seen):
    """Rows from RECOVERED_KINDS: inside the appointment, one per (PI, work); appended to `rows`."""
    HERE, school, n, pid0, cwork = ctx.here, ctx.school, ctx.n, ctx.pid0, ctx.cwork
    # papers on the PI's own DBLP page that only DOI-resolved OpenAlex records or the paper's first page tie to the school
    # (tools/dblp_recover.py -> hierarchy/<school>/dblp-recovered.jsonl.gz), and likewise papers the PI's own lab
    # publications page lists (tools/labpage_recover.py -> hierarchy/<school>/labpage-recovered.jsonl.gz, key 'labpage:<sha1>')
    for kind, label in RECOVERED_KINDS:
        rf = HERE / 'hierarchy' / school / f'{kind}-recovered.jsonl.gz'
        for x in (json.loads(l) for l in gzip.open(rf, 'rt')) if rf.exists() else []:
            p = pid0.get(x['pi'])
            if not p:
                continue
            ev = x['evidence']; date = str(x['year'])
            via = ev.get('school_via') or [f"page 1 ({ev.get('how')}): " + ' … '.join(ev.get('quotes') or [])]
            per = next((q for q in p['periods'] if contains(q['start'], q['end'], date, q['asof'] or TODAY) == 'supported'), None)
            lst = None if per else next((l for l in p['listings'] if l['year'] == int(x['year'])), None)
            if per is None and lst is None:
                n[f'{kind}_recovered_outside_appointment'] += 1; continue
            cw = cwork(dict(doi=x.get('doi'), title=(x.get('title') or '').rstrip('.'), publication_year=x['year'])) or None
            oa_id = ev.get('oa') or (f"https://dblp.org/rec/{x['dblp_key']}" if kind == 'dblp' else x['key'])
            if (x['pi'], cw or oa_id) in seen:
                continue
            seen.add((x['pi'], cw or oa_id))
            rows.append(dict(pi=x['pi'], work=cw, oa=oa_id, doi=x.get('doi'), title=(x.get('title') or '').rstrip('.'), year=x['year'], date=date, type='article',
                             venue=x.get('venue'), landing=ev.get('url'), byline=x.get('byline') or [], byline_school=[],
                             authorship=dict(position=None, raw_name=None, author_id=None, institutions=[], raw_affiliations=[], school_via=via[:3],
                                             page1=dict(url=ev.get('url'), pdf_sha256=ev.get('pdf_sha256'), how=ev.get('how'), quotes=ev.get('quotes')) if ev.get('how') else None),
                             identity=label, appointment=dict(periodId=per['id']) if per else dict(listing=lst), source=f'{kind}_recover:' + ev['basis']))
            n[f'{kind}_recovered_lab_papers'] += 1


def drop_namesakes(rows, pis, reviewed_oa, n):
    """R-PAP-14: when two PIs claim one paper through the same byline name, the PI holding that author id as a reviewed
    id keeps it; else the PI whose given names the byline spells out; else neither."""
    # namesake PIs (2026-10-28: Philip / Simon Wong, Hari / Hamsa Balakrishnan, Jean-Philippe / Patrick Thiran): when two
    # PIs claim one paper through the same byline name, the PI holding that author id as a reviewed id keeps it; else the
    # PI whose given names the byline spells out; a byline with initials only that no reviewed id settles goes to neither
    def given_words(names, raw=None):
        out = set()
        for nm_ in ([raw] if raw is not None else names):
            t_ = [w for w in re.split(r"[\s.\-]+", unicodedata.normalize('NFKD', str(nm_ or '')).encode('ascii', 'ignore').decode().lower().replace(',', ' ')) if w]
            if ',' in str(nm_):  # 'Wong, H. -S. Philip'
                t_ = t_[1:] + t_[:1]
            out |= {w for w in t_[:-1] if len(w) > 1}
        return out
    pi_given = {p['pi']: given_words(p.get('names') or [p['pi']]) for p in pis}
    claims = collections.defaultdict(list)
    for i, r in enumerate(rows):
        a = r.get('authorship') or {}
        if a.get('raw_name'):
            claims[(r['oa'], a['raw_name'].lower(), a.get('position'))].append(i)
    drop = set()
    for k, ix in claims.items():
        if len({rows[i]['pi'] for i in ix}) < 2:
            continue
        aid = (rows[ix[0]].get('authorship') or {}).get('author_id')
        owners = [i for i in ix if aid and aid in reviewed_oa[rows[i]['pi']]]
        if not owners:
            words = given_words(None, rows[ix[0]]['authorship']['raw_name'])
            owners = [i for i in ix if words and words <= pi_given[rows[i]['pi']]] if words else []
        if len({rows[i]['pi'] for i in owners}) != 1:
            owners = []
        drop |= set(ix) - set(owners)
    n['namesake_claims_dropped'] = len(drop)
    rows = [r for i, r in enumerate(rows) if i not in drop]
    return rows


def drop_not_papers(rows, dblp_nauth, n):
    """R-PAP-17 .. R-PAP-19, R-PAP-22, R-PAP-23: rows that are not papers leave the lab, counted per tag with samples.
    Returns (rows kept, samples)."""
    # not papers (R-PAP-18/19/22, 2026-10-29, owner: accuracy sample): repository records, paratext, seminar and workshop
    # reports, award announcements, tributes, meeting abstracts and dissertations leave the lab (not_a_paper); and a
    # record whose DOI belongs to another work (R-PAP-23, doi_year_conflict). Counted per tag, with samples, in the report.
    kept_, not_paper_samples = [], collections.defaultdict(list)
    for r in rows:
        why = not_a_paper(r) or ('doi_year_conflict' if doi_year_conflict(r) else None)
        if why == 'meeting_abstract:single_author' and dblp_nauth[r['pi']].get(norm_title(r.get('title')), 0) >= 2:
            why = None  # OpenAlex cut the byline: the PI's DBLP page has the paper with co-authors, so it is no keynote
            n['single_author_abstract_kept_dblp_coauthors'] += 1
        if why:
            n['not_paper:' + why] += 1
            if len(not_paper_samples[why]) < 10:
                not_paper_samples[why].append(dict(pi=r['pi'], oa=r['oa'], title=r.get('title'), venue=r.get('venue'), type=r.get('type'), doi=r.get('doi')))
        else:
            kept_.append(r)
    n['not_paper_dropped'] = len(rows) - len(kept_); rows = kept_
    return rows, not_paper_samples


def merge_editions(rows, n):
    """R-PAP-16: one record per unique paper and lab; editions share a normalized title, the published edition leads,
    and every edition's byline is kept for the links (`_bylines`)."""
    # one record per unique paper and lab: editions (arXiv preprint, conference, journal version) share a normalized
    # title; the published edition leads (a DOI that is not arXiv's, then a collection work), the rest are its editions
    def rank(r):
        d = r.get('doi') or ''
        return (0 if d and not d.startswith('10.48550') else 1, 0 if r['work'] else 1, -(int(r['year'] or 0)))
    grouped = collections.defaultdict(list)
    for r in rows:
        grouped[(r['pi'], norm_title(r.get('title'))[:150] or r['oa'])].append(r)
    rows = []
    for g in grouped.values():
        g.sort(key=rank); lead = dict(g[0])
        dups = [d for x in g for d in x.get('_dups') or []]
        lead['editions'] = [dict(oa=x['oa'], work=x['work'], doi=x.get('doi'), year=x['year'], venue=x.get('venue')) for x in g[1:]] \
            + [{k_: d[k_] for k_ in ('oa', 'work', 'doi', 'year', 'venue')} for d in dups]
        # every edition's byline counts for the lab's students (2026-10-29): a lead record can carry a cut byline (Freedman's
        # 'Poor Video Streaming Performance Explained' lead names only him) or another name form than its preprint
        lead['_bylines'] = [(x['byline'], x['byline_school']) for x in g] + [(d['byline'], d['byline_school']) for d in dups]
        lead.pop('_dups', None)
        rows.append(lead)
    n['edition_records_merged'] = sum(len(g) - 1 for g in grouped.values())
    return rows


def lab_papers(ctx):
    """Every lab paper of the school: ctx.rows (with `_bylines` until the package is written)."""
    school, n, pis = ctx.school, ctx.n, ctx.pis
    funnel = collections.defaultdict(collections.Counter)
    ctx.funnel = funnel
    unit_tables(ctx)
    venue_tables(ctx)
    rows, seen = rows_from_hits(ctx)
    recovered_rows(ctx, rows, seen)
    rows = drop_namesakes(rows, pis, ctx.reviewed_oa, n)
    rows, not_paper_samples = drop_not_papers(rows, ctx.dblp_nauth, n)
    # books are one work, and a translation is not new work (2026-10-29, owner: best judgement): fold_books
    nv0 = sum(r.get('type') == 'book-chapter' and not r.get('venue') for r in rows)
    rows, n['book_chapters_folded'], translated = fold_books(rows, school)
    n['book_chapters_folded_by_doi_prefix'] = nv0 - sum(r.get('type') == 'book-chapter' and not r.get('venue') for r in rows)
    if translated is not None:
        n['translated_editions_dropped'] = translated
    rows = merge_editions(rows, n)
    n['lab_papers'] = len(rows); n['lab_papers_in_collection'] = sum(bool(r['work']) for r in rows); n['lab_papers_new'] = n['lab_papers'] - n['lab_papers_in_collection']
    n['lab_papers_by_period'] = sum('periodId' in r['appointment'] for r in rows); n['lab_papers_by_listing'] = n['lab_papers'] - n['lab_papers_by_period']
    n.update({'identity:' + k: v for k, v in collections.Counter(r['identity'] for r in rows).items()})
    ctx.rows, ctx.not_paper_samples = rows, not_paper_samples
