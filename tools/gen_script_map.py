"""Regenerate the generated block of docs/SCRIPT-MAP.md: the `bin/atlas` commands (from atlas_cli.COMMANDS) and the script classes
(from the R0 reachability inventory, scratch/refactor-1117/inventory.json, 2026-11-17). The retired-script ledger below the block is
hand-kept and checked by tests/test_script_map.py; this tool only rewrites what sits between the two markers.

  atlas run tools/gen_script_map.py [--inventory FILE] [--check]
"""
import argparse
import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
MAP = CODE / 'docs' / 'SCRIPT-MAP.md'
BEGIN, END = '<!-- generated:begin (tools/gen_script_map.py) -->', '<!-- generated:end -->'
DEFAULT_INV = CODE.parent / 'scratch' / 'refactor-1117' / 'inventory.json'
CLASSES = {'live-pipeline': 'reached from a live root (CLI command, stage gate, rebuild, collectors, release)',
           'live-adhoc': 'not reached, but ran in the last 14 days (heuristic)',
           'documented-manual': 'run by hand as documented in a doc',
           'school-one-off': 'one-school scripts kept as records',
           'dead': 'no live referrer and no run evidence (a candidate list, not a verdict)',
           'archived': 'under archive/', 'study-ai-writing': 'the ai-writing ML studies', 'test': 'tests'}


def commands():
    from atlas_cli import COMMANDS
    rows = ['| command | runs | what it does |', '|---|---|---|']
    for name, (kind, target, desc) in sorted(COMMANDS.items()):
        rows.append(f'| `atlas {name}` | `{target}` ({kind}) | {desc} |'.replace('\n', ' ').replace(' | ', ' \\| '))
    return rows


def classes(inv):
    d = json.load(open(inv))
    rows = ['| scope | class | files | lines | meaning |', '|---|---|---|---|---|']
    for k, v in sorted(d['counts'].items()):
        scope, cls = k.rsplit('/', 1) if '/' in k else (k, '')
        rows.append(f"| {scope} | {cls} | {v['files']} | {v['lines']} | {CLASSES.get(cls, '')} |")
    return rows, d.get('generated', '')


def block(inv):
    out = [BEGIN, '## Live commands (generated)', '',
           f'`bin/atlas <command>` (`atlas_cli/__init__.py` COMMANDS; {len(__import__("atlas_cli").COMMANDS)} commands). Regenerate: `atlas run tools/gen_script_map.py`.', '']
    out += commands()
    if Path(inv).exists():
        rows, gen = classes(inv)
        out += ['', f'## Script classes (generated from the R0 reachability inventory of {gen})', '',
                'Universe: every tracked `.py/.sh/.slurm` outside `vendor/`, plus `../world-atlas/scripts`. Edges are imports and name tokens; tests and docs never make a file live.',
                'Method and limits: `scratch/refactor-1117/inventory.md`.', ''] + rows
    out += ['', END]
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inventory', default=str(DEFAULT_INV))
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = MAP.read_text()
    new = block(a.inventory)
    if BEGIN in text:
        pre, rest = text.split(BEGIN, 1)
        post = rest.split(END, 1)[1]
        out = pre + new + post
    else:                                   # first run: insert before the first "## " section after the intro
        i = text.index('\n## ')
        out = text[:i] + '\n\n' + new + '\n' + text[i:]
    if a.check:
        sys.exit(0 if out == text else 1)
    MAP.write_text(out)
    print('wrote', MAP, len(out))


if __name__ == '__main__':
    main()
