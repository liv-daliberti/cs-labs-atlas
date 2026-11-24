"""A small JSON Schema validator for the atlas's data files (ROADMAP item 9). env/atlas has no jsonschema, and the env is
not edited for it; this covers the subset the schemas in schemas/ use:

  type (a name or a list of names: object, array, string, integer, number, boolean, null), enum, const, properties,
  required, additionalProperties (true, false or a schema), patternProperties, items, minItems, minimum, maximum,
  minLength, pattern (re.search), anyOf, oneOf, allOf, $ref to "#/$defs/<name>", description / title / $comment /
  examples (ignored).
  Two atlas keywords on the top-level schema: "x-format": "jsonl" or "csv" (the schema is for each line of a JSON-lines
  file, or each row of a CSV file as an object of strings keyed by the header)
  and "x-file": the path pattern the schema is for (documentation; tools/validate.py maps files to schemas).

validate(instance, schema) -> [(json path, message)], at most `limit` of them. Unknown keywords raise, so a schema
cannot silently use a feature the validator does not check.
usage: schema_check.py <schema.json> <data file>        (.gz is decompressed; prints the violations; exit 1 if any)
"""
import gzip
import json
import re
import sys
from pathlib import Path

TYPES = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'null': type(None)}
IGNORED = {'description', 'title', '$comment', 'examples', '$schema', '$id', 'default', 'x-file', 'x-format', 'x-kind',
           'x-writer', 'x-readers', 'x-rules', '$defs'}
KNOWN = IGNORED | {'type', 'enum', 'const', 'properties', 'required', 'additionalProperties', 'patternProperties', 'items',
                   'minItems', 'minimum', 'maximum', 'minLength', 'pattern', 'anyOf', 'oneOf', 'allOf', '$ref'}


def _is(v, t):
    if t == 'integer':
        return isinstance(v, int) and not isinstance(v, bool)
    if t == 'number':
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, TYPES[t])


class Validator:
    def __init__(self, schema, limit=200):
        self.root, self.limit, self.errors = schema, limit, []

    def err(self, path, msg):
        if len(self.errors) < self.limit:
            self.errors.append((path or '$', msg))

    def check(self, v, s, path=''):
        if len(self.errors) >= self.limit or s is True or s == {}:
            return
        unknown = set(s) - KNOWN
        if unknown:
            raise ValueError(f'schema at {path or "$"} uses unsupported keywords {sorted(unknown)}')
        if '$ref' in s:
            name = s['$ref'].split('/')[-1]
            self.check(v, self.root['$defs'][name], path)
        if 'type' in s:
            ts = s['type'] if isinstance(s['type'], list) else [s['type']]
            if not any(_is(v, t) for t in ts):
                self.err(path, f'type {type(v).__name__}, expected {"|".join(ts)}')
                return
        if 'const' in s and v != s['const']:
            self.err(path, f'{v!r} is not {s["const"]!r}')
        if 'enum' in s and v not in s['enum']:
            self.err(path, f'{str(v)[:80]!r} not in {s["enum"][:12]}')
        if isinstance(v, str):
            if 'minLength' in s and len(v) < s['minLength']:
                self.err(path, f'shorter than {s["minLength"]}')
            if 'pattern' in s and not re.search(s['pattern'], v):
                self.err(path, f'{v[:80]!r} does not match {s["pattern"]}')
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if 'minimum' in s and v < s['minimum']:
                self.err(path, f'{v} < {s["minimum"]}')
            if 'maximum' in s and v > s['maximum']:
                self.err(path, f'{v} > {s["maximum"]}')
        if isinstance(v, dict):
            for k in s.get('required') or []:
                if k not in v:
                    self.err(path, f'missing {k!r}')
            props, pats = s.get('properties') or {}, s.get('patternProperties') or {}
            for k, x in v.items():
                sub = f'{path}.{k}'
                if k in props:
                    self.check(x, props[k], sub)
                    continue
                hit = [ps for p, ps in pats.items() if re.search(p, k)]
                for ps in hit:
                    self.check(x, ps, sub)
                if not hit:
                    ap = s.get('additionalProperties', True)
                    if ap is False:
                        self.err(sub, 'property not in the schema')
                    elif isinstance(ap, dict):
                        self.check(x, ap, sub)
        if isinstance(v, list):
            if 'minItems' in s and len(v) < s['minItems']:
                self.err(path, f'fewer than {s["minItems"]} items')
            if 'items' in s:
                for i, x in enumerate(v):
                    self.check(x, s['items'], f'{path}[{i}]')
                    if len(self.errors) >= self.limit:
                        break
        for key, need in (('anyOf', 1), ('oneOf', 1)):
            if key in s:
                ok = 0
                for alt in s[key]:
                    sub = Validator(self.root, 1); sub.check(v, alt, path); ok += not sub.errors
                if (key == 'anyOf' and ok < need) or (key == 'oneOf' and ok != 1):
                    self.err(path, f'{key}: {ok} of {len(s[key])} alternatives match')
        for alt in s.get('allOf') or []:
            self.check(v, alt, path)


def validate(instance, schema, limit=200):
    V = Validator(schema, limit)
    V.check(instance, schema)
    return V.errors


def load(p):
    p = Path(p)
    b = p.read_bytes()
    if p.suffix == '.gz':
        b = gzip.decompress(b)
    name = p.name[:-3] if p.suffix == '.gz' else p.name
    if name.endswith('.jsonl'):
        return [json.loads(x) for x in b.decode().split('\n') if x.strip()]
    if name.endswith('.csv'):
        import csv, io
        return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
    return json.loads(b)


def validate_file(path, schema, limit=200):
    """Violations of one data file; a JSON-lines or CSV schema ("x-format": "jsonl" | "csv") is applied to each row ([n] in the path)."""
    data = load(path)
    if schema.get('x-format') in ('jsonl', 'csv'):
        out = []
        for i, row in enumerate(data):
            out += [(f'[{i}]' + (p if p != '$' else ''), m) for p, m in validate(row, schema, limit - len(out))]
            if len(out) >= limit:
                break
        return out
    return validate(data, schema, limit)


if __name__ == '__main__':
    errs = validate_file(sys.argv[2], json.loads(Path(sys.argv[1]).read_text()))
    for p, m in errs:
        print(f'{p}: {m}')
    print(f'{len(errs)} violation(s)' + (' (first 200)' if len(errs) >= 200 else ''))
    sys.exit(1 if errs else 0)
