"""Coordination directory <LEASES>/coord/ (V4b, owner-approved 2026-11-17, docs/PROCESS-V4-PROPOSAL.md 3.8): one place for the log, the owner questions and the decisions.

  atlas note "text" [--task T] [--school S]            append one UTC line to LOG.md (session from --session / $ATLAS_SESSION)
  atlas ask --school S [--rec "..."] [--task T] "question"     add a block to QUESTIONS.md (status open); prints its id
  atlas ask --list [--open] [--school S] [--full]       one line per question (--full: the whole block)
  atlas answer Q-0007 "answer text"                    mark the question answered (the owner's words; also logged)
  atlas decide "decision" [--ref Q-0007|T012|docs/X.md]  append to DECISIONS.md (per-person decisions go to the evidence store, not here)
  atlas coord sync-legacy                              copy lines appended to the frozen old log (scratch/top25-goal-1107/OVERNIGHT-LOG.md) into LOG.md tagged 'legacy'
  atlas coord cutover | import-questions               the one-off migration (both refuse to run twice)

Every write holds flock on coord/.coord.lock and is ONE write() of whole lines, so concurrent writers never interleave. LOG.md and DECISIONS.md are append only;
QUESTIONS.md is rewritten atomically only by `answer`. The old OVERNIGHT-LOG.md / OVERNIGHT-QUESTIONS.md stay where they are as read-only archives.
"""
import argparse, contextlib, datetime, fcntl, json, os, re, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402

LEGACY_DIR = Path(P.ROOT) / 'scratch' / 'top25-goal-1107'
STATE = '.legacy-sync.json'


def coord_dir(root=None):
    return Path(root or Path(P.LEASES) / 'coord')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def session_id(given=None):
    s = given or os.environ.get('ATLAS_SESSION') or os.environ.get('CLAUDE_SESSION_ID')
    if not s:
        raise SystemExit('no session id: pass --session or set ATLAS_SESSION')
    return s


@contextlib.contextmanager
def locked(root):
    d = coord_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / '.coord.lock', 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield d
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _append(path, text):
    """One O_APPEND write of whole lines (the caller holds the lock)."""
    data = text if text.endswith('\n') else text + '\n'
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o664)
    try:
        os.write(fd, data.encode())
    finally:
        os.close(fd)


def one_line(s):
    return re.sub(r'\s+', ' ', s).strip()


def log_line(text, session, task='', school='', ts=None, tag=''):
    head = f'- {ts or utc()} UTC {session}' + (f' ({task})' if task else '') + (f' [{school}]' if school else '') + (f' {tag}' if tag else '')
    return f'{head}: {one_line(text)}'


def note(text, session=None, task='', school='', root=None):
    line = log_line(text, session_id(session), task, school)
    with locked(root) as d:
        _append(d / 'LOG.md', line)
    return line


# ---- questions ----
HEAD = re.compile(r'^## (Q-\d{4,}) \| school: (\S*) \| (open|answered)$')


def read_questions(root=None):
    p = coord_dir(root) / 'QUESTIONS.md'
    qs, cur = [], None
    for line in (p.read_text().splitlines() if p.exists() else []):
        m = HEAD.match(line)
        if m:
            cur = {'id': m.group(1), 'school': m.group(2), 'status': m.group(3), 'lines': [line], 'text': ''}
            qs.append(cur)
        elif cur is not None:
            cur['lines'].append(line)
    for q in qs:
        q['text'] = '\n'.join(q['lines'])
        m = re.search(r'^- question: (.*?)(?=^- (?:recommendation|task|source|asked|answer):)', q['text'] + '\n- answer:', re.S | re.M)
        q['question'] = re.sub(r'\n  ', '\n', m.group(1)).strip() if m else ''
    return qs


def _field(label, text):
    return f'- {label}: ' + text.strip().replace('\n', '\n  ')


def block(qid, school, question, rec, session, task='', source='', asked=None):
    parts = [f'## {qid} | school: {school or "-"} | open', _field('asked', f'{asked or utc()} {session}')]
    if task:
        parts.append(_field('task', task))
    if source:
        parts.append(_field('source', source))
    parts += [_field('question', question), _field('recommendation', rec or '(none given)'), '- answer:']
    return '\n'.join(parts) + '\n\n'


def next_id(root):
    return 'Q-%04d' % (1 + max([int(q['id'][2:]) for q in read_questions(root)] + [0]))


def ask(question, school, rec='', task='', session=None, root=None):
    s = session_id(session)
    with locked(root) as d:
        qid = next_id(root)
        _append(d / 'QUESTIONS.md', block(qid, school, question, rec, s, task))
        _append(d / 'LOG.md', log_line(f'asked the owner {qid}: {question[:100]}', s, task, school))
    return qid


def answer(qid, text, session=None, root=None):
    s = session_id(session)
    with locked(root) as d:
        p = d / 'QUESTIONS.md'
        src = p.read_text() if p.exists() else ''
        parts = re.split(r'(?m)^(?=## Q-\d)', src)
        hit = False
        for i, b in enumerate(parts):
            m = HEAD.match(b.splitlines()[0]) if b.strip() else None
            if m and m.group(1) == qid:
                hit = True
                b = re.sub(r'(?m)^(## Q-\d+ \| school: \S* \| )(open|answered)$', r'\1answered', b, count=1)
                b = re.sub(r'(?m)^- answer:.*(\n  .*)*', lambda _m: _field('answer', f'[{utc()} {s}] {one_line(text)}'), b, count=1)
                parts[i] = b
        if not hit:
            return False
        tmp = p.with_suffix('.tmp')
        tmp.write_text(''.join(parts))
        os.replace(tmp, p)
        _append(d / 'LOG.md', log_line(f'owner answered {qid}: {text[:100]}', s))
    return True


def decide(text, ref='', session=None, root=None):
    s = session_id(session)
    with locked(root) as d:
        p = d / 'DECISIONS.md'
        n = 1 + len(re.findall(r'(?m)^- D-\d+ ', p.read_text())) if p.exists() else 1
        did = 'D-%04d' % n
        _append(p, f'- {did} {utc()[:10]} ({s}){" ref " + ref if ref else ""}: {one_line(text)}')
        _append(d / 'LOG.md', log_line(f'decision {did}: {text[:100]}', s))
    return did


# ---- migration from the old files ----
def parse_old_questions(text):
    """(first_line, last_line, text) per block: a '## ' heading owns its body, only the FIRST bullet right under a heading belongs to it; every other '- ' line starts a new block."""
    blocks, cur, prev_blank = [], None, True
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith('## '):
            cur = [i, i, [line], True]; blocks.append(cur)
        elif line.startswith('- ') and not (cur and cur[3] and len(cur[2]) == 1 and not prev_blank):
            cur = [i, i, [line], False]; blocks.append(cur)
        elif line.strip() and cur is not None:
            cur[2].append(line); cur[1] = i
        prev_blank = not line.strip()
    return [(a, b, '\n'.join(t)) for a, b, t, _ in blocks]


def school_of(text, keys):
    m = re.match(r'^(?:- )?\[([a-z0-9-]+)\]', text)
    if m and m.group(1) in keys:
        return m.group(1)
    best = None
    for k in keys:
        mm = re.search(r'(?<![A-Za-z0-9])' + re.escape(k) + r'(?![A-Za-z0-9])', text, re.I)
        if mm and (best is None or mm.start() < best[0]):
            best = (mm.start(), k)
    return best[1] if best else ''


def is_open(text):
    return not re.search(r'ANSWERED|RESOLVED', text) or bool(re.search(r'(still|remaining) open', text, re.I))


def import_questions(session=None, root=None, old=None, schools_dir=None):
    s = session_id(session)
    old = Path(old or LEGACY_DIR / 'OVERNIGHT-QUESTIONS.md')
    keys = sorted(p.stem for p in Path(schools_dir or Path(__file__).resolve().parents[1] / 'schools').glob('*.toml') if p.stem != 'TEMPLATE')
    blocks = parse_old_questions(old.read_text())
    rel = 'scratch/top25-goal-1107/OVERNIGHT-QUESTIONS.md'
    with locked(root) as d:
        if any('- source: ' + rel in q['text'] for q in read_questions(root)):
            raise SystemExit('import-questions: already imported (QUESTIONS.md names the old file as a source)')
        n0, out = int(next_id(root)[2:]), []
        keep = [b for b in blocks if is_open(b[2])]
        for i, (a, b, text) in enumerate(keep):
            out.append(block('Q-%04d' % (n0 + i), school_of(text, keys), text, '(not separated in the original; the recommendation, if any, is in the text above)', s,
                             source=f'{rel} lines {a}-{b} (no ANSWERED/RESOLVED mark in the old file)', asked='legacy'))
        _append(d / 'QUESTIONS.md', ''.join(out))
        _append(d / 'LOG.md', log_line(f'imported {len(keep)} of {len(blocks)} old question blocks into QUESTIONS.md (blocks marked ANSWERED/RESOLVED stay only in the archive)', s))
    return len(keep), len(blocks)


def sync_legacy(root=None, old=None):
    """Append complete lines added to the old log after the frozen mark to LOG.md, tagged 'legacy'. Returns the number of lines."""
    with locked(root) as d:
        sp = d / STATE
        if not sp.exists():
            raise SystemExit('sync-legacy: no frozen mark yet (run `atlas coord cutover` once)')
        st = json.loads(sp.read_text())
        with open(old or st['log'], 'rb') as f:
            f.seek(st['offset'])
            data = f.read()
        cut = data.rfind(b'\n') + 1            # a half-written last line waits for the next sync
        lines = [x for x in data[:cut].decode('utf-8', 'replace').splitlines() if x.strip()]
        if lines:
            ts = utc()
            _append(d / 'LOG.md', '\n'.join(f'- {ts} UTC legacy: {one_line(x.lstrip("- ").lstrip())}' for x in lines))
        st['offset'] += cut
        st['last_sync'] = utc()
        sp.write_text(json.dumps(st))
    return len(lines)


def cutover(session=None, root=None, old=None):
    """Atomic cutover: the last line of the old log and the first of LOG.md say so; the old file's offset after its last line is the frozen mark."""
    s = session_id(session)
    old = Path(old or LEGACY_DIR / 'OVERNIGHT-LOG.md')
    with locked(root) as d:
        if (d / STATE).exists():
            raise SystemExit('cutover: already done (see coord/.legacy-sync.json)')
        t = utc()
        mark = f'- {t} UTC {s} (V4b): FROZEN. The coordination log moved to leases/coord/LOG.md (atlas note "..."). This file is a read-only archive; stray lines appended below are copied by `atlas coord sync-legacy`.'
        size = old.stat().st_size
        _append(old, mark)
        with open(old, 'rb') as f:
            f.seek(size)
            tail = f.read()
        offset = size + tail.index(mark.encode()) + len(mark.encode()) + 1          # just after our line, even if another writer got in before it
        _append(d / 'LOG.md', f'- {t} UTC {s} (V4b): LOG START. Old log frozen from {t} (OVERNIGHT-LOG.md byte {offset}, 1.1 MB archive, read-only); its last line says so. Lines appended to it later are copied here as "legacy" by `atlas coord sync-legacy`.')
        (d / STATE).write_text(json.dumps({'log': str(old), 'frozen_at': t, 'offset': offset}))
        for name, head in (('QUESTIONS.md', '# Owner questions (one block per question; `atlas ask`, `atlas answer`)\n\nOld questions: scratch/top25-goal-1107/OVERNIGHT-QUESTIONS.md (read-only archive).\n\n'),
                           ('DECISIONS.md', '# Owner decisions (`atlas decide`; per-person decisions go to the evidence store)\n\n')):
            if not (d / name).exists():
                _append(d / name, head)
    return t, offset


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--root', help='coord directory (tests)'); common.add_argument('--session')
    ap = argparse.ArgumentParser(prog='atlas', description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('note', parents=[common]); p.add_argument('text'); p.add_argument('--task', default=''); p.add_argument('--school', default='')
    p = sub.add_parser('ask', parents=[common]); p.add_argument('question', nargs='?'); p.add_argument('--school', default=''); p.add_argument('--rec', default=''); p.add_argument('--task', default='')
    p.add_argument('--list', action='store_true'); p.add_argument('--open', action='store_true'); p.add_argument('--full', action='store_true')
    p = sub.add_parser('answer', parents=[common]); p.add_argument('qid'); p.add_argument('text')
    p = sub.add_parser('decide', parents=[common]); p.add_argument('text'); p.add_argument('--ref', default='')
    p = sub.add_parser('coord', parents=[common]); p.add_argument('what', choices=('sync-legacy', 'cutover', 'import-questions'))
    a = ap.parse_args(argv)
    if a.cmd == 'note':
        print(note(a.text, a.session, a.task, a.school, a.root))
    elif a.cmd == 'ask':
        if a.list:
            for q in read_questions(a.root):
                if (not a.open or q['status'] == 'open') and (not a.school or q['school'] == a.school):
                    print(q['text'] if a.full else f"{q['id']} [{q['school']}] {q['status']}: {one_line(q['question'])[:110]}")
        elif not a.question or not a.school:
            raise SystemExit('ask: --school S and the question are required (or --list)')
        else:
            print(ask(a.question, a.school, a.rec, a.task, a.session, a.root))
    elif a.cmd == 'answer':
        if not answer(a.qid, a.text, a.session, a.root):
            print(f'no such question {a.qid}', file=sys.stderr)
            return 1
        print(f'{a.qid} answered')
    elif a.cmd == 'decide':
        print(decide(a.text, a.ref, a.session, a.root))
    elif a.what == 'sync-legacy':
        print(f'sync-legacy: {sync_legacy(a.root)} line(s) copied')
    elif a.what == 'cutover':
        print('cutover at %s, old log offset %d' % cutover(a.session, a.root))
    else:
        print('imported %d of %d old question blocks' % import_questions(a.session, a.root))
    return 0


if __name__ == '__main__':
    sys.exit(main())
