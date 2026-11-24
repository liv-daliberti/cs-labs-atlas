"""Papers: which works matched to a PI are the PI's lab papers. The school basis (institution, raw string, page 1, bare
unit names, an advisee at the school, an unaffiliated byline with an advisee), identity, the appointment, the recovered
rows, namesakes, not-papers, books and editions.
R-PAP-08 .. R-PAP-26 (see docs/RULES.md); R-PAP-01/02/03/13 come from periods, R-PAP-04 .. 07 from identity."""
import collections, gzip, html, json, re, unicodedata, zlib

import atlas_paths as P  # data paths (DATA_FILES)
import school_config as _S  # the school charters (R-PAP-15's foreign-title exception)
from .common import NOT_PAPERS, OWN_UNITS, SCHOOL_LOOSE, TODAY, WINDOW_START, accepted_additions, excluded_school_only, ndoi, norm_title, related_gate, school_scope_work
from .identity import in_blocked_cluster
from .names import NICK, _nick_pairs, byline_name, full_pair, name_toks, toks, Name, quotes_name_pi, tie_for_pi  # noqa: F401
from .periods import _year, before_window, LISTING_BRIDGE, bridge_periods, listing_bridge_periods, contains, same_year, transition_side, transition_status
from . import identity, primary_affiliations, recovery_reviews, reviewed_claims, source_metadata, title_enrichment, primary_publications, recovered_dates
from dblp_dump_pages import page_count  # noqa: E402  (DBLP's `pages` string -> number of pages; R-PAP-27)

# Recovered lab-paper rows as (kind, identity label): hierarchy/<school>/<kind>-recovered.jsonl.gz (tools/dblp_recover.py,
# tools/labpage_recover.py), and the accepted lab-page additions (labpage-additions.json `papers`, LP-PAP-01, gated by
# labpage-acceptance.json; 2026-10-31). EXTENSION POINT: a new reviewed paper source is one more entry here and in
# recovered_source.
RECOVERED_KINDS = [('dblp', 'dblp_person_page'), ('labpage', 'labpage_listing'), ('labpage_addition', 'labpage_listing'), ('publisher', 'reviewed_primary_publisher')]


def recovered_source(ctx, kind):
    """The rows of one RECOVERED_KINDS kind, in the recovered-row format {pi, key, title, year, doi, venue, byline, evidence}."""
    if kind == 'publisher':
        return primary_publications.rows(ctx)
    if kind == 'labpage_addition':
        return accepted_additions(ctx.school, 'papers', ctx.here, ctx.n)
    rf = P.data(f'{kind}-recovered.jsonl.gz', ctx.school, root=ctx.here)
    return (json.loads(l) for l in gzip.open(rf, 'rt')) if rf.exists() else []

# Interrogatives are English function words too: Portuguese 'do' alone must not classify an English question as foreign.
EN_WORDS = set('the of and for in a an to with on from by at as is are its into via toward towards using '
               'how what why where when which who whose whom whether'.split())
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
ERRATUM_TITLE = re.compile(r'(?i)^\s*(?:publisher|author)s?[’\']?\s+correction\b|^\s*correction(?: to)?\s*:|^\s*erratum\b|^\s*corrigendum\b|^\s*corrections?\s+to\s+["“”‘’\']')
EDITORIAL_TITLE = re.compile(r"(?i)^\s*(guest[- ]editorial|(?:inaugural )?editorial\b|foreword\b|preface\b|from the (?:guest )?editors?\b|"
                             r"welcome to [\w .&-]+\s+\d+\(\d+\)\s*$|"
                             r"(?:guest )?editors?['’]? (?:introduction|note|preface|message)|editor['’]?s? note|"
                             r"introduction to the (?:\w+ )?(?:special|focus|featured|themed) (?:issue|section)|"
                             r"message from the (?:general |program |conference )?(?:co-?)?chairs?|in this issue\b|letter from the editor)")
# An explicit final genre label is also paratext, even when the issue's subject
# precedes it. Requiring paired brackets and the whole label preserves research
# about editorial work and ordinary papers whose titles contain "introduction".
_GUEST_EDITORIAL_LABEL = r"\s*guest[- ]editors?(?:['’]s?)?\s+(?:introduction|preface|note|message)\s*"
BRACKETED_EDITORIAL_TITLE = re.compile(r'(?i)(?:\[' + _GUEST_EDITORIAL_LABEL + r'\]|\(' + _GUEST_EDITORIAL_LABEL + r'\))\s*\.?\s*$')
# Issue front matter can put the journal/volume before "Editorial". Require the complete issue-label shape,
# not merely the word, so research studying editorial decisions remains eligible.
ISSUE_EDITORIAL_TITLE = re.compile(r'(?is)^\s*[\w.&-]+,?\s+v(?:ol(?:ume)?)?\.?\s*\d+\b'
                                   r'.*?\bn(?:o)?\.?\s*\d+\b.*?\b(?:19|20)\d{2}\s+editorial\b'
                                   r'(?:\s+[a-z]+\d+)?\s*\.?\s*$')
# R-PAP-40 (b) (2026-11-12, stage-9 genre rules): 'Custom Sub-Systems and Circuits for Deep Learning: Guest Editorial Overview' (the label comes last), and
# OpenAlex type `editorial` (an NEJM AI editorial with a research-like title). EDITORIAL_TYPE_DROPS is the owner's switch: R-PAP-18 (2026-10-29) kept the
# type alone, because research-like titles carry it (coordinator 2026-11-12: default OFF; the switch stays for the owner). ON drops about 437 lab-paper rows.
GUEST_EDITORIAL_ANYWHERE = re.compile(r'(?i)\bguest[- ]editorial\b')
EDITORIAL_TYPE_DROPS = False
# R-PAP-40 (c): 'Reply to: The overwhelming role of ballistic photons ...' (Nature Communications Matters Arising reply, typed letter). OWNER DECISION
# (owner 2026-11-12: ON): a reply is the authors' own short research output but answers another paper.
REPLY_TO_LETTERS_DROP = True   # owner 2026-11-12: switched ON
REPLY_TO_COLON_TITLE = re.compile(r'(?i)^\s*reply to\s*:')
# R-PAP-40 (d) (2026-11-12): proceedings front matter. A bare workshop/conference acronym with a two-digit year is the volume's own title ("ADVM'21", "MM'21");
# always dropped (`proceedings_volume`). The abstract/tutorial family below is a policy question (owner R2 pending since 2026-10-29), so its switch is OFF:
# an ACL-anthology tutorial abstract (DOI `...-tutorials.N`), an all-caps title under an Elsevier dated DOI (Eur Neuropsychopharmacology congress abstracts; all-caps titles alone are not enough: Journal of Symbolic Logic prints them), a
# supplement-style Elsevier DOI (`chest.YYYY.MM.NNNN`, four-digit item number) and a poster code in the DOI (`nzz041.p21-009-19`). Tag `meeting_abstract:genre`.
BARE_ACRONYM_VOLUME = re.compile(r"^\s*[A-Z][A-Za-z0-9&-]{1,14}\s?['’]\s?\d{2}\s*$")
# Owner 2026-11-12: the three narrow patterns (tutorial DOI, poster-code DOI, all-caps title + dated Elsevier DOI) are ON; the broader
# supplement-style item DOI (SUPPLEMENT_ITEM_DOI) was not part of that approval and has its own switch, OFF.
ABSTRACT_FAMILY_DROPS = True
SUPPLEMENT_ITEM_DOI_DROPS = False
TUTORIAL_ABSTRACT_DOI = re.compile(r'(?i)^10\.18653/v1/\d{4}\.[a-z0-9-]+-tutorials?\.\d+$')
POSTER_CODE_DOI = re.compile(r'(?i)\.p\d{1,3}-\d{2,3}-\d{2}$')
ELSEVIER_DATED_DOI = re.compile(r'(?i)^10\.1016/j\.[a-z0-9.]+\.\d{4}\.\d{2}\.\d{3,4}$')
SUPPLEMENT_ITEM_DOI = re.compile(r'(?i)^10\.1016/j\.chest\.\d{4}\.\d{2}\.\d{4}$')
JAAD_2026_SUPPLEMENT_DOI = re.compile(r'(?i)^10\.1016/j\.jaad\.2026\.04\.\d{4}$')
JAAD_ABSTRACT_NUMBER = re.compile(r'^\s*\d{5}\s+\S')


# R-PAP-48 (2026-11-19, D-0023; Toronto gate 9 pi2): meeting-supplement abstracts keyed by DOI shape. A journal-supplement item DOI of an OUP journal
# carries the supplement's article id plus a dotted item number ('10.1093/jcag/gwaf042.015', 'ehz748.0574', 'ofx163.110'); a regular OUP article DOI has no dotted
# suffix. Neuromuscular Disorders prints the World Muscle Society congress abstracts as items numbered 100 and up ('10.1016/j.nmd.2017.06.320').
OUP_SUPPLEMENT_DOI = re.compile(r'(?i)^10\.1093/[a-z0-9]+/[a-z]{2,8}\d{2,4}[a-z]?\.\d{2,5}$')
NMD_CONGRESS_DOI = re.compile(r'(?i)^10\.1016/j\.nmd\.\d{4}\.\d{2}\.(\d{3,4})$')
# R-PAP-49: Dagstuhl/DROPS artifact-evaluation deposits (software or data artifacts of a paper, DOI series 10.4230/artifacts.N), never the paper.
DAGSTUHL_ARTIFACT_DOI = re.compile(r'(?i)^10\.4230/artifacts\.\d+')
# R-PAP-50: a workshop's own front matter or proposal titled 'ACRONYM'YY: Nth/First/Second ... Workshop on ...' (ADVM'21, MuCAI'20, Meta-HCI: First Workshop
# on Meta-Research in HCI, DRL4IR: 2nd Workshop on ...); only conference records (a 'workshop report' article is not touched).
WORKSHOP_ORDINAL_TITLE = re.compile(r'^[^:]{2,70}:\s*(?i:the\s+)?(?i:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+(?:st|nd|rd|th))\s+'
                                    r'(?:(?:(?i:international|annual|national|joint|virtual|biennial)|[A-Z][\w-]*)\s+){0,5}(?i:workshop)\b')
# R-PAP-51: a journal's own report on its state and changes (editors-in-chief, annual summary): 'Report on the state and changes of the SoSyM journal (2025 summary)'.
JOURNAL_STATE_REPORT_TITLE = re.compile(r'(?i)^\s*report on the state and changes of the\b[^:]{0,60}\bjournal\b')


# R-PAP-55 (2026-11-19, D-0023; Oxford gate 9 pi2, Worrell): a DROPS series volume record, 'LIPIcs, Volume 198, ICALP 2021, Complete Volume' (the editors are on its byline).
DROPS_COMPLETE_VOLUME_TITLE = re.compile(r'(?i)^\s*(?:LIPIcs|OASIcs),\s*Volume\s+\d+\b.*\bComplete Volume\s*$')


# R-PAP-57 (2026-11-19, D-0023; MIT gate 9 pi2, Modiano's LIDS report): an institution's annual 'Report to the President for year ended June 30, YYYY, <unit>' (DSpace@MIT).
ANNUAL_REPORT_TITLE = re.compile(r'(?i)^\s*report to the president for (?:the )?year ended\b')


# R-PAP-58 (2026-11-19, D-0026; Georgia Tech gate 9 pi2, Inan's IEEE Sensors 2016 record): IEEE demonstration abstracts titled 'Live demonstration: <system>' (ISCAS, BioCAS, Sensors
# 'Live Demonstration' sessions): a one-page description of a demo shown at the conference, not a paper.
LIVE_DEMONSTRATION_TITLE = re.compile(r'(?i)^\s*live demo(?:nstration)?s?\s*[:\-]')
# R-PAP-59: a slide deck ('(Presentation)' or '(Slides)' as the whole-title suffix; Ling Liu's TigerPrints record) and a Zenodo/Figshare/Dryad deposit typed `book` whose title
# says it is data, code, a schema or an official implementation ('Physiohub ... (Data Analysis & DB Schema)', 'Official implementation of paper ...', 'Gaps in the Record - Notebooks and Analysis Dataset').
SLIDE_DECK_TITLE = re.compile(r'(?i)\((?:presentation|slides?)\)\s*$')
REPOSITORY_BOOK_DEPOSIT_TITLE = re.compile(r'(?i)\((?:data|code|software|source code|schema)\b[^)]*\)\s*$|^\s*official implementa(?:tion|ion) of\b|\banalysis (?:code|dataset)\s*$|\bnotebooks and\b.*\b(?:dataset|data)\s*$')
# R-PAP-60: an editor-in-chief's anniversary column ('Five years as editor-in-chief of Communications', CACM 2022).
EDITOR_ANNIVERSARY_TITLE = re.compile(r'(?i)^\s*\w+ years? as (?:the )?editor[- ]in[- ]chief\b')


# R-PAP-61 (2026-11-20, D-0028; SJTU gate 9 pi2, Li Jianhua's FITEE 2018 record): the opening item of a Frontiers of Information Technology & Electronic Engineering special issue, DOI
# 10.1631/fitee.YYNNNN0 with item number 0000 ('fitee.1840000' 'Security for cyberspace: challenges and opportunities', fitee.1820000), is the guest editors' introduction.
FITEE_ISSUE_INTRO_DOI = re.compile(r'(?i)^10\.1631/fitee\.\d{2}[0-9]0000$')


def all_caps_title(t):
    letters = [c for c in t if c.isalpha()]
    return len(t.split()) >= 4 and len(letters) >= 20 and not any(c.islower() for c in letters)


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
ABSTRACT_JOURNALS = re.compile(r'(?i)^(cancer research|cardiovascular research|circulation|blood|stroke|sleep|journal of clinical oncology|the journal of the acoustical society|'
                               r'biophysical journal|the journal of immunology|neuro-oncology|clinical cancer research|cancer immunology research|'
                               r'ultrasound in obstetrics|journal of the american society of nephrology|innovation in aging|arteriosclerosis|open forum infectious|'
                               r'genetics in medicine|schizophrenia bulletin|structural dynamics|academy of management proceedings|'
                               r'regular and young investigator|the faseb journal|neurology|biological psychiatry|value in health|'
                               r'annals of the rheumatic diseases|american journal of respiratory and critical care|journal of thoracic oncology)')
# R-PAP-19 extension (2026-11-09, Claude on the owner's delegation): meeting-supplement abstracts of two congress series. Neuromodulation
# (INS congress, Elsevier DOIs 10.1016/j.neurom.YYYY.MM.NNN) abstracts are typed conference-abstract or open with a program code ('PO222 / #1008 ...',
# 'O025 ...', 'RF006 ...', 'ID: 324641 ...'); a regular Neuromodulation article is title-case with no such code and stays. ERS congress abstracts have
# DOIs 10.1183/13993003.congress-YYYY.<code> (OpenAlex also carries the typo 10.1183/1393003.congress-...); every such DOI is an abstract.
NEUROM_DOI = re.compile(r'(?i)^10\.1016/j\.neurom\.\d{4}\.\d{2}\.\d+$')
NEUROM_ABSTRACT_CODE = re.compile(r'^\s*(?:[A-Z]{1,3}\d{2,4}\b(?:\s*/\s*#\d+)?\s|ID:\s*\d+\s)')   # 'PO222 / #1008 ', 'O025 ', 'ID: 324641 '
ERS_CONGRESS_DOI = re.compile(r'(?i)^10\.1183/1\d*3003\.congress-\d{4}\.')
BCS_CONGRESS_DOI = re.compile(r'(?i)^10\.1136/heartjnl-\d{4}-bcs\.\d+$')
THESIS_REPOSITORY_DOI = re.compile(r'^10\.25740/')  # Stanford Digital Repository (purl.stanford.edu): theses, honors theses, capstones


# ---- commentaries, columns and short invited abstracts (R-PAP-27; 2026-11-02, owner: accuracy pass) --------------------
# The Michigan sample (2026-11-02) found a CACM 'Technical perspective' (one page), a CACM Viewpoint (3 pages) and a two-page
# SIGCSE keynote abstract. A title or venue catches the first; the other two need the record's page count, which OpenAlex's
# sweep works do not carry: DBLP's `<pages>` (tools/dblp_dump_pages.py -> hierarchy/dblp-dump-pages.json.gz) does.
COMMENTARY_TITLE = re.compile(r'(?i)^\s*technical perspective\b')
# R-PAP-31 (2026-11-05, owner standard: general rule from the Georgia Tech stage-9 sample): a reply to a discussion or comment is a
# commentary ('Closure to "Macroelement and Macropatch Approaches ..."', 'Discussion of "..."', "Authors' reply to the Discussion of ...",
# 'Comment on "..."' / 'Reply to "..."' with the quoted title of the work answered), and a special-issue preface ('Special Topic on ...',
# 'Special Issue on ...', 'Special Section on ...', 'Top Picks from ...') is an editorial: a guest-editor's introduction, not research.
REPLY_COMMENTARY_TITLE = re.compile(r"(?i)^\s*(?:closure to\b|discussion (?:of|on|to)\b|authors?['’] ?(?:reply|response|closure)\b|"
                                    r"(?:reply|response|comments?) (?:to|on)\s*[“‘\"'])")
SPECIAL_ISSUE_TITLE = re.compile(r'(?i)^\s*(?:special (?:issue|topic|section|collection|feature)\b|top picks from\b)')
# R-PAP-27 (2026-11-02, coordinator's note on the rule-3 hand check): a whole proceedings volume ('Proceedings of SAT Race 2019',
# 'Proceedings 8th International Workshop on ...'), and a numbered abstract of a journal supplement ('203. Decoding the Role of ...',
# '(338) Automatic detection of ...': Biological Psychiatry, Journal of Pain, Journal of Adolescent Health)
PROCEEDINGS_VOLUME = re.compile(r'(?i)^\s*proceedings\b[:\s]*(?:of\b)?.*(?:\b(?:19|20)\d\d\b|\b\d+(?:st|nd|rd|th)\b|workshop|conference|symposium|race|competition|think tank|annual)')
SUPPLEMENT_NUMBER = re.compile(r'^\s*(?:\(\d{1,4}\)|\d{1,4}\.)\s+\S')
COLUMN_VENUE = re.compile(r'(?i)^(?:communications of the acm|ieee micro|computer|ieee computer|ieee security (?:&|and) privacy|ieee software|'
                          r'ieee pervasive computing|ieee internet computing|ieee design (?:&|and) test(?: of computers)?|ieee annals of the history of computing|'
                          r'acm queue|queue|xrds|ieee intelligent systems|ieee network|ieee communications magazine|ieee spectrum|'
                          r'ieee solid-state circuits magazine|ieee potentials|ieee consumer electronics magazine|ieee cloud computing)\s*$')  # exact: 'Computer Networks' is a journal
COLUMN_MAX_PAGES = 3      # a magazine piece of this length or less is a column (Viewpoint, Inside Risks, Kode Vicious), not a paper
INVITED_MAX_PAGES = 2     # a single-author conference record of this length is a keynote or invited-talk abstract


def short_piece(r, pages, bare=False):
    """R-PAP-27 by page count: `pages` is the largest page count DBLP gives the record (None: unknown, so no signal). A magazine
    piece of 3 pages or less is a column; a single-author conference-paper record of 2 pages or less is a keynote or invited-talk
    abstract (SIGCSE 2019, 502-503). `bare`: DBLP gave a single number, no range. In a magazine that is a one-page piece only in
    CACM (ACM Queue's is an article number: 'Troubling Trends in Machine Learning Scholarship' is '80'); a conference record with
    one number is a keynote abstract in the sample (ICAART 2016 '5', IWASI 2019 '1')."""
    if not pages:
        return None
    v = str(quality_venue(r.get('venue')) or ''); ty = r.get('type') or ''
    if COLUMN_VENUE.search(v) and ty in ('article', 'other', 'editorial', 'paratext') and pages <= COLUMN_MAX_PAGES \
            and not (bare and not re.match(r'(?i)communications of the acm', v)):
        return 'column'
    if ty == 'conference-paper' and len(r.get('byline') or []) == 1 and pages <= INVITED_MAX_PAGES:
        return 'invited_abstract'
    return None


# ---- R-PAP-33 (2026-11-05, owner: round-r2 pooled failures and the abstracts decision) ----------------------------------
# Not research records the round-r2 samples found, each as a general pattern: session and special-section introductions, interviews, eBook
# editorials, SPIE '(Conference Presentation)' records, repository (Zenodo/Figshare/Dryad) and dataset records, conference highlights and
# summaries, CACM 'Research for Practice' columns, edited-volume records (a book-level DOI with no chapter suffix), and workshop or session
# descriptions ('EE2: Workshop on ...' at ISSCC, 'VDS @ KDD 2022'). The owner's decision of the same day: conference abstracts are not papers.
INTRODUCTION_TITLE = re.compile(r'(?i)^\s*(?:(?:session|special[- ]section|special[- ]issue|minitrack|track|mini[- ]symposium) introduction\b|introduction to the (?:session|minitrack|track)\b)')
INTERVIEW_TITLE = re.compile(r'(?i)^\s*(?:an )?interview\s*(?::|with\b)|[:\u2013\u2014-]\s*an interview with\s+[A-Z]')   # 2026-11-10 (HKUST): 'Connecting minds and machines: an interview with Miguel Nicolelis'
PRESENTATION_TITLE = re.compile(r'(?i)\((?:conference|invited|keynote|plenary) (?:presentation|talk)\)\s*$')
ABSTRACT_REPRINT_TITLE = re.compile(r'(?i)\(abstract reprint\)\s*$')
REPOSITORY_DOI = re.compile(r'(?i)^10\.(?:5281/zenodo|6084/m9\.figshare|5061/dryad)\b')   # not OSF (10.17605): those are preprints
DATASET_TITLE = re.compile(r'(?i)^\s*(?:processed|raw|synthetic|simulation) data\b|^\s*datasets? (?:for|of|from|used in)\b|'
                           r'\b(?:matlab|csv|json|hdf5?) (?:data )?(?:format|files?)\s*$')
# Repository-hosted named dataset deposits can be mislabeled articles with the repository as venue.
NAMED_DATASET_TITLE = re.compile(r'(?i)^\s*[^:]{1,100}\bdatasets?\s*:')
# R-PAP-33 extension (2026-11-09): project deliverables, reports and consultation responses deposited on Zenodo (Sansone's FAIRplus/BY-COVID/ELIXIR
# deliverables 'D2.5 ...', Wallom's 'Project Radar D4.5', Bueno-Orovio's 'SMASH-HCM D1.4'). Only a Zenodo/Figshare/Dryad DOI is tested.
DELIVERABLE_TITLE = re.compile(r'(?i)(?:^|[\s:(\-\u2013])D\d{1,2}\.\d{1,2}(?:\.\d{1,2})?\b|\bdeliverable\s+\d|^\s*M\d{1,2}\s*:|'
                               r'\b(?:final|interim|annual|progress|workshop|stakeholder engagement|case) reports?\b|^\s*report on\b|\bplenary\b.*\breport\b|'
                               r'\bresponse of\b.*\bto the\b|\bresponse to the\b.*\b(?:consultation|rfi|call for (?:evidence|views|input))|\bconsultation response\b|'
                               r'\bfocus group\b|^\s*preliminary release\b')
# R-PAP-43 (2026-11-09, Claude on the owner's delegation; HKUST admission review): artifact deposits, editor messages, bare front matter.
ARTIFACT_DEPOSIT_TITLE = re.compile(r'(?i)^\s*(?:[A-Z]{2,8}\s?\d{2,4}\s+)?artifacts?\s+(?:for|of)\b')
EDITOR_MESSAGE_TITLE = re.compile(r'(?i)^\s*(?:a\s+)?message\s+from\s+the\b')
BARE_FRONT_MATTER_TITLE = re.compile(r'(?i)^\s*(?:epilogue|prologue|foreword|afterword)\s*$')
REPOSITORY_VENUE = re.compile(r'(?i)^\s*(?:zenodo|figshare|dryad)(?:\s*\([^)]*\))?\s*$')
HIGHLIGHTS_SUMMARY_TITLE = re.compile(r'(?i)\bhighlights (?:from|of) the\b.*\b(?:conference|workshop|symposium|meeting|summit)\b|'
                                      r'^\s*(?:summary|report|overview) (?:of|on) the\b.*\b(?:workshop|conference|symposium|seminar|meeting|summit)\b|'
                                      r'^\s*(?:conference|workshop|symposium) (?:summary|report)\b')
EVENT_RECAP_TITLE = re.compile(r'(?i)^(?:ACM|IEEE|USENIX|AAAI|SIAM)\s+.{4,100}\b(?:conference|symposium|workshop)\s+(?:19|20)\d{2}$')
SUMMARY_SUFFIX = re.compile(r'(?i)\b(?:workshop|symposium|conference) (?:summary|report)\s*$')   # 'SECM 2017 Workshop Summary' (8 words or fewer: a long title is a paper)
CONFERENCE_VOLUME_TITLE = re.compile(r'(?i)^\s*(?:the )?(?:\d+(?:st|nd|rd|th)\s+)?(?:annual |international |joint )?(?:conference|symposium|workshop)\s+on\b[^:]{0,110}?\s*(?:\([^)]{2,25}\)\s*)?(?:19|20)\d\d\.?\s*$')   # 'Conference on Health, Inference, and Learning (CHIL) 2022': a proceedings volume
# An event's named Research Proceedings YEAR [location] is the whole abstract collection, even when a journal types
# it as an article. Require the complete event/volume title; individual abstracts and papers discussing proceedings stay.
EVENT_RESEARCH_PROCEEDINGS_TITLE = re.compile(
    r"^\s*(?:(?:[A-ZÀ-ÖØ-Þ][\w’'&-]*|of|the|for|and|in|on)\s+){0,16}"
    r'(?i:forum|conference|congress|symposium|workshop|meeting)\s+(?i:research\s+proceedings)\s+(?:19|20)\d{2}'
    r"(?:\s*[:,–-]?\s+(?:[A-ZÀ-ÖØ-Þ][\w’'&-]*[,.]?\s*){1,8})?\.?\s*$")
RESEARCH_FOR_PRACTICE = re.compile(r'(?i)^\s*research for practice\b')
BOOK_LEVEL_DOI = re.compile(r'^10\.(?:1007|1002|1016|3233|1201|1142|1017)/97[89][\d-]+$')   # an ISBN-style DOI: the book itself, no chapter suffix
SESSION_WORKSHOP_TITLE = re.compile(r'^\s*[A-Z]{1,4}\d{1,3}(?:\.\d+)?\s*:\s*(?i:workshop|tutorial|forum|panel|short course|special session|evening session)\b|'
                                    r'\s@\s*[A-Z][A-Za-z]+\s*\d{4}\s*$|'
                                    r'^\s*[A-Za-z]+[- ]?\d{4} (?i:international )?(?i:workshop|tutorial) on\b')


def non_research_record(r, pages=None):
    """R-PAP-33: why a record is no research paper (tag), or None."""
    t = str(r.get('title') or '').strip(); v = str(r.get('venue') or ''); d = ndoi(r.get('doi')); ty = r.get('type') or ''
    if INTRODUCTION_TITLE.search(t):
        return 'session_introduction'
    if INTERVIEW_TITLE.search(t):
        return 'interview'
    if ty == 'editorial' and re.match(r'(?i)acm ebooks', v.strip()):
        return 'editorial'
    if PRESENTATION_TITLE.search(t):
        return 'presentation_only'
    if REPOSITORY_DOI.match(d) and ARTIFACT_DEPOSIT_TITLE.search(t):
        return 'artifact_deposit'
    if ty == 'editorial' and EDITOR_MESSAGE_TITLE.search(t):
        return 'editor_message'
    if ty in ('book-chapter', 'editorial', 'other') and BARE_FRONT_MATTER_TITLE.search(t):
        return 'front_matter'
    if ABSTRACT_REPRINT_TITLE.search(t):
        return 'conference_abstract'
    if REPOSITORY_DOI.match(d) and not v.strip():
        return 'repository_record'
    if REPOSITORY_DOI.match(d) and (ty == 'report' or DELIVERABLE_TITLE.search(t)):
        return 'repository_deliverable'
    if REPOSITORY_DOI.match(d) and REPOSITORY_VENUE.match(v) and (DATASET_TITLE.search(t) or NAMED_DATASET_TITLE.search(t)):
        return 'dataset_record'
    if not d and not v.strip() and DATASET_TITLE.search(t):
        return 'dataset_record'
    if HIGHLIGHTS_SUMMARY_TITLE.search(t) or (SUMMARY_SUFFIX.search(t) and len(t.split()) <= 8):
        return 'highlights_column'
    if ty == 'article' and EVENT_RECAP_TITLE.fullmatch(t):
        return 'conference_report'
    if RESEARCH_FOR_PRACTICE.search(t):
        return 'column'
    if CONFERENCE_VOLUME_TITLE.search(t) or EVENT_RESEARCH_PROCEEDINGS_TITLE.fullmatch(t):
        return 'proceedings_volume'
    # an authored monograph OpenAlex types 'article' (no venue, at most three authors: Rojo and Bloch, The Principle of Least Action, Cambridge 2018) is a
    # book, which R-PAP-15 keeps; an edited volume is typed conference-paper/proceedings/editorial or lists its editors
    authored_monograph = ty == 'article' and not v.strip() and 1 <= len(r.get('byline') or []) <= 3
    if BOOK_LEVEL_DOI.match(d) and ty in ('conference-paper', 'article', 'other', 'proceedings', 'editorial') and not authored_monograph:
        return 'edited_volume'
    if SESSION_WORKSHOP_TITLE.search(t) and ty in ('conference-paper', 'conference-abstract', 'article', 'other'):
        return 'workshop_proposal'
    if ty == 'conference-abstract' and pages and pages <= INVITED_MAX_PAGES:   # a one- or two-page abstract record of any byline
        return 'conference_abstract'
    return None


def not_a_paper(r, pages=None, bare=False):
    """Why a lab-paper row is not a paper, or None (2026-10-29, owner: accuracy sample). `r` is a lab-paper row (title,
    venue, type, doi, byline, authorship.position). The tags:
      R-PAP-18 (R1) software_record, repository_supplement (incl. protocols.io), erratum, machine_translation,
               dagstuhl_report, oberwolfach_report, editorial, award_announcement, workshop_proposal, highlights_column,
               tribute
      R-PAP-19 (R2) meeting_abstract:<venue|doi|title|journal|single_author|keynote|congress>  (congress: Neuromodulation/ERS supplements, 2026-11-09)
      R-PAP-22 (R5) dissertation (the PI is the adviser, not the author).
      R-PAP-31      commentary (a closure, discussion or quoted comment/reply), editorial (a 'Special Issue/Topic/Section on ...' preface)
      R-PAP-27      proceedings_volume, supplement_abstract (a numbered abstract in a journal), commentary (a 'Technical perspective'), column (a magazine piece of 3 pages or less), invited_abstract (a
                    single-author conference record of 2 pages or less); `pages` is the DBLP page count when known (`bare`: a single number)."""
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
    if ty == 'book-review':   # R-PAP-40 (a): a review of someone else's book is paratext, whatever the journal
        return 'book_review'
    if SUPPLEMENT_TITLE.search(t) or d.startswith('10.17504/protocols.io'):
        return 'repository_supplement'
    if ERRATUM_TITLE.search(t):
        return 'erratum'
    if re.match(r'(?i)^notice of removal\s*:', t):
        return 'removal_notice'
    if '【Powered by NICT】' in t:
        return 'machine_translation'  # JST's machine-translated Japanese record of a paper (CMU, OpenPose)
    if re.search(r'(?i)dagstuhl (?:reports|manifestos)', v) or re.match(r'10\.4230/(?:dagrep|dagman)\b', d) or re.search(r'\(Dagstuhl Seminar \d+\)\s*$', t):
        return 'dagstuhl_report'
    if re.search(r'(?i)oberwolfach', v) or d.startswith('10.4171/owr'):
        return 'oberwolfach_report'
    if GUEST_EDITORIAL_ANYWHERE.search(t):
        return 'editorial'
    if EDITORIAL_TITLE.search(t) or ISSUE_EDITORIAL_TITLE.search(t) or BRACKETED_EDITORIAL_TITLE.search(t):
        return 'editorial'
    if AWARD_TITLE.search(t) or (AWARD_END.search(t) and len(t.split()) <= 8):
        return 'award_announcement'
    if WORKSHOP_TITLE.search(t) or (TUTORIAL_ON.search(t) and ty in ('conference-paper', 'conference-abstract')):
        return 'workshop_proposal'
    if ty in ('conference-paper', 'conference-abstract', 'other') and WORKSHOP_ORDINAL_TITLE.search(t):   # R-PAP-50
        return 'workshop_proposal'
    if JOURNAL_STATE_REPORT_TITLE.search(t):   # R-PAP-51
        return 'editorial'
    if ANNUAL_REPORT_TITLE.search(t):   # R-PAP-57
        return 'annual_report'
    if LIVE_DEMONSTRATION_TITLE.search(t):   # R-PAP-58
        return 'demo_abstract'
    if SLIDE_DECK_TITLE.search(t):   # R-PAP-59
        return 'presentation_only'
    if ty == 'book' and REPOSITORY_DOI.match(d) and REPOSITORY_BOOK_DEPOSIT_TITLE.search(t):   # R-PAP-59
        return 'dataset_record'
    if EDITOR_ANNIVERSARY_TITLE.search(t):   # R-PAP-60
        return 'editorial'
    if FITEE_ISSUE_INTRO_DOI.match(d):   # R-PAP-61
        return 'editorial'
    if DAGSTUHL_ARTIFACT_DOI.match(d):   # R-PAP-49
        return 'artifact_deposit'
    if ty == 'conference-paper' and (pages is None or pages <= 2) and re.match(r'(?i)^[A-Z]{2,8}(?:[- ]\d{4})?\s+workshop on\b', t):
        return 'workshop_proposal'
    if HIGHLIGHTS_TITLE.search(t):
        return 'highlights_column'
    m = LIFE_DATES.match(t)
    life = m and [w for w in re.sub(r"[‘’'][^‘’']*[‘’']", ' ', m.group(1)).split() if w]  # 'Sanjiv ‘Sam’ Gambhir (1962–2020)'
    if TRIBUTE_TITLE.search(t) or person_name_title(t) or (life and len(life) <= 4 and all(w[:1].isupper() for w in life)
                                                            and life[0].lower() in given_names()):
        return 'tribute'
    # R-PAP-27: commentaries by title, columns and short invited abstracts by page count (`pages`: the record's DBLP page count)
    if COMMENTARY_TITLE.search(t) or REPLY_COMMENTARY_TITLE.search(t):
        return 'commentary'
    if SPECIAL_ISSUE_TITLE.search(t):
        return 'editorial'
    if BARE_ACRONYM_VOLUME.search(t) and ty in ('conference-paper', 'proceedings', 'other', 'article', 'book-chapter'):
        return 'proceedings_volume'
    if REPLY_TO_LETTERS_DROP and REPLY_TO_COLON_TITLE.search(t):
        return 'commentary'
    if PROCEEDINGS_VOLUME.search(t):
        return 'proceedings_volume'
    if DROPS_COMPLETE_VOLUME_TITLE.search(t):   # R-PAP-55
        return 'proceedings_volume'
    if SUPPLEMENT_NUMBER.search(t) and ty == 'article' and v.strip():
        return 'supplement_abstract'
    # JAAD volume 95 issue 1S lists five-digit abstract IDs on AB pages. OpenAlex types
    # those one-page supplement records as articles; require both the issue DOI family
    # and the printed abstract-number prefix so ordinary JAAD articles remain eligible.
    if ty == 'article' and JAAD_2026_SUPPLEMENT_DOI.match(d) and JAAD_ABSTRACT_NUMBER.match(t):
        return 'supplement_abstract'
    sp = short_piece(r, pages, bare)
    if sp:
        return sp
    nr = non_research_record(r, pages)   # R-PAP-33 (after the meeting-abstract tags below it keeps their finer names)
    if nr and nr != 'conference_abstract':
        return nr
    if EDITORIAL_TYPE_DROPS and ty == 'editorial':   # R-PAP-40 (b), after the finer R-PAP-33 tags
        return 'editorial'
    # R2: meeting abstracts (owner: abstracts are not papers)
    if ABSTRACT_VENUE.search(v):
        return 'meeting_abstract:venue'
    if ABSTRACT_DOI.search(d) and ty in ('conference-abstract', 'article', 'other', 'paratext'):
        return 'meeting_abstract:doi'
    if ABSTRACT_TITLE.search(t):
        return 'meeting_abstract:title'
    if ERS_CONGRESS_DOI.match(d) or BCS_CONGRESS_DOI.match(d) or (NEUROM_DOI.match(d) and (ty == 'conference-abstract' or NEUROM_ABSTRACT_CODE.search(t))):
        return 'meeting_abstract:congress'
    if ABSTRACT_FAMILY_DROPS and (TUTORIAL_ABSTRACT_DOI.match(d) or POSTER_CODE_DOI.search(d)
                                  or (SUPPLEMENT_ITEM_DOI_DROPS and SUPPLEMENT_ITEM_DOI.match(d))
                                  or (all_caps_title(t) and ELSEVIER_DATED_DOI.match(d))):
        return 'meeting_abstract:genre'
    if ty == 'conference-abstract' and ABSTRACT_JOURNALS.search(v):
        return 'meeting_abstract:journal'
    if ty == 'conference-abstract' and nb == 1:
        return 'meeting_abstract:single_author'
    if ty == 'conference-abstract' and re.search(r'(?i)\bkeynote\b|\binvited talk\b', t):
        return 'meeting_abstract:keynote'
    if ty in ('article', 'conference-abstract', 'other') and (OUP_SUPPLEMENT_DOI.match(d) or (NMD_CONGRESS_DOI.match(d) and int(NMD_CONGRESS_DOI.match(d).group(1)) >= 100)):
        return 'meeting_abstract:supplement'   # R-PAP-48
    return nr   # R-PAP-33: a conference abstract not tagged above


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

COMPANY_AFFILIATION = re.compile(
    r'\b(?:google|microsoft|meta|facebook|amazon|ibm|nvidia|openai|deepmind|anthropic|uber|apple|adobe|intel|'
    r'samsung|huawei|tencent|baidu|incorporated|inc|corporation|corp|ltd|gmbh|llc)\b', re.I)


def unwrapped_affiliation(raw):
    """Join a word broken across a PDF line, e.g. 'Intel- ligence', before matching organization names."""
    return re.sub(r'(?<=[A-Za-z])-\s+(?=[a-z])', '', raw or '')


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
        if len(u.split()) >= 2 and not PLACE.match(u) and not COMPANY_AFFILIATION.search(unwrapped_affiliation(part)):
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


def page1_elsewhere(status, text, school, title=None, author_names=()):
    """R3 (R-PAP-20, 2026-10-29, owner: accuracy sample): page 1 of the paper, read by tools/pi_fulltext_affiliation.py,
    names neither the school (not even loosely: 'Berkeley', 'CMU', 'Lausanne', 'CSAIL') nor ties it to anyone, while its
    author block names another institution, company, e-mail or web domain: the paper was done elsewhere (pi-0: every
    author on page 1 is Physical Intelligence's, 'physicalintelligence.company'). A page with no affiliations at all
    says nothing and is kept. Numbered author affiliations may be extracted after the abstract: require a supplied
    byline name carrying the same marker and an institution-shaped footnote, not an institution mentioned in prose."""
    if status != 'ok_absent' or not text:
        return None
    flat = re.sub(r'\s+', ' ', text)
    if re.search(SCHOOL_LOOSE[school], flat, re.I):
        return None
    m = AFFILIATION_MARK.search(page1_head(text, title))
    if m:
        return m.group(0)
    abstract = re.search(r'\babstract\b', text[:6000], re.I)
    if not abstract:
        return None
    header = re.sub(r'\s+', ' ', text[:abstract.start()])
    markers = set()
    for name in author_names:
        words = str(name or '').split()
        if len(words) < 2:
            continue
        pattern = r'(?<!\w)' + r'\s+'.join(map(re.escape, words)) + r'\s*(\d{1,2})(?!\d)'
        markers.update(re.findall(pattern, header, re.I))
    if not markers:
        return None
    # Affiliation notes start with a proper institution name (possibly a department), followed by punctuation or
    # a line ending. This deliberately excludes numbered narrative such as "6 Results at Columbia University ...".
    word = r"(?:[A-ZÀ-ÖØ-Þ][\w’'&-]*|of|the|for|and|in)"
    institution = (r'(?:' + word + r',?[ \t]+){0,10}'
                   r'(?:University|Institute|Institution|College|Laboratory|Laboratories|Polytechnic|Academy)'
                   r'(?:[ \t]+' + word + r'){0,10}(?=[.,;\n]|$)')
    for note in re.finditer(r'(?m)^\s*(\d{1,2})[.)]?[ \t]+(' + institution + r')', text[abstract.end():]):
        if note.group(1) in markers:
            return note.group(2)
    # R-PAP-52 (2026-11-19, D-0023; Toronto gate 9 pi2, Fleet's arXiv 2302.14816): a company or industry-lab footnote ('1\nGoogle Research. Correspondence to ...';
    # the marker may stand alone on its line). Only a named company, not a bare lab word, and only the marker of a byline author.
    company = (r'(?:Google|Microsoft|Meta|Facebook|Amazon|IBM|NVIDIA|Nvidia|OpenAI|DeepMind|Apple|Adobe|Intel|Anthropic|Salesforce|Samsung|Huawei|Tencent|Baidu|Alibaba|ByteDance)'
               r'(?:[ \t]+(?:Research|AI|Brain|Labs?|DeepMind|Inc|Corp|Corporation|Team|Brain Team|Research India|Research Asia))*(?=[.,;\n]|$)')
    for note in re.finditer(r'(?m)^\s*(\d{1,2})[.)]?\s+(' + company + r')', text[abstract.end():]):
        if note.group(1) in markers:
            return note.group(2)
    return None


def page1_pi_credited_elsewhere(text, names, aff):
    """R-PAP-29 (2026-11-18, Harvard gate 9: Tambe's AAAI-23 SAHELI paper, page 1 credits him to Google Research India while a co-author is Harvard's):
    the quote when page 1 (the text before 'Abstract', or its first 2500 characters) puts the PI's own name at an institution or company that is not
    the school: the footnote line of the PI's marker, or the text within 160 characters after the name, names another institution and not the school.
    None when the PI's name is not in the author block, carries no affiliation, or is credited to the school (alone or beside another institution)."""
    flat = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text or ''))
    ab = re.search(r'\babstract\b', flat[:6000], re.I)
    head = flat[:ab.start()] if ab else flat[:2500]
    for n in names or []:
        t = name_toks(n)
        if len(t) < 2:
            continue
        rx = re.compile(r'(?<![A-Za-z])' + re.escape(t[0][0]) + (re.escape(t[0][1:]) if len(t[0]) > 1 else r'\.?') + r'[\w.\-]*(?:\s+[A-Z][\w.\-]*){0,2}\s+' + re.escape(t[-1]) + r'(?![a-z])', re.I)
        for m in rx.finditer(head):
            tail = head[m.end():]
            mk = re.match(r'\s?([0-9,\s\u2217*\u2020\u2021\u00a7\u00b6]+)', tail[:14])
            lines = []
            if mk and mk.group(1).strip(' ,'):
                for sym in [x for x in re.split(r'[,\s]+', mk.group(1)) if x]:
                    lines += [ln.group(1) for ln in re.finditer(r'(?:^|\s)' + re.escape(sym) + r'\s?([^0-9\u2217*\u2020\u2021\u00a7\u00b6]{5,160})', tail[len(mk.group(0)):])]
            else:
                lines = [re.split(r'[.;]\s', tail[:160])[0]]   # no marker: the affiliation follows the name directly, up to the end of the sentence
            for ln in lines:
                if aff.search(ln):
                    return None
                first = re.split(r'(?<![A-Za-z])[A-Z][a-z]+\s+[A-Z][a-z]+\s*[0-9\u2217*\u2020\u2021]', ln)[0]
                if AFFILIATION_MARK.search(first) and re.search(r'univ|institut|college|laborator|\blabs?\b|\binc\b|corp|\bltd\b|gmbh|\bllc\b|hospital|academy|google|microsoft|\bmeta\b|amazon|\bibm\b|nvidia|openai|deepmind|\bresearch\b', first, re.I):
                    return (flat[m.start():m.end()] + ' ' + first).strip()
    return None


OTHER_INST = re.compile(r'univ|institut|college|polytechn|[ée]cole|laborator|\blabs?\b|\binc\b|corp|\bltd\b|gmbh|\bllc\b|hospital|academy|'
                        r'cent(?:er|re)\b|google|microsoft|\bmeta\b|amazon|\bibm\b|nvidia|openai|deepmind|foundation|\bcnrs\b|\binria\b|'
                        r'\beth\b|max planck|national|company|' + COMPANY_AFFILIATION.pattern, re.I)  # an institution, not a department


def names_other_inst(z, school):
    z = unwrapped_affiliation(z)
    u = OWN_UNITS.get(school)
    return bool(OTHER_INST.search(u.sub(' ', z) if u else z))


REPRINT_YEARS = 4   # R-PAP-38: a book chapter this many years after the PI's DBLP record of the same title is a reprint of that older paper


def venue_version_date(w, venues):
    """R9 (R-PAP-26, 2026-10-29, owner: accuracy sample): (date for the appointment check, dated_by or None). A preprint or
    repository deposit (type preprint, an arXiv DOI, or a repository as the primary source) whose title is on the PI's
    DBLP person page as a venue publication (`venues`: normalized title -> (earliest venue year, DBLP key), CoRR, ECCC
    and ePrint excluded) is dated by that venue year: Engelhardt's ML4H 2023 paper had only its October 2021 arXiv
    record; Sandholm's IJCAI 2009 paper was a 2018 KiltHub deposit."""
    date = w.get('publication_date') or str(w.get('publication_year') or '')
    src = (w.get('primary_location') or {}).get('source') or {}
    # R-PAP-38 (2026-11-06, owner): a book chapter is dated like a deposit: ACM Books and other anthologies reprint older papers as chapters ('Video Textures',
    # SIGGRAPH 2000, as a 2023 ACM Books chapter), so the PI's own DBLP record of the same title gives the work's year (and takes it out of the window when older)
    deposit = w.get('type') in ('preprint', 'book-chapter') or ndoi(w.get('doi')).startswith('10.48550/') or src.get('type') == 'repository'
    vy = venues.get(norm_title(w.get('title'))) if deposit else None
    if vy and w.get('type') == 'book-chapter' and w.get('type') != 'preprint' and not (int(w.get('publication_year') or 0) - int(vy[0]) >= REPRINT_YEARS):
        vy = None   # R-PAP-38: a chapter of a proceedings-type series a year or two after its conference (Springer Tracts, LNCS) is no reprint
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
        # Repeated joint company/university affiliations cannot turn the company into a university unit.
        # Apply this even to an already learned unit, and even with a school co-author.
        if COMPANY_AFFILIATION.search(unwrapped_affiliation(z)):
            return False
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
    DUMP_PERSONS = getattr(ctx, 'dblp_persons', identity.DUMP_PERSONS)
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
    # R-PAP-27: the largest page count DBLP gives each of the PI's records, by normalized title and by DOI (the sidecar
    # hierarchy/dblp-dump-pages.json.gz; without it no page signal, only titles)
    dblp_pages = dict(title=collections.defaultdict(dict), doi=collections.defaultdict(dict))
    pg = {}
    if DUMP_PERSONS is not None:
        for pf in (P.data('dblp-dump-pages.json.gz', root=ctx.here),
                   P.data('dblp-dump-pages-school.json.gz', ctx.school, root=ctx.here)):
            if pf.exists():
                pg.update(json.loads(gzip.decompress(pf.read_bytes()))['pages'])
    if DUMP_PERSONS is not None and pg:
        for p in pis:
            for q in p['dblp']:
                for r_ in (DUMP_PERSONS['persons'].get(q) or {}).get('pubs') or []:
                    c_ = page_count(pg.get(r_.get('key')))
                    if c_ is None:
                        continue
                    b_ = not re.search(r'[-\u2013]', str(pg.get(r_.get('key'))))  # a single number, no range
                    t_ = norm_title(html.unescape(r_.get('title') or '').rstrip('.'))
                    if t_:
                        dblp_pages['title'][p['pi']][t_] = max((c_, b_), dblp_pages['title'][p['pi']].get(t_, (0, True)))
                    for d_ in r_.get('dois') or []:
                        dblp_pages['doi'][p['pi']][ndoi(d_)] = max((c_, b_), dblp_pages['doi'][p['pi']].get(ndoi(d_), (0, True)))
        ctx.n['dblp_page_counts_titles'] = sum(len(v) for v in dblp_pages['title'].values())
    ctx.dblp_pages = dblp_pages
    ctx.dblp_page_ranges = pg  # retain exact publication-key/literal evidence for recovered sources


AUTHOR_AFFILIATION_PREFIX = re.compile(r'^\s*(?:drs?|profs?|professors?)\.?\s+', re.I)
AUTHOR_AFFILIATION_TITLE = re.compile(r'\b(?:drs?|profs?|professors?)\.?\s+', re.I)


def _affiliation_author_names(authorship):
    return {tuple(toks(byline_name(name))) for name in
            (authorship.get('raw_author_name'), (authorship.get('author') or {}).get('display_name')) if name}


def _named_affiliation_owners(qualifier, authorships):
    """Indices of byline authors explicitly named by a Dr/Prof qualifier; None means unresolved."""
    if not AUTHOR_AFFILIATION_PREFIX.match(qualifier):
        return None
    owners = set()
    for part in re.split(r'\band\b|[,&/;]', AUTHOR_AFFILIATION_TITLE.sub('', qualifier), flags=re.I):
        wanted = toks(part)
        if not wanted:
            return None
        matches = set()
        for index, author in enumerate(authorships):
            for name in _affiliation_author_names(author):
                if name and wanted[-1] == name[-1] and all(
                        word in name[:-1] or (len(word) == 1 and any(n.startswith(word) for n in name[:-1]))
                        for word in wanted[:-1]):
                    matches.add(index)
        if not matches:
            return None
        owners.update(matches)
    return owners


def school_affiliation_explicitly_other_author(work, authorship, aff):
    """Every raw school clause explicitly names another byline author, never this one.

    A structured institution list can repeat a combined affiliation block. Only clear named qualifiers contradict it;
    unqualified text, unknown names and ambiguous ownership retain the existing behavior. No person identity is decided.
    """
    # Without an explicit Dr/Prof qualifier, the existing parser can only return unknown/empty assignments.
    # Avoid normalizing the entire byline in this common case, especially on large collaborations.
    if not any(aff.search(raw) and any(AUTHOR_AFFILIATION_PREFIX.match(m[1])
                                      for m in re.finditer(r'\(([^()]*)\)', raw))
               for raw in authorship.get('raw_affiliation_strings') or []):
        return False
    authors = work.get('authorships') or []
    target_names = _affiliation_author_names(authorship)
    targets = {i for i, author in enumerate(authors)
               if author is authorship or bool(_affiliation_author_names(author) & target_names)}
    if not targets:
        return False
    assignments = []
    for raw in authorship.get('raw_affiliation_strings') or []:
        if not aff.search(raw):
            continue
        # Semicolons inside a shared author qualifier belong to that qualifier.
        for clause in re.split(r';(?![^()]*\))', raw):
            start = 0
            for match in re.finditer(r'\(([^()]*)\)', clause):
                if not AUTHOR_AFFILIATION_PREFIX.match(match[1]):
                    continue   # geographical/unit parentheses are not author assignments
                if aff.search(clause[start:match.start()]):
                    owners = _named_affiliation_owners(match[1], authors)
                    assignments.append('unknown' if owners is None else 'own' if owners & targets else 'other')
                start = match.end()
            if aff.search(clause[start:]):
                assignments.append('unknown')
    return bool(assignments) and all(a == 'other' for a in assignments)


def _authorship_school_via(work, authorship, inst, aff, school=None):
    if school is not None and excluded_school_only(authorship, school):
        return []
    if school_affiliation_explicitly_other_author(work, authorship, aff):
        return []
    raw = authorship.get('raw_affiliation_strings') or []
    # A contact address may outlive an appointment. It cannot override an
    # explicitly named institution when the school occurs only in that address.
    # Keep independent institution entries and non-contact school affiliations.
    without_contacts = [re.sub(r'\b[\w.+-]+@[\w.-]+\b', ' ', value) for value in raw]
    contact_only = (not any(aff.search(value) for value in without_contacts)
                    and any(OTHER_INST.search(unwrapped_affiliation(value)) for value in without_contacts))
    return [i.get('display_name') for i in authorship.get('institutions') or []
            if inst == i.get('id') or inst in (i.get('lineage') or [])] \
        + ['text: ' + value for value in raw if not contact_only and aff.search(value)]


def reviewed_byline_school(ctx, work):
    """Complete primary author blocks affect derived flags only, after ordinary paper eligibility."""
    original = [(a.get('raw_author_name') or (a.get('author') or {}).get('display_name'))
                for a in work.get('authorships') or []
                if _authorship_school_via(work, a, ctx.inst, ctx.aff, school=ctx.school)]
    page1 = (getattr(ctx, 'tied', None) or {}).get(work['id'])
    dedicated = (getattr(ctx, 'author_review_pages', None) or {}).get(work['id'])
    if dedicated is None and (not page1 or 'author_affiliation_review' not in page1):
        return original, None
    try:
        source_key = primary_affiliations.digest(work)
    except (TypeError, ValueError):
        source_key = None
    key = (work['id'], source_key)
    if dedicated is not None:
        key += (primary_affiliations.author_review_signature(dedicated),
                'legacy_review' if page1 and 'author_affiliation_review' in page1 else 'dedicated_review')
    cache = getattr(ctx, 'primary_affiliation_reviews', None)
    if cache is None:
        ctx.primary_affiliation_reviews = cache = {}
    if key not in cache:
        if dedicated is not None:
            if page1 and 'author_affiliation_review' in page1:
                result = dict(status='held', reason='competing_author_review_channels', work=work['id'])
            else:
                result = primary_affiliations.resolve_author_review(work, ctx.school, dedicated)
        else:
            status, text, _ = (getattr(ctx, 'page_read', None) or {}).get(work['id'], (None, None, None))
            result = primary_affiliations.resolve(work, page1, text) if status == 'ok' else dict(status='held', reason='page1_not_read', work=work['id'])
        corrected = primary_affiliations.school_flags(work, result, lambda w, a: _authorship_school_via(w, a, ctx.inst, ctx.aff, school=ctx.school))
        evidence = dict(status=result['status'], **result['evidence']) if corrected is not None else dict(result)
        cache[key] = (corrected if corrected is not None else original, evidence)
        ctx.n['primary_pdf_affiliation_review_' + result['status']] += 1
    return cache[key]


STRONG_IDENTITY = ('reviewed_openalex_author_id', 'pi_orcid', 'dblp_verified_collection_work', 'dblp_person_page_doi', 'dblp_person_page_title',
                   'pi_institutional_publication_list', 'lab_publication_page')
# R-PAP-29 (2026-11-03): a cross-affiliated byline does not count when the PI's appointment at the school is not a primary one: an adjunct's,
# consultant's or leave-taker's company paper was not done at the school (fresh hand check, 3 of 20 wrong: Savarese's Salesforce paper under a
# Stanford adjunct listing, Metze's Meta paper under 'Associate Research Professor (On Leave)', Kalai's Microsoft paper under 'Adjunct Associate Professor')
NONPRIMARY = re.compile(r'\b(adjunct|on leave|consulting|visiting|courtesy|affiliate|emerit|part[- ]time)', re.I)
CROSS_KINDS = {'company', 'nonprofit', 'government', 'facility', 'other', 'archive'}  # R-PAP-29: not another university


def reviewed_cross_affiliation_holds(overrides):
    """Explicit observed-year uncertainty holds, never inferred leave intervals or negative identity verdicts."""
    from datetime import datetime
    result = collections.defaultdict(lambda: collections.defaultdict(list))
    fields = {'action', 'years', 'reason', 'evidence', 'leave_start', 'leave_end', 'departure_inferred'}
    for pi, override in overrides.items():
        if not isinstance(override, dict) or 'cross_affiliation_holds' not in override:
            continue
        reviews = override['cross_affiliation_holds']
        if not isinstance(reviews, list):
            raise ValueError('cross-affiliation holds must be a reviewed list: ' + pi)
        for review in reviews:
            if not isinstance(review, dict) or set(review) != fields or review.get('action') != 'hold_company_only_fallback' \
                    or not isinstance(review.get('reason'), str) or not review['reason'].strip() \
                    or review.get('leave_start') is not None or review.get('leave_end') is not None \
                    or review.get('departure_inferred') is not False:
                raise ValueError('invalid explicit cross-affiliation uncertainty review: ' + pi)
            years, evidence = review['years'], review['evidence']
            if not isinstance(years, list) or not years or any(type(y) is not int or not WINDOW_START <= y <= 2026 for y in years) \
                    or len(set(years)) != len(years) or not isinstance(evidence, list) or not evidence:
                raise ValueError('cross-affiliation uncertainty review needs exact years and source evidence: ' + pi)
            observed_years = set()
            for source in evidence:
                if not isinstance(source, dict) or not re.fullmatch(r'https?://[^\s]+', str(source.get('url') or '')) \
                        or not re.fullmatch(r'[0-9a-f]{64}', str(source.get('sha256') or '')) \
                        or not isinstance(source.get('quote'), str) or not NONPRIMARY.search(source['quote']) \
                        or not isinstance(source.get('observedAt'), str):
                    raise ValueError('cross-affiliation uncertainty review lacks its nonprimary source: ' + pi)
                try:
                    observed_years.add(datetime.fromisoformat(source['observedAt'].replace('Z', '+00:00')).year)
                except ValueError as error:
                    raise ValueError('cross-affiliation uncertainty review has an invalid observation date: ' + pi) from error
            if observed_years != set(years):
                raise ValueError('cross-affiliation hold years must equal the literal source observation years: ' + pi)
            for year in years:
                result[pi][year].append(review)
    return result


page1_quote_names_pi = quotes_name_pi


def school_basis(ctx, pi, w, a, ident, page1):
    """Why authorship `a` of `w` ties the PI to the school, as `via` (empty: no basis), and the page-1 tie used: the
    institution lineage or raw string; page 1 (R-PAP-10); a bare unit name (R-PAP-25); an advisee at the school on the
    byline (R-PAP-11); an advisee on an unaffiliated byline (R-PAP-12). Returns (via, page1)."""
    school, n, inst, aff, tied = ctx.school, ctx.n, ctx.inst, ctx.aff, ctx.tied
    pi_units, school_units, anchored = ctx.pi_units, ctx.school_units, ctx.anchored
    advisee_names, adv_full, from_pw = ctx.advisee_names, ctx.adv_full, ctx.from_pw
    p = ctx.pid0[pi]
    bystander = school_affiliation_explicitly_other_author(w, a, aff)
    via = _authorship_school_via(w, a, inst, aff, school=school)
    if page1 and not a.get('institutions') and not a.get('raw_affiliation_strings'):
        via = [f"page 1 ({page1['how']}): " + ' … '.join(page1['quotes'])]  # the paper's own first page ties the school to the PI
    elif not via and tie_for_pi(tied.get(w['id']), p['names']):
        # a sweep work whose OpenAlex record gives the PI no school (none, a garbled footnote string, or a co-author's
        # institution misassigned by position) while the paper's own first page, read by tools/pi_fulltext_affiliation.py,
        # ties the school to this PI by name (2026-10-29: Chi Jin, Karthik Narasimhan, Adam Perer); the primary
        # source outranks OpenAlex's derived affiliation
        page1 = tie_for_pi(tied[w['id']], p['names']); via = [f"page 1 ({page1['how']}): " + ' … '.join(page1['quotes'])]
    if not via and excluded_school_only(a, school):
        n['school_excluded_child_only'] += 1
        return [], page1
    if bystander and not via:
        n['school_affiliation_explicit_other_author'] += 1
        return [], page1   # a named bystander is not an unaffiliated PI or a silent R-PAP-11/29 recovery
    raws_ = a.get('raw_affiliation_strings') or []
    if not via and not a.get('institutions') and raws_ and all(norm_unit(z) in pi_units[pi] or norm_unit(z) in school_units for z in raws_):
        # R6: the PI's raw affiliation is only the name of one of the PI's own units at the school, and no institution
        # is named for the PI; it counts as the school when the PI's identity is anchored (not the advisee route) or
        # another author on the byline lists the school ('Department of Computer Science' alone is common to every
        # school, so the unit must be the PI's own and one of the two must hold)
        aid_ = (a.get('author') or {}).get('id')
        anchored_ok = (ident not in (None, 'advisee_coauthor', 'advisee_anchored_author_id')) or bool(aid_ and anchored[pi].get(aid_, 0) >= 1)
        school_co = any(x is not a and _authorship_school_via(w, x, inst, aff, school=school) for x in w.get('authorships') or [])
        if bare_unit_school(raws_, pi_units[pi], school_units, anchored_ok, school_co):
            via = [f'school unit on the PI authorship: {raws_[0]}']; n['school_via_bare_unit'] += 1
    if not via and not a.get('institutions') and not any(names_other_inst(z, school) for z in a.get('raw_affiliation_strings') or []):
        # the PI's authorship names no institution (none, or a department only, as recent preprints do) and a stated
        # advisee of the PI on the same byline lists the school: the paper is the lab's (identity and appointment still apply)
        co = [x.get('raw_author_name') for x in w.get('authorships') or [] if x is not a and x.get('raw_author_name')
              and _authorship_school_via(w, x, inst, aff, school=school)
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
    if not via and ident in STRONG_IDENTITY and a.get('institutions') and ctx.direct_years[pi].get(int(w.get('publication_year') or 0), 0) >= 2:
        # R-PAP-29 (2026-11-02, owner: accuracy pass; Wenisch's HPCA 2016 paper): OpenAlex credits the PI to a company or agency
        # only, while the byline also names the school (a co-author's institution, or a shifted position) and the PI's own works of
        # that year name the school at least twice. Strong identity, the appointment check below and the paper-type checks still
        # apply. Not the unaffiliated route: a byline with no institution at all (pi-0) is not touched.
        kinds_ = {i.get('type') for i in a['institutions']}
        school_co = any(x is not a and _authorship_school_via(w, x, inst, aff, school=school) for x in w.get('authorships') or [])
        if kinds_ <= CROSS_KINDS and school_co:
            # a page-1 read (arXiv v1 or the catalog's copy, pi_fulltext_affiliation.py pdf) that puts the PI's own name at another institution and not the school
            # shows the co-author's credit is the only school on the byline: not the PI's lab paper (page 1 outranks OpenAlex, as in R-PAP-10)
            st1, blob1, _u1 = (getattr(ctx, 'page_read', None) or {}).get(w['id']) or (None, None, None)
            elsewhere1 = page1_pi_credited_elsewhere(zlib.decompress(blob1).decode('utf-8', 'replace'), p['names'], ctx.aff) if blob1 and st1 in ('ok', 'ok_untied', 'ok_absent') else None
            if elsewhere1:
                n['cross_affiliation_page1_pi_elsewhere'] += 1
                return [], page1
            via = ['cross-affiliated byline: PI credited to ' + ', '.join(i.get('display_name') or '?' for i in a['institutions'][:2])
                   + '; a co-author is credited to the school']
            n['school_via_cross_affiliation'] += 1
    return via, page1


def direct_via(via):
    """The school basis is the PI's own authorship naming the school (an institution or a raw affiliation string), not an
    advisee, a unit name, a first page or a cross-affiliation."""
    return bool(via) and not via[0].startswith(('advisee', 'school unit', 'page 1', 'cross-affiliated'))


def anchored_orcid_given_name_conflict(pi_record, authorship, identity_label):
    """Hold an initial-only PI name match when the byline spells a different given name and its ORCID also disagrees.

    An anchored OpenAlex id alone cannot resolve that contradiction. Stronger per-work identities (the PI's ORCID,
    DBLP DOI/title or a reviewed publication page) are assessed by their own evidence.
    """
    if identity_label not in ('anchored_author_id', 'advisee_anchored_author_id'):
        return False
    author = authorship.get('author') or {}
    observed = {str(o).rsplit('/', 1)[-1].upper() for o in
                (author.get('observed_orcids') or []) + [author.get('orcid')] if o}
    owned = {str(o).rsplit('/', 1)[-1].upper() for o in pi_record.get('orcid') or [] if o}
    if not observed or not owned or not observed.isdisjoint(owned):
        return False
    raw = name_toks(authorship.get('raw_author_name') or author.get('display_name') or '')
    if len(raw) < 3 or len(raw[0]) != 1 or len(raw[1]) < 2:
        return False
    return not any(name_toks(n)[:2] == raw[:2] or
                   (len(name_toks(n)) >= 2 and raw[1] == name_toks(n)[0])
                   for n in pi_record.get('names') or [pi_record['pi']])


def rows_from_hits(ctx):
    """Lab-paper rows from the matched authorships: school basis, page 1 before the unaffiliated route (R-PAP-20),
    identity, venue-version dating (R-PAP-26), the appointment (R-PAP-01, R-PAP-13); a second OpenAlex record of one
    collection work becomes an edition (R-PAP-16). Returns (rows, seen keys)."""
    school, n, hits, pid0, inst, aff = ctx.school, ctx.n, ctx.hits, ctx.pid0, ctx.inst, ctx.aff
    funnel, blocked, anchored, page_read, dblp_venue = ctx.funnel, ctx.blocked, ctx.anchored, ctx.page_read, ctx.dblp_venue
    page1_samples = []
    uncertainty_holds = reviewed_cross_affiliation_holds(getattr(ctx, 'ov', {}))
    ctx.cross_affiliation_hold_review = []
    # lab papers
    rows, seen = [], set()
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
            byline_names = [name for au in w.get('authorships') or [] for name in
                            (au.get('raw_author_name'), (au.get('author') or {}).get('display_name')) if name]
            elsewhere = page1_elsewhere(st_, txt_, school, w.get('title'), byline_names)
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
        if anchored_orcid_given_name_conflict(p, a, identity):
            n['anchored_orcid_given_name_conflicts'] += 1; continue
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
        if before_window(date):   # any route: a record dated before the atlas window (a re-pulled merged id, an old PI work) is no lab paper of the window
            n['dated_before_window'] += 1; funnel[pi]['dated_before_window'] += 1; continue
        # R-PAP-37: a listing-continuity period admits only a paper whose own byline names the school
        per = next((q for q in p['periods'] if contains(q['start'], q['end'], date, q['asof'] or TODAY) == 'supported'
                    and (q.get('reviewed') != LISTING_BRIDGE or direct_via(via))), None)
        lst = None
        if per is None:
            y = same_year(date); lst = next((l for l in p['listings'] if l['year'] == y), None) if y else None
        if per is None and lst is None and direct_via(via):
            # R-PAP-28 (2026-11-02, owner: accuracy pass; Klasnja's IMWUT 2020 paper): a period whose boundary the date cannot be
            # placed against ('boundary_unresolved': a year-precision start, or a paper dated by its year only) does not turn
            # away a paper whose own authorship names the school: the affiliation is the dated statement the period lacks, as in
            # R-PAP-13's transition years. Only the PI's own affiliation counts (not an advisee, unit-name or page-1 route).
            per = next((q for q in p['periods'] if contains(q['start'], q['end'], date, q['asof'] or TODAY) == 'boundary_unresolved'), None)
            if per is not None:
                n['period_boundary_affiliated'] += 1; funnel[pi]['period_boundary_affiliated'] += 1
        if per is None and lst is None:
            n['outside_appointment'] += 1; funnel[pi]['outside_appointment_' + str(w.get('publication_year'))] += 1; continue
        if via[0].startswith('cross-affiliated') and NONPRIMARY.search(' '.join([(q_.get('quote') or '') for q_ in (per or {}).get('evidence') or []] + [(lst or {}).get('quote') or '', (lst or {}).get('kind') or ''])):
            n['cross_affiliation_nonprimary_appointment'] += 1; continue
        if via[0].startswith('cross-affiliated') and (reviews := uncertainty_holds[pi].get(same_year(date))):
            n['cross_affiliation_review_hold'] += 1; funnel[pi]['cross_affiliation_review_hold'] += 1
            ctx.cross_affiliation_hold_review.append(dict(pi=pi, oa=w['id'], title=w.get('title'), date=date,
                status='held_source_uncertainty', school_via=via,
                admitting_appointment=dict(periodId=per['id']) if per else dict(listing=lst), reviews=reviews))
            continue
        if via[0].startswith('cross-affiliated') and per is None and len({l_['year'] for l_ in p['listings']}) >= 2 \
                and lst['year'] <= int(TODAY[:4]) - 3 and transition_side(p, lst, date) == 'outside' \
                and ctx.other_years[pi][int(w.get('publication_year') or 0)] > ctx.direct_years[pi][int(w.get('publication_year') or 0)]:
            # R-PAP-29 guard (2026-11-03; Smola's 2017 Amazon papers under his last CMU listing, April 2017): a byline crediting the PI to a
            # company says nothing about where the work was done, so in the PI's arrival or departure year the listing proves only its own
            # side of the capture date, as for an unaffiliated byline (R-PAP-13). A count of the PI's works by institution does not
            # separate the cases: dual-role faculty (Freeman, Yang, Xiong) have more company-credited works than school-credited ones. Only with 2+
            # listing years and a listing at least 3 years old: a PI with one captured listing (Turitsyn) or whose last capture is recent
            # (Rosenholtz, 2024) has no observed arrival or departure, only thin captures. And only when the PI's identified works of the
            # year credit other institutions more often than the school (Smola 2017: Amazon 7, CMU 1; Turitsyn 2019, MIT 11 vs D. E. Shaw 2, stays).
            n['cross_affiliation_transition_outside'] += 1; funnel[pi]['cross_affiliation_transition_outside'] += 1; continue
        weak = unaffiliated or via[0].startswith('advisee at the school')
        if weak and per is None and lst is not None and lst['year'] in ctx.stale_years[pi]:
            # R-PAP-30: the listing of a year in which OpenAlex puts the PI's works at another institution and none at the school
            # proves nothing by itself: a paper that only an advisee or an unaffiliated byline ties to the school goes to the review
            # list instead of the lab (a paper naming the school itself, or tied by its first page, is never withheld)
            ctx.stale_years[pi][lst['year']]['withheld'].append(dict(oa=w['id'], title=w.get('title'), date=date))
            n['stale_listing_withheld'] += 1; funnel[pi]['stale_listing_withheld'] += 1; continue
        if weak:
            tw_ = [t_ for t_ in ctx.twin_records.get((pi, norm_title(w.get('title'))), []) if t_[0] != w['id'] and not t_[1] and t_[2]]
            if tw_:
                # the same paper's other record credits the PI to another institution only: always a review item; the paper is
                # withheld when that record is dated earlier, in a listing year the PI's works contradict (Song's SSRN preprint
                # dated 2025-01-01, its National University of Singapore record 2024-12, his 2024 listing a visiting page)
                early = [t_ for t_ in tw_ if t_[3] and str(t_[3]) < str(date) and _year(t_[3]) in ctx.stale_years[pi]]
                ctx.listing_review.append(dict(pi=pi, kind='twin_record', year=w.get('publication_year'), oa=w['id'], title=w.get('title'),
                                               twin=[dict(oa=t_[0], institutions=t_[2][:2], date=t_[3]) for t_ in tw_[:2]], withheld=bool(early)))
                n['twin_record_credits_elsewhere'] += 1
                if early:
                    n['twin_record_withheld'] += 1; funnel[pi]['twin_record_elsewhere'] += 1; continue
        if unaffiliated and per is None and transition_side(p, lst, date) == 'outside':
            # (2026-10-29, owner: best judgement) a byline with no affiliations says nothing about where the work was done,
            # so in a PI's arrival or departure year a listing proves only its own side of the capture date: Thomas
            # Griffiths's last Berkeley listing is April 2018 and he moved to Princeton that July, so an unaffiliated
            # September 2018 preprint is not a Berkeley lab paper (an affiliated one still is)
            n['unaffiliated_transition_year_outside'] += 1; funnel[pi]['transition_year_outside'] += 1; continue
        if per is None and lst is not None:
            # ROADMAP #29: every paper admitted by a transition-year listing is counted by its side of the dated capture (reported, not decided
            # here for affiliated papers: R-PAP-13 keeps them); 'undecided' is a date range that straddles the capture
            ts = transition_status(p, lst, date)
            if ts:
                n[f"transition_year_{'unaffiliated' if unaffiliated else 'affiliated'}_{ts}"] += 1
        funnel[pi]['in_appointment'] += 1
        k = (pi, cw or w['id'])
        # Keep each complete admitted source through namesake/type checks and lead selection. Compacting a later
        # same-collection record here loses its appointment/authorship and can hide its better published metadata.
        seen.add(k)
        byline_school, affiliation_review = reviewed_byline_school(ctx, w)
        rows.append(dict(pi=pi, work=cw, oa=w['id'], doi=ndoi(w.get('doi')), title=w.get('title'), year=dated_by['venue_year'] if dated_by else w.get('publication_year'), date=date, type=w.get('type'),
                         venue=((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
                         landing=(w.get('primary_location') or {}).get('landing_page_url'),
                         _edition_source=edition_source(w),
                         byline=[(x.get('raw_author_name') or (x.get('author') or {}).get('display_name')) for x in w.get('authorships') or []],
                         byline_school=byline_school,
                         authorship=dict(position=a.get('author_position'), raw_name=a.get('raw_author_name'), author_id=aid,
                                         institutions=[i.get('display_name') for i in a.get('institutions') or []], raw_affiliations=a.get('raw_affiliation_strings') or [],
                                         school_via=via[:3], page1=dict(url=page1['url'], pdf_sha256=page1['pdf_sha256'], how=page1['how'], quotes=page1['quotes']) if page1 and via[0].startswith('page 1') else None),
                         identity=identity, appointment=dict(periodId=per['id']) if per else dict(listing=lst),
                         **({'byline_affiliation_review': affiliation_review} if affiliation_review else {}),
                         **({'dated_by': dated_by} if dated_by else {}),
                         **({'page1_check': page1_check} if page1_check else {}),
                         **({'flags': ['page1_unchecked']} if page1_check and page1_check['status'] == 'page1_unchecked' else {})))
    title_sources = {}
    for pi, w, *_ in ctx.hits:
        if title_enrichment.missing(w.get('title')):
            title_sources.setdefault((pi, w['id']), w)
    for row in rows:
        # Retain source references only for missing-title eligible rows; raw work objects are never changed.
        source = title_sources.get((row['pi'], row['oa']))
        if source is not None:
            title_enrichment.remember(ctx, row, source)
    ctx.page1_samples = page1_samples
    ctx.listing_review += [dict(v, withheld_n=len(v['withheld'])) for per_ in ctx.stale_years.values() for v in per_.values()]  # R-PAP-30
    return rows, seen


ARXIV_PRE_YEARS = 4   # a DBLP record this many years after its arXiv v1: the v1's affiliation is not where the published version was done (Mossel 2016, v1 2012)


def arxiv_predates_record(ev, year):
    """R-PAP-36: the arXiv v1 an accepted page-1 read came from (id YYMM.NNNNN) was posted ARXIV_PRE_YEARS or more years before the DBLP record's year."""
    m = re.search(r'/pdf/(\d{2})\d{2}/', ev.get('url') or '') if ev.get('basis') == 'page1_arxiv' else None
    return bool(m and year and int(year) - (2000 + int(m.group(1))) >= ARXIV_PRE_YEARS)


# Citation abbreviations and DBLP journal streams identify the same venues already covered by R-PAP-27.
# These are quality views only: retain original source spellings in the paper and reviewed inputs.
QUALITY_VENUE_ALIASES = {'commun acm': 'Communications of the ACM', 'ieee softw': 'IEEE Software',
                         'ieee pervasive comput': 'IEEE Pervasive Computing'}
QUALITY_DBLP_STREAMS = {'journals/cacm/': 'Communications of the ACM', 'journals/software/': 'IEEE Software',
                        'journals/pervasive/': 'IEEE Pervasive Computing'}
RECOVERED_PUB_TYPES = {'inproceedings': 'conference-paper', 'article': 'article', 'incollection': 'book-chapter',
                       'book': 'book', 'phdthesis': 'dissertation', 'mastersthesis': 'dissertation'}


def quality_venue(venue):
    key = re.sub(r'[^a-z0-9]+', ' ', str(venue or '').lower()).strip()
    return QUALITY_VENUE_ALIASES.get(key, venue)


def recovered_publication_binding(ctx, p, x, ev, kind):
    """Resolve format/role evidence on this exact owned publication, without adding any PI/global aliases.

    An owned PID's attested selfnames apply only to its own matching publication. Publication year is separate
    evidence: proceedings/event and publisher years may differ, and this resolver never changes either date.
    """
    key = re.sub(r'^https?://dblp[.]org/rec/', '', str(x.get('dblp_key') or ev.get('dblp_key') or ''))
    base_names = p.get('names') or [p['pi']]
    pubs, compatible = [], []
    if kind == 'dblp' and key:
        persons = (getattr(ctx, 'dblp_persons', None) or {}).get('persons') or {}
        for pid in p.get('dblp') or []:
            person = persons.get(pid) or {}
            self_names = [re.sub(r'\s+\d{4}$', '', str(name)) for name in person.get('names') or []]
            names = list(dict.fromkeys([*base_names, *self_names]))
            for record in person.get('pubs') or []:
                if record.get('key') != key:
                    continue
                entry = dict(pid=pid, record=record, self_names=self_names)
                pubs.append(entry)
                title = norm_title(html.unescape(str(x.get('title') or '')))
                if not title or norm_title(html.unescape(str(record.get('title') or ''))) != title \
                        or (record.get('dois') and ndoi(x.get('doi')) not in {ndoi(d) for d in record['dois']}):
                    continue
                if any(Name(names).match(byline_name(re.sub(r'\s+\d{4}$', '', a[0]))) for a in record.get('authors') or []):
                    compatible.append(entry)
    # No aliases from a wrong key/title/DOI, another PID, or a publication lacking its owner's byline.
    names = list(base_names)
    if compatible and len(compatible) == len(pubs):
        names = list(dict.fromkeys([*names, *(name for entry in compatible for name in entry['self_names'])]))
    return dict(key=key, publications=pubs, compatible=compatible, names=names)


def recovered_source_metadata(ctx, p, x, ev, kind, strict=False, binding=None):
    """Type/quality evidence for an independently retained source, never an authorship or school admission waiver.

    A missing historical `article` fallback has no authority for a newly retained alternate. Owned publication kinds
    bind exact key/title/DOI and the owned author's literal selfnames; a differing source year is recorded separately
    and cannot rewrite recovery dates or waive ordinary appointment/window gates. Exact same-edition raw metadata
    retains a more specific nonpaper genre. Quality-only canonical venues never reconstruct a publisher record.
    """
    key = re.sub(r'^https?://dblp[.]org/rec/', '', str(x.get('dblp_key') or ev.get('dblp_key') or ''))
    proof = dict(pi=p['pi'], kind=kind, key=key, doi=x.get('doi'), title=x.get('title'), year=x.get('year'),
                 strict_new_alternate=strict, original_type=x.get('type'), original_venue=x.get('venue'),
                 pages_literal=(getattr(ctx, 'dblp_page_ranges', None) or {}).get(key))
    if not hasattr(ctx, 'recovered_source_quality'):
        ctx.recovered_source_quality = []
    evidence = []
    binding = binding if binding is not None else recovered_publication_binding(ctx, p, x, ev, kind)
    pubs = [(entry['pid'], entry['record']) for entry in binding['publications']]
    compatible = [(entry['pid'], entry['record']) for entry in binding['compatible']]
    if kind == 'dblp':
        kinds = {r.get('type') for _, r in compatible}
        typ = RECOVERED_PUB_TYPES.get(next(iter(kinds))) if len(kinds) == 1 else None
        proof['owned_publications'] = [dict(pid=pid, record=r) for pid, r in pubs]
        proof['owned_publication_selfnames'] = [dict(pid=entry['pid'], names=entry['self_names']) for entry in binding['compatible']]
        proof['year_disagreements'] = [dict(pid=pid, key=key, publication_year=r.get('year'), recovery_year=x.get('year'))
                                       for pid, r in compatible if str(r.get('year')) != str(x.get('year'))]
        review = (['publication_year_disagreement'] if proof['year_disagreements'] else [])
        if re.search(r'(?i)\bpanel report\s*[.]?$', str(x.get('title') or '')):
            review.append('panel_report_genre_review')
        if re.search(r'(?i)\bwork[- ]in[- ]progress\b', str(x.get('title') or '')):
            review.append('work_in_progress_genre_review')
        proof['review_reasons'] = review
        for reason in review:
            ctx.n['recovered_source_review:' + reason] += 1
        if typ and len(compatible) == len(pubs):
            # DBLP serializes CoRR records as <article>; CoRR is an e-print
            # repository, so that XML element does not establish journal publication.
            if typ == 'article' and key.startswith('journals/corr/'):
                typ = 'preprint'
            canonical = next((v for prefix, v in QUALITY_DBLP_STREAMS.items() if key.startswith(prefix)), None)
            evidence.append(dict(type=typ, venue=canonical or quality_venue(x.get('venue'))))
        else:
            typ = None
    else:
        typ = None
    raw = ev.get('openalex_work')
    oid = ev.get('oa')
    if not isinstance(raw, dict) or raw.get('id') != oid:
        if not hasattr(ctx, '_recovery_source_work_index'):
            ctx._recovery_source_work_index = {(pi, w['id']): w for pi, w, *_ in getattr(ctx, 'hits', [])}
        raw = ctx._recovery_source_work_index.get((p['pi'], oid))
    raw_bound = bool(raw and raw.get('id') == oid and norm_title(raw.get('title')) == norm_title(x.get('title'))
                     and (not raw.get('doi') or not x.get('doi') or ndoi(raw.get('doi')) == ndoi(x.get('doi'))))
    proof['raw_same_edition_bound'] = raw_bound
    if raw_bound:
        source = ((raw.get('primary_location') or {}).get('source') or {})
        proof['raw_metadata'] = dict(id=raw.get('id'), doi=raw.get('doi'), title=raw.get('title'),
                                     type=raw.get('type'), venue=source.get('display_name'))
        if raw.get('type'):
            evidence.append(dict(type=raw['type'], venue=quality_venue(source.get('display_name') or x.get('venue'))))
            if kind != 'dblp':
                typ = raw['type']
    if x.get('type'):
        evidence.append(dict(type=x['type'], venue=quality_venue(x.get('venue'))))
        if kind != 'dblp' and not typ:
            typ = x['type']
    # A known source contradiction cannot be paper-positive merely through an explicit generic `article` label.
    if pubs and (len(compatible) != len(pubs) or not typ):
        reason = 'owned_publication_metadata_conflict'
    elif strict and not typ:
        reason = 'new_alternate_type_unproven'
    elif strict and kind == 'dblp' and x.get('doi') \
            and not (raw_bound and ndoi(raw.get('doi')) == ndoi(x['doi'])) \
            and not any(ndoi(x['doi']) in {ndoi(d) for d in r.get('dois') or []} for _, r in pubs):
        reason = 'new_alternate_doi_unproven'
    else:
        reason = None
    proof.update(classified_type=typ, quality_views=evidence, hold_reason=reason)
    ctx.recovered_source_quality.append(proof)
    if reason:
        ctx.n['recovered_source_quality:' + reason] += 1
        return None
    if not typ:
        # Preserve the pre-existing route's output contract; it does not make the fallback new source evidence.
        typ = x.get('type') or 'article'
        ctx.n['recovered_source_quality:legacy_type_unproven'] += 1
    else:
        ctx.n['recovered_source_quality:classified'] += 1
    return dict(type=typ, quality_views=evidence,
                author_count=max((len(r.get('authors') or []) for _, r in compatible), default=None) if kind == 'dblp' else None,
                page_evidence=dict(key=key, literal=proof['pages_literal']) if kind == 'dblp' and compatible else None)


def recovered_scope_via(ctx, p, ev, require_replay=False, names=None, publication=None):
    """Replay an OpenAlex recovery against the current charter; display names alone cannot prove scope.
    Page-1 evidence is independent. Legacy rows may reuse the original work already read by the native hits stage."""
    if ev.get('basis') != 'openalex_authorship' or (not require_replay and not related_gate(ctx.school)):
        return ev.get('school_via')
    w = ev.get('openalex_work')
    if not isinstance(w, dict) or w.get('id') != ev.get('oa'):
        w = next((h[1] for h in getattr(ctx, 'hits', []) if h[1]['id'] == ev.get('oa')), None)
    if w is None:
        ctx.n['recovered_school_scope_unreplayable'] += 1
        return []
    nm = Name(names if names is not None else p.get('names') or [p['pi']])
    base = Name(p.get('names') or [p['pi']])
    alias_used = any(nm.match(a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or '')
                     and not base.match(a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or '')
                     for a in w.get('authorships') or [])
    if alias_used and publication is not None:
        title = norm_title(publication.get('title'))
        if not title or norm_title(w.get('title')) != title \
                or (w.get('doi') and publication.get('doi') and ndoi(w['doi']) != ndoi(publication['doi'])):
            ctx.n['recovered_school_scope_alias_source_conflict'] += 1
            return []   # a new local alias cannot borrow this other work's school
    w = school_scope_work(w, ctx.school)
    via = [v for a in w.get('authorships') or []
           if nm.match(a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or '')
           for v in _authorship_school_via(w, a, ctx.inst, ctx.aff, school=ctx.school)]
    if not via:
        ctx.n['recovered_school_scope_not_supported'] += 1
    return via


def recovered_rows(ctx, rows, seen):
    """Rows from RECOVERED_KINDS: inside the appointment, one per (PI, work); appended to `rows`."""
    HERE, school, n, pid0, cwork = ctx.here, ctx.school, ctx.n, ctx.pid0, ctx.cwork
    present_sources = {(r['pi'], r['oa']) for r in rows}
    from .students import merged_alias_spellings
    merged_alias = merged_alias_spellings(school, list(pid0.values()), HERE)   # a merged census alias spelling keys recovered rows too
    # papers on the PI's own DBLP page that only DOI-resolved OpenAlex records or the paper's first page tie to the school
    # (tools/dblp_recover.py -> hierarchy/<school>/dblp-recovered.jsonl.gz), and likewise papers the PI's own lab
    # publications page lists (tools/labpage_recover.py -> hierarchy/<school>/labpage-recovered.jsonl.gz, key 'labpage:<sha1>')
    for kind, label in RECOVERED_KINDS:
        for x in recovered_source(ctx, kind):
            p = pid0.get(x['pi']) or next((q for q in pid0.values() if q.get('censusName') == x['pi']), None) or pid0.get(merged_alias.get(x['pi']))   # R-PAP-34: rows made under a census placeholder name; a merged-away spelling
            if not p:
                continue
            x = recovery_reviews.project(ctx, p, dict(x, pi=p['pi']), kind)
            if x is None:
                continue
            ev = x['evidence']
            if kind == 'dblp' and in_blocked_cluster(p, dict(authorships=[dict(raw_author_name=b_) for b_ in x.get('byline') or []])):
                n['dblp_recovered_blocked_cluster'] += 1; continue   # R-PAP-32: a reviewed namesake cluster is never the PI's, whatever the DBLP page says

            def aside(why, x=x):  # an accepted lab-page paper the build does not keep: named in report.json
                if kind == 'labpage_addition':
                    ctx.labpage_set_aside.append(dict(pi=x['pi'], year=int(x['year']), title=x.get('title'), key=x.get('key'), reason=why))
            try:
                date = recovered_dates.publication_date(ctx, x, kind)
            except (KeyError, TypeError, ValueError, OSError, IndexError):
                n[f'{kind}_recovered_invalid_publication_date_proof'] += 1
                aside('invalid_publication_date_proof'); continue
            if not WINDOW_START <= int(x['year']) <= int(TODAY[:4]):  # the atlas window, as the sweep's (2026-10-31: EPFL 2015 row)
                n[f'{kind}_recovered_outside_window'] += 1; aside('outside_window'); continue
            if kind == 'dblp' and arxiv_predates_record(ev, x.get('year')):   # R-PAP-36: page 1 of a v1 posted 4+ years before the record says where it was done then
                n['dblp_recovered_arxiv_v1_predates_record'] += 1; continue
            cw = cwork(dict(doi=x.get('doi'), title=(x.get('title') or '').rstrip('.'), publication_year=x['year'])) or None
            oa_id = ev.get('oa') or (f"https://dblp.org/rec/{re.sub('^https?://dblp[.]org/rec/', '', str(x['dblp_key']))}" if kind == 'dblp' else x['key'])
            if reviewed_claims.excluded(ctx, x['pi'], dict(oa=oa_id, doi=x.get('doi'), work=cw)):
                aside('reviewed_source_held'); continue
            existing = (x['pi'], cw or oa_id) in seen or (x['pi'], oa_id) in present_sources
            binding = recovered_publication_binding(ctx, p, x, ev, kind)
            own_byline = any(Name(binding['names']).match(byline_name(b)) for b in x.get('byline') or [])
            base_byline = any(Name(p.get('names') or [p['pi']]).match(byline_name(b)) for b in x.get('byline') or [])
            if (existing or kind == 'publisher') and not own_byline:
                n[f'{kind}_recovered_existing_pi_byline_unproven'] += 1; aside('existing_work_pi_byline_unproven'); continue
            alias_replay = kind == 'dblp' and bool(p.get('dblp')) and bool(x.get('byline')) and not base_byline
            scope_via = recovered_scope_via(ctx, p, ev, require_replay=existing or alias_replay,
                                            names=binding['names'], publication=x)
            if ev.get('basis') == 'openalex_authorship' and scope_via == []:
                aside('school_scope_not_supported'); continue
            via = scope_via or [f"page 1 ({ev.get('how')}): " + ' … '.join(ev.get('quotes') or [])]
            if kind == 'dblp' and ev.get('how'):  # R-PAP-36: the DBLP-listed work confirmed by its own first page
                via = ['page1_dblp: ' + str(x.get('dblp_key') or '')] + via
            per = next((q for q in p['periods'] if contains(q['start'], q['end'], date, q['asof'] or TODAY) == 'supported'), None)
            lst = None if per else next((l for l in p['listings'] if l['year'] == int(x['year'])), None)
            if per is None and lst is None:
                n[f'{kind}_recovered_outside_appointment'] += 1; aside('outside_appointment'); continue
            classified = recovered_source_metadata(ctx, p, x, ev, kind, strict=existing, binding=binding)
            if classified is None:
                aside('source_type_unproven_or_conflicting'); continue
            # A complete independently eligible recovery can be the publisher edition of an existing collection
            # work. It must reach the ordinary quality checks and edition selector instead of being discarded here.
            seen.add((x['pi'], cw or oa_id))
            present_sources.add((x['pi'], oa_id))
            rows.append(dict(pi=x['pi'], work=cw, oa=oa_id, doi=x.get('doi'), title=(x.get('title') or '').rstrip('.'), year=x['year'], date=date, type=classified['type'], _source_quality_views=classified['quality_views'], _source_author_count=classified['author_count'], _source_page_evidence=classified['page_evidence'],
                             venue=x.get('venue'), landing=ev.get('url'), byline=list(dict.fromkeys(x.get('byline') or [])), byline_school=[],
                             authorship=dict(position=None, raw_name=None, author_id=None, institutions=[], raw_affiliations=[], school_via=via[:3],
                                             page1=dict(url=ev.get('url'), pdf_sha256=ev.get('pdf_sha256'), how=ev.get('how'), quotes=ev.get('quotes'),
                                                       **({'dblp_key': ev['dblp_key'], 'fetched_at': ev['fetched_at']} if ev.get('dblp_key') and ev.get('fetched_at') else {})) if ev.get('how') else None),
                             identity=label, appointment=dict(periodId=per['id']) if per else dict(listing=lst),
                             source=(f'{kind}_recover:' if kind != 'labpage_addition' else f"labpage_addition:{x.get('rule')}:") + ev['basis']))
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


def reviewed_not_paper(p, r):
    """R-PAP-39: a reviewed `not_papers` entry of the PI (census overrides: doi or OpenAlex id, why, evidence) names this row."""
    for e in (p or {}).get('notPapers') or []:
        if (e.get('doi') and ndoi(e['doi']) == ndoi(r.get('doi'))) or (e.get('oa') and e['oa'] == r.get('oa')):
            return e
    return None


def drop_not_papers(rows, dblp_nauth, n, dblp_pages=None, pid0=None):
    """R-PAP-17 .. R-PAP-19, R-PAP-22, R-PAP-23: rows that are not papers leave the lab, counted per tag with samples.
    Returns (rows kept, samples)."""
    # not papers (R-PAP-18/19/22, 2026-10-29, owner: accuracy sample): repository records, paratext, seminar and workshop
    # reports, award announcements, tributes, meeting abstracts and dissertations leave the lab (not_a_paper); and a
    # record whose DOI belongs to another work (R-PAP-23, doi_year_conflict). Counted per tag, with samples, in the report.
    kept_, not_paper_samples = [], collections.defaultdict(list)
    for r in rows:
        pg_, bare_ = None, False
        exact_pages = r.get('_source_page_evidence')
        if exact_pages is not None:
            literal = exact_pages['literal']
            pg_, bare_ = page_count(literal), bool(literal and not re.search(r'[-\u2013]', str(literal)))
        elif dblp_pages:  # R-PAP-27: the raw record's page count by DOI, else title
            pg_, bare_ = dblp_pages['doi'][r['pi']].get(ndoi(r.get('doi'))) or dblp_pages['title'][r['pi']].get(norm_title(r.get('title'))) or (None, False)
        why = None; corrected_authors = False
        for view in [r] + [dict(r, **fields) for fields in r.get('_source_quality_views') or []]:
            why = ('source_type:' + view['type'] if view.get('type') in NOT_PAPERS else None) \
                or not_a_paper(view, pg_, bare_) or ('doi_year_conflict' if doi_year_conflict(view) else None)
            if why in ('meeting_abstract:single_author', 'invited_abstract') and (r.get('_source_author_count') if r.get('_source_author_count') is not None
                    else dblp_nauth[r['pi']].get(norm_title(r.get('title')), 0)) >= 2:
                why = None; corrected_authors = True  # same existing full-DBLP-author correction for every source quality view
            if why:
                break
        if not why and reviewed_not_paper((pid0 or {}).get(r['pi']), r):
            why = 'reviewed_not_paper'
        if not why and corrected_authors:
            n['single_author_abstract_kept_dblp_coauthors'] += 1
        if why:
            n['not_paper:' + why] += 1
            if len(not_paper_samples[why]) < 10:
                not_paper_samples[why].append(dict(pi=r['pi'], oa=r['oa'], title=r.get('title'), venue=r.get('venue'), type=r.get('type'), doi=r.get('doi')))
        else:
            # Title-enrichment review tracks this native row by object identity. Remove only internal quality fields;
            # raw work/recovery source objects are separate and stay unchanged.
            r.pop('_source_quality_views', None); r.pop('_source_author_count', None); r.pop('_source_page_evidence', None)
            kept_.append(r)
    n['not_paper_dropped'] = len(rows) - len(kept_); rows = kept_
    return rows, not_paper_samples


def edition_source(work):
    """Compact source evidence used while selecting a lead, removed before package serialization."""
    location = work.get('primary_location') or {}
    return dict(version=location.get('version'), is_published=location.get('is_published'),
                source_type=(location.get('source') or {}).get('type'))


def edition_rank(r):
    """Existing source/DOI/collection/year preference, applied only to complete eligible records."""
    d = ndoi(r.get('doi'))
    source = r.get('_edition_source') or {}
    published = source.get('is_published') is True or source.get('version') == 'publishedVersion'
    repository = source.get('source_type') == 'repository' or (r.get('type') == 'preprint' and not published) \
        or d.startswith('10.48550') or REPOSITORY_DOI.match(d) or REPOSITORY_VENUE.search(str(r.get('venue') or ''))
    manuscript = source.get('version') in ('submittedVersion', 'acceptedVersion') and source.get('is_published') is not True
    publication = 2 if repository or manuscript else (0 if published else 1)
    return (publication, 0 if d and not d.startswith('10.48550') else 1,
            bool(d.startswith('10.5555/')), 0 if r['work'] else 1, -(int(r['year'] or 0)))


class EditionIdentityConflict(ValueError):
    """Complete source records disagree; retain the inputs and hold before package serialization."""

    def __init__(self, conflicts):
        self.conflicts = conflicts
        super().__init__('Eligible edition identity requires source review: ' + json.dumps(conflicts, ensure_ascii=False))


def compatible_bylines(a, b):
    """A source may omit authors, but must not replace/reorder the authors it supplies for the same identifier."""
    def subsequence(short, long):
        j = 0
        for name in long:
            if j < len(short) and Name([short[j]]).match(byline_name(name)):
                j += 1
        return j == len(short)
    return subsequence(a, b) or subsequence(b, a)


def legacy_edition_key(r):
    """The ordinary R16 identity key, evaluated before choosing a different metadata source."""
    title = str(r.get('title') or '')
    wip = re.sub(r'^\s*work[- ]in[- ]progress\s*:\s*|\s*:\s*work[- ]in[- ]progress\s*$', '', title, flags=re.I)
    if wip != title and r.get('year') and r.get('byline'):
        return ('wip', r['pi'], norm_title(wip), r['year'], tuple(norm_title(a) for a in r['byline']))
    return (r['pi'], norm_title(title)[:150] or r['oa'])


def eligible_untranslated_sources(rows, school):
    """R-PAP-15 is per source: a translated alternate cannot lead or lend a byline after CW collapse."""
    if _S.field(_S.get(school), 'rules.foreign_title_exception'):
        return rows, None
    kept = [r for r in rows if not (r.get('type') in ('book', 'book-chapter') and foreign_title(r.get('title')))]
    return kept, len(rows) - len(kept)


def collapse_eligible_sources(rows, n, diagnostics=None):
    """Retain legacy first-eligible representatives for identity/book counting, not metadata preference.

    All complete normally eligible alternatives survive internally. Inherited collection/source grouping is not a
    new OA identity assertion or an assertion that discrepant author orders/DOIs have been independently verified.
    """
    diagnostics = diagnostics if diagnostics is not None else []
    grouped = collections.defaultdict(list)
    for i, r in enumerate(rows):
        key = (r['pi'], 'collection', r['work']) if r.get('work') else (r['pi'], 'source', r.get('oa') or i)
        grouped[key].append(r)
    out = []
    for key, g in grouped.items():
        representative = dict(g[0])
        representative['_eligible_editions'] = g[1:]
        # Book folding runs on this eligible legacy representative. A later publisher's title cannot redefine R16.
        representative['_legacy_identity_key'] = legacy_edition_key(g[0])
        out.append(representative)
        signatures = {(ndoi(r.get('doi')), r.get('year'), r.get('type'), tuple(r.get('byline') or [])) for r in g}
        if len(signatures) > 1:
            diagnostics.append(dict(kind='established_source_metadata_disagreement', base=list(key), records=g))
    n['established_source_metadata_disagreements'] = sum(d['kind'] == 'established_source_metadata_disagreement' for d in diagnostics)
    return out


def merge_editions(rows, n, preferred=None, diagnostics=None):
    """Fix legacy CW/R16 components before metadata selection; guard only genuinely new exact-OA bridges."""
    diagnostics = diagnostics if diagnostics is not None else []
    grouped = collections.defaultdict(list)
    chapter_counts = collections.Counter()
    for r in rows:
        key = r.get('_legacy_identity_key') or legacy_edition_key(r)
        complete = dict(r)
        variants = complete.pop('_eligible_editions', [])
        complete.pop('_legacy_identity_key', None)
        complete.pop('_source_partition', None)
        chapter_counts[key] += r.get('chapters_folded', 0)
        grouped[key].extend([complete] + variants)
    keys = list(grouped)
    groups = [grouped[k] for k in keys]
    parent = list(range(len(groups)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    doi_sets = [{ndoi(r.get('doi')) for r in g} - {''} for g in groups]
    observations = collections.defaultdict(lambda: collections.defaultdict(list))
    for i, g in enumerate(groups):
        for r in g:
            if r.get('oa'):
                observations[r['pi'], r['oa']][i].append(r)
    edges = []
    for (pi, oa), by_component in observations.items():
        ix = list(by_component)
        # Contradictions inside an established R16 component remain source diagnostics, not new-join failures.
        for i in ix:
            g = by_component[i]
            if len({tuple(r.get('byline') or []) for r in g}) > 1:
                diagnostics.append(dict(kind='established_oa_byline_disagreement', pi=pi, oa=oa, component=keys[i], records=g))
        for pos, a in enumerate(ix):
            for b in ix[pos + 1:]:
                reason = None
                if doi_sets[a] and doi_sets[b] and not doi_sets[a] & doi_sets[b]:
                    reason = 'distinct_populated_doi_components'
                elif not doi_sets[a] and not doi_sets[b]:
                    reason = 'new_oa_bridge_without_doi_support'
                elif not all(compatible_bylines(x.get('byline') or [], y.get('byline') or [])
                             for x in by_component[a] for y in by_component[b]):
                    reason = 'new_oa_bridge_byline_unresolved'
                if reason:
                    diagnostics.append(dict(kind='new_oa_join_withheld', reason=reason, pi=pi, oa=oa,
                                            components=[keys[a], keys[b]], records=by_component[a] + by_component[b]))
                else:
                    edges.append((a, b, pi, oa))
    # Look ahead before any union. A missing-DOI component with two incompatible identified neighbors must not
    # choose whichever edge happens to be processed first (nor transitively connect those two publications).
    neighbors = collections.defaultdict(set)
    for a, b, _, _ in edges:
        if not doi_sets[a]: neighbors[a].add(b)
        if not doi_sets[b]: neighbors[b].add(a)
    ambiguous_empty = set()
    for empty, boundary in neighbors.items():
        boundary = list(boundary)
        reached = {boundary[0]}
        while True:
            expanded = reached | {j for i in reached for j in boundary if doi_sets[i] & doi_sets[j]}
            if expanded == reached:
                break
            reached = expanded
        if len(reached) != len(boundary):
            ambiguous_empty.add(empty)
            diagnostics.append(dict(kind='new_oa_join_withheld', reason='transitive_missing_doi_bridge',
                                    components=[keys[empty]] + [keys[i] for i in boundary],
                                    records=[r for i in [empty] + boundary for r in groups[i]]))
    for a, b, pi, oa in edges:
        if a in ambiguous_empty or b in ambiguous_empty:
            continue
        a, b = root(a), root(b)
        if a == b:
            continue
        if doi_sets[a] and doi_sets[b] and not doi_sets[a] & doi_sets[b]:
            diagnostics.append(dict(kind='new_oa_join_withheld', reason='component_doi_conflict_after_union', pi=pi, oa=oa,
                                    components=[keys[a], keys[b]], records=groups[a] + groups[b]))
            continue
        parent[b] = a
        doi_sets[a] |= doi_sets[b]
    components = collections.defaultdict(list)
    counts = collections.Counter()
    for i, g in enumerate(groups):
        components[root(i)].extend(g)
        counts[root(i)] += chapter_counts[keys[i]]
    out = []
    for i, g in components.items():
        selected = preferred(g) if preferred else None
        if selected is not None and not any(selected is r for r in g):
            raise EditionIdentityConflict([dict(reason='preferred target is not a complete eligible source', records=g)])
        g.sort(key=lambda r: (0 if r is selected else 1, edition_rank(r)))
        lead = dict(g[0])
        aliases, seen = [], {(lead['oa'], lead.get('work'), ndoi(lead.get('doi')))}
        for r in g[1:]:
            identity = (r['oa'], r.get('work'), ndoi(r.get('doi')))
            if identity not in seen:
                aliases.append(dict(oa=r['oa'], work=r.get('work'), doi=r.get('doi'), year=r['year'], venue=r.get('venue')))
                seen.add(identity)
        dups = [d for r in g for d in r.get('_dups') or []]
        aliases.extend({k: d[k] for k in ('oa', 'work', 'doi', 'year', 'venue')} for d in dups)
        lead['editions'] = aliases
        source_reviews = [d for r in g for d in r.get('sourceMetadataReviews') or []]
        if source_reviews:
            lead['sourceMetadataReviews'] = list({(d['id'], d['source_work_sha256']): d for d in source_reviews}.values())
        lead['_bylines'] = [(r['byline'], r['byline_school']) for r in g] + [(d['byline'], d['byline_school']) for d in dups]
        if counts[i]:
            lead['chapters_folded'] = counts[i]
        for field in ('_dups', '_edition_source', '_legacy_identity_key', '_eligible_editions', '_source_partition'):
            lead.pop(field, None)
        out.append(lead)
    n['edition_records_merged'] = sum(len(g) - 1 for g in components.values())
    n['new_oa_joins_withheld'] = sum(d['kind'] == 'new_oa_join_withheld' for d in diagnostics)
    n['source_distinct_same_oa_records'] = sum(d.get('reason') == 'distinct_populated_doi_components' for d in diagnostics) * 2
    return out


def listing_continuity_on(school):
    """R-PAP-37 is switched on per school by the charter ([rules].listing_continuity): Michigan since 2026-11-05; the other schools
    were measured and wait for the owner (docs/DECISIONS.md)."""
    return bool(_S.field(_S.get(school), 'rules.listing_continuity'))


def continuity_bridges(ctx):
    """R-PAP-28: add each PI's continuity periods (periods.bridge_periods) before the rows are made. The years that count are those
    of the PI's identified works whose own authorship names the school (institution lineage or raw affiliation)."""
    n, pis, inst, aff, blocked, anchored = ctx.n, ctx.pis, ctx.inst, ctx.aff, ctx.blocked, ctx.anchored
    years, other = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    for pi, w, a, cw, ident, page1 in ctx.hits:
        aid = (a.get('author') or {}).get('id')
        if aid in blocked[pi] or not (ident or (aid and anchored[pi].get(aid))):
            continue
        if any(inst == i.get('id') or inst in (i.get('lineage') or []) for i in a.get('institutions') or []) \
                or any(aff.search(z) for z in a.get('raw_affiliation_strings') or []):
            y = w.get('publication_year')
            if y:
                years[pi][int(y)] += 1
        elif a.get('institutions') and w.get('publication_year'):
            other[pi][int(w['publication_year'])] += 1  # R-PAP-29 guard: the PI's works of that year credited elsewhere
    for p in pis:
        moved = bool(p.get('listingsAfterMove')) or any('end_moved' in (e.get('kind') or '') for q in p['periods'] for e in q.get('evidence') or [])
        new = bridge_periods(p['periods'], years[p['pi']], moved)
        if new:
            p['periods'] = p['periods'] + new
            n['continuity_bridge_periods'] += len(new)
        lb = listing_bridge_periods(p, years[p['pi']], other[p['pi']], getattr(ctx, 'listing_covered', {}), moved) if listing_continuity_on(ctx.school) else []  # R-PAP-37
        if lb:
            p['periods'] = p['periods'] + lb
            n['listing_bridge_periods'] += len(lb)
    ctx.direct_years, ctx.other_years = years, other


def listing_review_prepass(ctx):
    """R-PAP-30 (2026-11-02, owner: accuracy pass; Ziyou Song at Michigan). Two review signals from OpenAlex, built before rows.
    (1) stale listing years: a year the PI has a department listing but no period, in which the PI's identified works credit
        another institution and none credits the school (2+ works). The listing may be a stale or visiting page (R-PAP-03's
        reasoning without an evidenced departure): the school is not credited from that listing; the year goes to the review list.
    (2) twin records: an advisee-route or unaffiliated-byline record whose twin (same normalized title, same PI) credits the PI
        to another institution and never to the school. The work was done elsewhere (Song's SSRN preprint, whose published
        record credits the National University of Singapore); the school is not credited; the work goes to the review list.
    Periods are never closed by this."""
    pis, inst, aff, blocked, anchored = ctx.pis, ctx.inst, ctx.aff, ctx.blocked, ctx.anchored
    year_ = collections.defaultdict(lambda: collections.defaultdict(lambda: dict(school=0, other=collections.Counter())))
    twin = collections.defaultdict(list)
    for pi, w, a, cw, ident, page1 in ctx.hits:
        aid = (a.get('author') or {}).get('id')
        if aid in blocked[pi] or not (ident or (aid and anchored[pi].get(aid))):
            continue

        insts = a.get('institutions') or []
        school = any(inst == i.get('id') or inst in (i.get('lineage') or []) for i in insts) or any(aff.search(z) for z in a.get('raw_affiliation_strings') or [])
        names = [i.get('display_name') for i in insts]
        y = w.get('publication_year')
        if y:
            if school:
                year_[pi][int(y)]['school'] += 1
            elif insts:
                year_[pi][int(y)]['other'].update(names[:1])
        t = norm_title(w.get('title'))
        if t:
            twin[(pi, t)].append((w['id'], school, names, w.get('publication_date') or str(w.get('publication_year') or '')))
    stale = collections.defaultdict(dict)
    for p in pis:
        lys = sorted(l['year'] for l in p.get('listings') or [])
        for l in p.get('listings') or []:
            y = l['year']
            if (y == lys[0] and y > 2016) or (y == lys[-1] and y < int(TODAY[:4])):
                continue  # an arrival or departure year: R-PAP-13's transition rules decide it (Tulsiani 2021, Mankoff 2019)
            covered = any(contains(q['start'], q['end'], f'{y}-06-30', q['asof'] or TODAY) != 'outside' for q in p['periods'])
            c = year_[p['pi']].get(y)
            if not covered and c and c['school'] == 0 and sum(c['other'].values()) >= 2:
                stale[p['pi']][y] = dict(pi=p['pi'], kind='listing_year', year=y, listing=dict(url=l.get('url'), quote=l.get('quote'), kind=l.get('kind')),
                                         works_at_other_institutions=dict(c['other'].most_common(3)), works_at_school=0, withheld=[])
    ctx.stale_years, ctx.twin_records, ctx.listing_review = stale, twin, []
    n = ctx.n
    n['stale_listing_pi_years'] = sum(len(v) for v in stale.values())


def lab_papers(ctx):
    """Every lab paper of the school: ctx.rows (with `_bylines` until the package is written)."""
    school, n, pis = ctx.school, ctx.n, ctx.pis
    funnel = collections.defaultdict(collections.Counter)
    ctx.funnel = funnel
    unit_tables(ctx)
    venue_tables(ctx)
    continuity_bridges(ctx)
    listing_review_prepass(ctx)
    rows, seen = rows_from_hits(ctx)
    recovered_rows(ctx, rows, seen)
    # A direct recovery (including a primary-page tie) does not resolve an explicit PI identity hold.
    # Keep the PI, website, appointments and members; withhold only scientific attribution until review resolves it.
    held = {p['pi'] for p in pis if p.get('identityHold')}
    n['paper_rows_withheld_by_identity_review'] = sum(r['pi'] in held for r in rows)
    rows = [r for r in rows if r['pi'] not in held]
    rows = drop_namesakes(rows, pis, ctx.reviewed_oa, n)
    # Exact owned-publication corrections precede quality, book folding and legacy R16 title components.
    rows = source_metadata.apply(ctx, rows, lambda w, title, r: venue_version_date(
        dict(w, title=title), ctx.dblp_venue[r['pi']])[0])
    rows, not_paper_samples = drop_not_papers(rows, ctx.dblp_nauth, n, ctx.dblp_pages, ctx.pid0)
    # Count distinct scientific chapters, not the number of OA/DBLP records describing one chapter. Full eligible
    # alternatives remain attached internally until the final edition selector; none are reconstructed from pointers.
    ctx.edition_source_diagnostics = []
    rows, translated_sources = eligible_untranslated_sources(rows, school)
    rows = collapse_eligible_sources(rows, n, diagnostics=ctx.edition_source_diagnostics)
    # books are one work, and a translation is not new work (2026-10-29, owner: best judgement): fold_books
    nv0 = sum(r.get('type') == 'book-chapter' and not r.get('venue') for r in rows)
    rows, n['book_chapters_folded'], translated = fold_books(rows, school)
    n['book_chapters_folded_by_doi_prefix'] = nv0 - sum(r.get('type') == 'book-chapter' and not r.get('venue') for r in rows)
    if translated is not None:
        n['translated_editions_dropped'] = (translated_sources or 0) + translated
    rows = merge_editions(rows, n, preferred=lambda group: reviewed_claims.preferred_edition(ctx, group),
                          diagnostics=ctx.edition_source_diagnostics)
    # Enrichment cannot lend identity or change ordinary edition groups/aliases.
    rows, filled_titles = title_enrichment.apply(ctx, rows, lambda w, title, r: venue_version_date(
        dict(w, title=title), ctx.dblp_venue[r['pi']])[0])
    if filled_titles:
        quality_counts = collections.Counter()
        quality_kept, quality_samples = drop_not_papers(filled_titles, ctx.dblp_nauth, quality_counts, ctx.dblp_pages, ctx.pid0)
        # Recheck R-PAP-15 per record. A singleton cannot regroup books or change aliases.
        untranslated = [r for r in quality_kept if fold_books([r], school)[0]]
        if n.get('translated_editions_dropped') is not None:
            n['translated_editions_dropped'] += len(quality_kept) - len(untranslated)
        quality_kept = untranslated
        n['not_paper_dropped'] += quality_counts['not_paper_dropped']
        for key, value in quality_counts.items():
            if key.startswith('not_paper:'):
                n[key] += value
        dropped_ids = {id(r) for r in filled_titles} - {id(r) for r in quality_kept}
        rows = [r for r in rows if id(r) not in dropped_ids]
        n['title_enrichment_quality_dropped'] += len(dropped_ids)
        for r in filled_titles:
            status = 'rejected' if id(r) in dropped_ids else 'passed'
            r['titleEnrichment']['quality_status'] = status
            for decision in ctx.paper_title_review['decisions']:
                if (decision['pi'], decision['oa'], decision['work']) == (r['pi'], r['oa'], r['work']):
                    decision['quality_status'] = status
        for why, samples in quality_samples.items():
            not_paper_samples[why] = (not_paper_samples[why] + samples)[:10]
    n['lab_papers'] = len(rows); n['lab_papers_in_collection'] = sum(bool(r['work']) for r in rows); n['lab_papers_new'] = n['lab_papers'] - n['lab_papers_in_collection']
    n['lab_papers_by_period'] = sum('periodId' in r['appointment'] for r in rows); n['lab_papers_by_listing'] = n['lab_papers'] - n['lab_papers_by_period']
    n.update({'identity:' + k: v for k, v in collections.Counter(r['identity'] for r in rows).items()})
    ctx.rows, ctx.not_paper_samples = rows, not_paper_samples
