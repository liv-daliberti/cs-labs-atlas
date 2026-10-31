"""The data dictionary (ROADMAP item 9): docs/DATA-DICTIONARY.md rendered from the schemas in schemas/*.schema.json.

One section per file kind: the path pattern (x-file), kind (derived: built by a tool; reviewed: a decision file tracked in
git), format (JSON, JSON lines with the schema per line, CSV with the schema per row), writer and main readers, then a
table of every field: dotted path ([] an array item, <key> a map key, <key ~ /re/> a pattern key), type, required,
meaning (description), allowed values (enum, const, pattern, range, examples) and the rule ids of docs/RULES.md (x-rules).
Shapes a schema shares through $defs get their own table after the section; a $comment on a node holding anyOf/allOf
constraints is listed under "Constraints".

The output depends only on the schemas (files in name order, fields in schema order, no timestamps), so a rerun on the
same schemas gives the same bytes; --check exits 1 when the file on disk differs from a fresh render.
usage: data_dictionary.py [--schemas DIR] [--out PATH] [--check]
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMAT = {'jsonl': 'JSON lines (the schema describes each line)', 'csv': 'CSV (the schema describes each row; every value is a string, empty for none)'}
KIND = {'derived': 'derived (built by a tool; never hand-edited)', 'reviewed': 'reviewed (a decision file, tracked in git)'}


def cell(s):
    """Markdown table cell text: pipes escaped (also inside code spans, as GitHub tables need), newlines folded."""
    return str(s).replace('|', '\\|').replace('\n', ' ').strip()


def code(s):
    s = str(s)
    return '`` ' + s + ' ``' if '`' in s else '`' + s + '`'


def jval(v):
    return 'null' if v is None else (json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)


def ref_name(s):
    return s['$ref'].split('/')[-1] if isinstance(s, dict) and '$ref' in s else None


def nullable_ref(s):
    """anyOf [{type: null}, {$ref}] -> the def name, else None."""
    alts = s.get('anyOf') if isinstance(s, dict) else None
    if alts and len(alts) == 2 and {'type': 'null'} in alts:
        other = next(a for a in alts if a != {'type': 'null'})
        return ref_name(other)
    return None


def type_of(s):
    """A short type text for one schema node."""
    if not isinstance(s, dict) or not s:
        return 'any'
    if '$ref' in s:
        return f'{code(ref_name(s))} (shape below)'
    nr = nullable_ref(s)
    if nr:
        return f'{code(nr)} | null'
    for key in ('oneOf', 'anyOf'):
        alts = [a for a in s.get(key) or [] if 'type' in a or '$ref' in a]
        if alts and 'type' not in s:
            return ' | '.join(dict.fromkeys(type_of(a) for a in alts))
    ts = s.get('type')
    ts = ts if isinstance(ts, list) else [ts] if ts else []
    out = []
    for t in ts:
        if t == 'array' and isinstance(s.get('items'), dict):
            out.append('array of ' + (code(ref_name(s['items'])) if '$ref' in s['items'] else type_of(s['items'])))
        elif t == 'object' and isinstance(s.get('additionalProperties'), dict) and not s.get('properties'):
            out.append('map')
        else:
            out.append(t)
    return ' | '.join(out) or 'any'


def allowed(s):
    """Enum, const, pattern, range, length and examples of one node (and of its array items)."""
    if not isinstance(s, dict):
        return ''
    out = []
    if 'enum' in s:
        out.append('one of ' + ', '.join(code(jval(v)) for v in s['enum']))
    if 'const' in s:
        out.append('always ' + code(jval(s['const'])))
    if 'pattern' in s:
        out.append('pattern ' + code(s['pattern']))
    lo, hi = s.get('minimum'), s.get('maximum')
    if lo is not None and hi is not None:
        out.append(f'{lo} to {hi}')
    elif lo is not None:
        out.append(f'at least {lo}')
    elif hi is not None:
        out.append(f'at most {hi}')
    if s.get('minItems'):
        out.append(f"at least {s['minItems']} item(s)")
    if s.get('minLength'):
        out.append('non-empty' if s['minLength'] == 1 else f"at least {s['minLength']} characters")
    if s.get('additionalProperties') is False and s.get('properties'):
        out.append('no other keys')
    it = s.get('items')
    if isinstance(it, dict) and '$ref' not in it and any(k in it for k in ('enum', 'pattern', 'const', 'minimum')):
        out.append('items: ' + allowed(it))
    if s.get('examples'):
        out.append('e.g. ' + ', '.join(code(jval(v)) for v in s['examples']))
    return '; '.join(out)


class Renderer:
    def __init__(self, schema):
        self.schema = schema
        self.defs_used = []
        self.constraints = []

    def use(self, name):
        if name and name not in self.defs_used:
            self.defs_used.append(name)

    def rows(self, s, path, req, out):
        """Table rows for node `s` at `path` (req: 'yes' / 'no' / '—'), then its children."""
        if not isinstance(s, dict):
            return
        scalar_item = path.endswith('[]') and not s.get('description') and not ({'properties', 'items', '$ref', 'anyOf', 'oneOf'} & set(s))
        if path and not scalar_item:  # a plain item of a scalar array is described by its array's row
            out.append([code(path), type_of(s), req, s.get('description', ''), allowed(s), ', '.join(s.get('x-rules') or [])])
        self.children(s, path, out)

    def children(self, s, path, out):
        self.use(ref_name(s))
        self.use(nullable_ref(s))
        if s.get('$comment') and any(k in s for k in ('anyOf', 'allOf', 'oneOf')):
            self.constraints.append((path or '(each record)', s['$comment']))
        for key in ('oneOf', 'anyOf'):  # typed alternatives with their own fields: their fields under the same path
            for a in s.get(key) or []:
                self.use(ref_name(a))
                if isinstance(a, dict) and a.get('properties') and 'type' in a:
                    self.props(a, path, out)
                elif isinstance(a, dict) and isinstance(a.get('items'), dict):
                    self.rows(a['items'], path + '[]', '—', out)
        ts = s.get('type') if isinstance(s.get('type'), list) else [s.get('type')]
        if 'object' in ts or s.get('properties') or s.get('patternProperties'):
            self.props(s, path, out)
        if isinstance(s.get('items'), dict):
            it = s['items']
            if '$ref' in it:
                self.use(ref_name(it))
            else:
                self.rows(it, path + '[]', '—', out)

    def props(self, s, path, out):
        req = set(s.get('required') or [])
        for k, v in (s.get('properties') or {}).items():
            self.rows(v, f'{path}.{k}' if path else k, 'yes' if k in req else 'no', out)
        for pat, v in (s.get('patternProperties') or {}).items():
            self.rows(v, f'{path}.<key ~ /{pat}/>' if path else f'<key ~ /{pat}/>', '—', out)
        ap = s.get('additionalProperties')
        if isinstance(ap, dict):
            if '$ref' in ap:
                self.use(ref_name(ap))
                out.append([code(f'{path}.<key>' if path else '<key>'), type_of(ap), '—', ap.get('description', ''), '', ''])
            else:
                self.rows(ap, f'{path}.<key>' if path else '<key>', '—', out)


def table(rows):
    L = ['| Field | Type | Required | Meaning | Allowed values | Rules |', '|---|---|---|---|---|---|']
    for r in rows:
        L.append('| ' + ' | '.join(cell(x) for x in r) + ' |')
    return L


def anchor(text):
    """The GitHub-style anchor of a heading."""
    a = ''.join(ch for ch in text.lower() if ch.isalnum() or ch in ' -_').replace(' ', '-')
    return a


def place(path):
    """Where a file sits, for the order: a school's package, the shared hierarchy files, the export, the tree, the rest."""
    for i, pre in enumerate(('hierarchy/<school>/', 'hierarchy/', 'export/', 'schools/')):
        if str(path).startswith(pre):
            return i
    return 4


def section(name, s):
    R = Renderer(s)
    L = [f"## {code(s.get('x-file', name))}", '']
    if s.get('description'):
        L += [s['description'], '']
    L.append(f'- schema: `schemas/{name}.schema.json`')
    L.append(f"- kind: {KIND.get(s.get('x-kind'), s.get('x-kind', ''))}")
    L.append(f"- format: {FORMAT.get(s.get('x-format'), 'JSON')}")
    L.append(f"- writer: {s.get('x-writer', '')}")
    if s.get('x-readers'):
        L.append('- readers: ' + ', '.join(s['x-readers']))
    if s.get('x-rules'):
        L.append('- rules: ' + ', '.join(s['x-rules']))
    L.append('')
    rows = []
    top = s.get('type')
    if top == 'array' or '$ref' in s.get('items', {}):
        L += [f"The file is an array of {type_of(s['items']) if '$ref' in s['items'] else 'items'}.", '']
        if '$ref' in s['items']:
            R.use(ref_name(s['items']))
        else:
            R.rows(s['items'], '[]', '—', rows)
    else:
        R.children(s, '', rows)
    if rows:
        L += table(rows) + ['']
    done = set()
    while len(done) < len(R.defs_used):
        d = next(x for x in R.defs_used if x not in done)
        done.add(d)
        ds = s.get('$defs', {}).get(d, {})
        drows = []
        R.children(ds, '', drows)
        L += [f'### {name}: shape `{d}`', '']
        if ds.get('description'):
            L += [ds['description'], '']
        if drows:
            L += table(drows) + ['']
    if R.constraints:
        L += ['Constraints:', ''] + [f'- {code(p)}: {c}' for p, c in R.constraints] + ['']
    return L


def render(schema_dir):
    schemas = {p.name[:-len('.schema.json')]: json.loads(p.read_text()) for p in sorted(Path(schema_dir).glob('*.schema.json'))}
    order = sorted(schemas, key=lambda n: (0 if schemas[n].get('x-kind') == 'derived' else 1, place(schemas[n].get('x-file', n)),
                                           str(schemas[n].get('x-file', n)).lower(), n))
    L = ['# Data dictionary', '',
         'Generated by `tools/data_dictionary.py` from `schemas/*.schema.json`; do not edit by hand (edit the schema and rerun). '
         '`tools/schema_check.py <schema> <file>` checks a file against its schema. Rule ids refer to `docs/RULES.md`; ids to `docs/IDS.md`.', '',
         'Paths: `a.b` a key inside an object, `[]` an array item, `<key>` any key of a map, `<key ~ /re/>` a key matching the pattern. '
         '"Required" is what the writer always writes (`—` for array items and map values).', '']
    for kind, title in (('derived', 'Derived files'), ('reviewed', 'Reviewed decision files')):
        names = [n for n in order if schemas[n].get('x-kind') == kind]
        if names:
            L += [f'**{title}**', ''] + [f"- [{code(schemas[n].get('x-file', n))}](#{anchor(schemas[n].get('x-file', n))})" for n in names] + ['']
    for n in order:
        L += section(n, schemas[n])
    return '\n'.join(L).rstrip('\n') + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--schemas', default=str(ROOT / 'schemas'))
    ap.add_argument('--out', default=str(ROOT / 'docs' / 'DATA-DICTIONARY.md'))
    ap.add_argument('--check', action='store_true', help='exit 1 when the file differs from a fresh render; write nothing')
    a = ap.parse_args(argv)
    text = render(a.schemas)
    out = Path(a.out)
    if a.check:
        same = out.exists() and out.read_text() == text
        print('up to date' if same else f'{out} differs from the schemas: rerun tools/data_dictionary.py')
        return 0 if same else 1
    out.write_text(text)
    print(f'{out}: {text.count(chr(10))} lines')
    return 0


if __name__ == '__main__':
    sys.exit(main())
