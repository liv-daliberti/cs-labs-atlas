"""The R-PAP-30 review list of one school as Markdown: PI-years whose department listing OpenAlex contradicts (the PI's works
of that year credit another institution, none the school) and records whose twin credits the PI elsewhere only. Read from the
build's report.json (`staleListingReview`); nothing is changed and no period is closed: the owner decides each line.

usage: stale_listing_review.py <school> [--root DIR] [--out FILE]
  --root DIR   read DIR/<school>/report.json (a trial build's PI_HIERARCHY_OUT) instead of the school's package
"""
import argparse
import json
import sys
from pathlib import Path

import atlas_paths as P  # noqa: E402  (every path in one place)


def render(school, review):
    ly = [e for e in review if e['kind'] == 'listing_year']
    tw = [e for e in review if e['kind'] == 'twin_record']
    out = [f'# {school}: listings and records OpenAlex contradicts (R-PAP-30)', '',
           f'{len(ly)} PI-years with a department listing and no period, in which the PI\'s identified works credit other institutions '
           f'and none the school; {len(tw)} advisee-route or unaffiliated records whose twin credits the PI elsewhere only.', '']
    out += ['## Listing years', '', '| PI | year | listing | works elsewhere | papers withheld |', '|---|---|---|---|---|']
    for e in sorted(ly, key=lambda e: (e['pi'], e['year'])):
        q = ' '.join(str(e['listing'].get('quote') or '').split())[:90].replace('|', '/')
        el = ', '.join(f'{k} ({v})' for k, v in e['works_at_other_institutions'].items())
        out.append(f"| {e['pi']} | {e['year']} | {q} ({e['listing'].get('url')}) | {el} | {e.get('withheld_n', len(e.get('withheld') or []))} |")
    out += ['', '## Records with a twin elsewhere', '', '| PI | year | title | twin credits | withheld |', '|---|---|---|---|---|']
    for e in sorted(tw, key=lambda e: (e['pi'], str(e['year']))):
        t = e['twin'][0]
        out.append(f"| {e['pi']} | {e['year']} | {str(e['title'])[:80].replace('|', '/')} | {', '.join(t['institutions'])} ({t.get('date')}) | {'yes' if e.get('withheld') else 'no'} |")
    return '\n'.join(out) + '\n'


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('school'); ap.add_argument('--root'); ap.add_argument('--out')
    a = ap.parse_args(argv)
    f = Path(a.root) / a.school / 'report.json' if a.root else P.data('report.json', a.school)
    text = render(a.school, json.loads(f.read_text()).get('staleListingReview') or [])
    Path(a.out).write_text(text) if a.out else sys.stdout.write(text)


if __name__ == '__main__':
    main(sys.argv[1:])
