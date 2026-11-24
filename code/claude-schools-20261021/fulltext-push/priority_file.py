"""Priority file for the download loops (2026-11-03, owner): the link-only papers still waiting in the download queue go first.

A link-only paper is a reader row of a release (reader/<school>.jsonl.gz) with decision 'link', no stored copy and a link_basis
other than 'confirmed_copy': the site links to an open copy confirmed at the source, and we hold no local copy. It is *queued* when
the release's unavailability ledger (hierarchy/<school>/unavailable.jsonl.gz) gives it reason_code found_awaiting_download or
pending_retry. Every other ledger code is left out: the policy-blocked ones (robots_disallowed, bot challenge, login, paywall_only)
must stay blocked, and the rest has nothing queued to attempt.

usage: priority_file.py <school> [<school> ...] [--release DIR] [--out-dir DIR] [--measure]
  writes <out-dir>/<school>-priority-work-ids.tsv (default out-dir = FT_RAW; default release = RELEASES/latest):
  '#' comment lines, then work_id TAB paper key TAB reason_code TAB link_basis. --measure prints the per-school counts instead.
"""
import gzip, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

QUEUED = ('found_awaiting_download', 'pending_retry')
BLOCKED = ('open_copy_robots_disallowed', 'open_copy_bot_challenge', 'open_copy_behind_login', 'paywall_only')


def priority_path(school, out_dir=None):
    return Path(out_dir or F.P.FT_RAW) / f'{school}-priority-work-ids.tsv'


def release_dir(release=None):
    return Path(release) if release else (Path(F.P.RELEASES) / 'latest').resolve()


def link_only_rows(school, release):
    """[(reader row, ledger record or None)] for the school's link-only papers in the release."""
    release = Path(release)
    led = {}
    with gzip.open(release / 'hierarchy' / school / 'unavailable.jsonl.gz', 'rt') as f:
        for line in f:
            r = json.loads(line)
            led[r['key']] = r
    out = []
    with gzip.open(release / 'reader' / f'{school}.jsonl.gz', 'rt') as f:
        for line in f:
            r = json.loads(line)
            if r.get('decision') == 'link' and not r.get('stored_copy') and r.get('link_basis') not in (None, 'confirmed_copy'):
                out.append((r, led.get(r['key'])))
    return out


def classify(rec):
    """'queued' | 'blocked' | 'other' | 'no_ledger' for a ledger record."""
    if rec is None:
        return 'no_ledger'
    code = rec.get('reason_code')
    return 'queued' if code in QUEUED else 'blocked' if code in BLOCKED else 'other'


def measure(school, release):
    n = Counter()
    for r, rec in link_only_rows(school, release):
        c = classify(rec)
        n['total'] += 1
        n[c] += 1
        if c == 'queued':
            n[rec['reason_code']] += 1
        if c in ('blocked', 'other'):
            n['code:' + rec['reason_code']] += 1
    return dict(n)


def queued_entries(school, release):
    return [(rec['work_id'], r['key'], rec['reason_code'], r['link_basis'])
            for r, rec in link_only_rows(school, release) if classify(rec) == 'queued' and rec.get('work_id')]


def write(school, release, out_dir=None):
    rows = queued_entries(school, release)
    p = priority_path(school, out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(f'# {school} link-only papers queued for download, from release {Path(release).name}\n'
                   + ''.join('\t'.join(r) + '\n' for r in rows))
    tmp.replace(p)
    return p, len(rows)


def read_ids(path):
    """The work ids of a priority file (first column; blank and '#' lines skipped)."""
    ids = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            ids.append(line.split('\t')[0].strip())
    return list(dict.fromkeys(i for i in ids if i))


def main(argv):
    args = list(argv)
    opts = {}
    for flag in ('--release', '--out-dir'):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    do_measure = '--measure' in args
    schools = [a for a in args if not a.startswith('--')]
    rel = release_dir(opts.get('--release'))
    for s in schools:
        if do_measure:
            print(s, json.dumps(measure(s, rel), sort_keys=True))
        else:
            p, n = write(s, rel, opts.get('--out-dir'))
            print(json.dumps(dict(school=s, release=rel.name, file=str(p), queued=n)), flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
