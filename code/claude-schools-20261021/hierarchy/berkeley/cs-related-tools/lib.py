import json, re, sqlite3, unicodedata, sys
sys.path.insert(0, '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/berkeley/cs-related-tools')
import mpcap
H = mpcap.HERE
CANDS = json.load(open(f'{H}/hierarchy/berkeley/cs-related-candidates.json'))

def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def forms(c):
    out = set()
    for n in c['names'] + [c['name']]:
        n = fold(n)
        if ',' in n:
            a, b = [x.strip() for x in n.split(',', 1)]; n = f'{b} {a}'
        t = [x for x in re.split(r'[\s.]+', n) if x]
        if len(t) >= 2:
            out.add((t[0].lower(), t[-1].lower()))
    return out

def pages(like):
    con = mpcap.connect()
    rows = con.execute('select url, sha256, text, fetched_at from captures where status=200 and error is null and (url like ? or capture_url like ?)', (like, like)).fetchall()
    con.close(); return rows

def year_of(url, fetched_at):
    m = mpcap.WAYBACK_RX.match(url)
    return int(m.group(1)[:4]) if m else int(fetched_at[:4])

TITLE = re.compile(r"((?:Below [Tt]he Line,? )?(?:(?:Adjunct|Associate|Assistant|Teaching|Distinguished|Visiting|Senior|Continuing)\s)*(?:Professor|Lecturer|Professor of Teaching)(?: Emerit(?:us|a))?(?: in Residence)?(?:, Professor in the Graduate School)?(?:, Retired)?(?:, (?:Director|Dean|Chair|Associate Chair|EE Division Chair|CS Division Chair))?)")

def kind_of(url):
    u = url.split('berkeley.edu', 1)[-1]
    if '/Lists/EE/' in u: k = 'EECS-EE'
    elif '/Lists/CS/' in u: k = 'EECS-CS'
    else: k = 'EECS (all divisions)'
    if 'emerit' in u: k += ' emeriti'
    elif 'visiting' in u: k += ' visiting'
    elif 'teaching' in u: k += ' teaching'
    elif 'new.' in u: k += ' new faculty'
    return 'dept_listing:' + k

def eecs_rows(written_names):
    """Dated EECS listing rows naming the person: one per capture, quote = the name as written + the title as listed."""
    con = mpcap.connect()
    rows = con.execute("select url, sha256, text, fetched_at from captures where status=200 and error is null and url like '%eecs.berkeley.edu%Faculty/Lists/%'").fetchall()
    con.close(); out = []
    for url, sha, text, fa in rows:
        for nm in written_names:
            i = text.find(nm + ' ')
            if i < 0: continue
            m = TITLE.match(text, i + len(nm) + 1)
            if not m: continue
            q = text[i:m.end()]
            wm = mpcap.WAYBACK_RX.match(url)
            obs = (wm.group(1)[:4] + '-' + wm.group(1)[4:6] + '-' + wm.group(1)[6:8]) if wm else fa[:10]
            out.append(dict(url=url, sha256=sha, quote=q, observed=obs, kind=kind_of(url)))
            break
    return sorted(out, key=lambda r: r['observed'])

def adv_rows(written_names):
    """EECS Ph.D. dissertations (year pages 2016-2026) whose adviser field names the person exactly."""
    con = mpcap.connect()
    rows = con.execute("select url, sha256, text from captures where status=200 and url like '%Pubs/Dissertations/Years/%' order by url").fetchall()
    con.close(); out = []
    for url, sha, text in rows:
        for m in re.finditer(r'((?:[A-Z][\w\'.-]*(?: (?:[A-Z][\w\'.-]*|de|van|von|da|del|la))*)) \[advisor: ([^\]]+)\]', text):
            advs = [a.strip() for a in re.split(r',| and ', m.group(2)) if a.strip()]
            if any(a in written_names for a in advs):
                # the student's name: the words just before '[' that the page writes as the author (take last 2-4 capitalised tokens)
                pre = text[max(0, m.start(2) - 200):m.start(2) - len(' [advisor: ')]
                st = re.search(r'((?:\S+ ){0,3}\S+)$', pre).group(1)
                out.append(dict(url=url, sha256=sha, year=int(url[-9:-5]), quote=f"{text[m.start(2)-len('[advisor: ')-len(st)-1:m.end()]}", advisers=advs))
    return out

def written_forms(c):
    out = set()
    for n in c['names'] + [c['name']]:
        if ',' in n:
            a, b = [x.strip() for x in n.split(',', 1)]; n = f'{b} {a}'
        out.add(n)
        t = n.split()
        if len(t) >= 3: out.add(f'{t[0]} {t[-1]}')
    return sorted(out)

def student_rows(written_names):
    """EECS dissertation entries the person authored (a Berkeley Ph.D. student)."""
    con = mpcap.connect()
    rows = con.execute("select url, sha256, text from captures where status=200 and url like '%Pubs/Dissertations/Years/%' order by url").fetchall()
    con.close(); out = []
    for url, sha, text in rows:
        for nm in written_names:
            for m in re.finditer(re.escape(nm) + r' \[advisor: [^\]]+\]', text):
                out.append(dict(url=url, sha256=sha, year=int(url[-9:-5]), quote=m.group(0)))
    return out
