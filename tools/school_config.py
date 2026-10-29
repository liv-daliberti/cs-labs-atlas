"""The school charters (schools/<key>.toml): one place every stage tool learns a school from (protocol stage 0).

Python   import school_config as S
         S.keys()              every configured school, in `order` (TEMPLATE excluded)
         S.released()          the released schools (status = "released"); atlas_paths.SCHOOL_IDS is the same list
         S.get('michigan')     the parsed charter (dict)
         S.inst_ids(k)         lineage institution ids (['I27837315']); S.inst(k) the primary one
         S.sweep_ids(k)        lineage + related ids (what the OpenAlex sweep filters on)
         S.aff(k)              the affiliation regex (str); S.aff_rx(k) compiled, case-insensitive
         S.short_names(), S.full_names(), S.computing(k), S.dblp_sweep(k), S.own_units(k)
CLI      school_config.py --check [key ...]     validate charters: required fields, ids, regex and its test cases
         school_config.py <key> [dotted.field]  print a charter or one field (JSON)

TOML is read with tomllib (3.11+) or tomli (the 3.10 env). Every charter field is documented in schools/TEMPLATE.toml.
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

try:
    import tomllib as _toml
except ImportError:  # Python 3.10
    import tomli as _toml

DIR = P.SCHOOL_CONFIGS
REQUIRED = ['key', 'name', 'short', 'status', 'order', 'ids.openalex', 'ids.ror', 'affiliation.regex']
_cache = {}


def _path(key):
    return DIR / f'{key}.toml'


def get(key):
    if key not in _cache:
        p = _path(key)
        if not p.exists():
            raise KeyError(f'no charter schools/{key}.toml (copy schools/TEMPLATE.toml; docs/ADDING-A-SCHOOL.md stage 0)')
        with open(p, 'rb') as f:
            _cache[key] = _toml.load(f)
    return _cache[key]


def keys():
    ks = [p.stem for p in DIR.glob('*.toml') if p.stem != 'TEMPLATE']
    return sorted(ks, key=lambda k: (get(k).get('order') or 999, k))


def released():
    return [k for k in keys() if get(k).get('status') == 'released']


def onboarding():
    return [k for k in keys() if get(k).get('status') == 'onboarding']


def field(cfg, dotted, default=None):
    x = cfg
    for part in dotted.split('.'):
        if not isinstance(x, dict) or part not in x:
            return default
        x = x[part]
    return x


def inst_ids(key):
    return list(get(key)['ids']['openalex'])


def inst(key):
    return inst_ids(key)[0]


def sweep_ids(key):
    return inst_ids(key) + list(get(key)['ids'].get('openalex_related') or [])


def aff(key):
    return get(key)['affiliation']['regex']


def aff_rx(key):
    return re.compile(aff(key), re.I)


def own_units(key):
    s = field(get(key), 'affiliation.own_units') or ''
    return re.compile(s, re.I) if s else None


def short_names():
    return {k: get(k)['short'] for k in keys()}


def full_names():
    return {k: get(k)['name'] for k in keys()}


def computing(key):
    """The departments listed_not_in_census.py treats as computing (None: every listed department)."""
    v = field(get(key), 'census.computing_departments')
    return set(v) if v else None


def dblp_sweep(key):
    return field(get(key), 'dblp.legacy_sweep') or None


def check(key):
    """Problems with one charter (empty list: the charter passes)."""
    out = []
    try:
        cfg = get(key)
    except Exception as e:  # noqa: BLE001 (a TOML syntax error is a finding)
        return [f'{key}: unreadable: {e}']
    for f in REQUIRED:
        v = field(cfg, f)
        if v in (None, '', []):
            out.append(f'{key}: missing {f}')
    if cfg.get('key') != key:
        out.append(f'{key}: key field {cfg.get("key")!r} differs from the file name')
    if cfg.get('status') not in ('onboarding', 'released'):
        out.append(f'{key}: status must be onboarding or released')
    for i in field(cfg, 'ids.openalex', []) + field(cfg, 'ids.openalex_related', []) + field(cfg, 'ids.openalex_excluded', []):
        if not re.fullmatch(r'I\d+', i):
            out.append(f'{key}: bad OpenAlex institution id {i!r}')
    if set(field(cfg, 'ids.openalex', [])) & set(field(cfg, 'ids.openalex_excluded', [])):
        out.append(f'{key}: an id is both included and excluded')
    try:
        rx = re.compile(field(cfg, 'affiliation.regex', ''), re.I)
        for s in field(cfg, 'affiliation.must_match', []):
            if not rx.search(s):
                out.append(f'{key}: affiliation regex misses must_match {s!r}')
        for s in field(cfg, 'affiliation.must_not_match', []):
            if rx.search(s):
                out.append(f'{key}: affiliation regex matches must_not_match {s!r}')
    except re.error as e:
        out.append(f'{key}: affiliation regex does not compile: {e}')
    if cfg.get('status') == 'onboarding':
        deps = cfg.get('departments') or []
        if not any(d.get('coverage') == 'full' for d in deps):
            out.append(f'{key}: no department with coverage = "full"')
        for d in deps:
            if d.get('coverage') not in ('full', 'affiliated'):
                out.append(f'{key}: department {d.get("code")} coverage must be full or affiliated')
            for s in d.get('listings') or []:
                if not s.get('slot') or not s.get('url'):
                    out.append(f'{key}: department {d.get("code")} has a listing slot without slot/url')
        if not cfg.get('hosts'):
            out.append(f'{key}: no [[hosts]] (stage 0 checks every host against robots.txt)')
        slots = [s['slot'] for d in deps for s in d.get('listings') or [] if s.get('slot')]
        if len(slots) != len(set(slots)):
            out.append(f'{key}: duplicate listing slot names')
    return out


def listing_slots(key):
    """The charter's listing slots in the listings pipeline's shape (listings/scripts/plan_fetch.py SLOTS)."""
    out = []
    for d in get(key).get('departments') or []:
        for s in d.get('listings') or []:
            opt = {}
            if s.get('prefix'):
                opt['prefix'] = True
            if s.get('match'):
                opt['match'] = s['match']
            spec = (s['url'], s.get('from') or '20160101', s.get('to') or '20261231') + ((opt,) if opt else ())
            out.append(dict(dept=d['code'], slot=s['slot'], kind=s.get('kind') or 'main', urls=[spec]))
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == '--check':
        ks = a[1:] or keys()
        probs = [p for k in ks for p in check(k)]
        print('\n'.join(probs) if probs else f'ok: {len(ks)} charters ({", ".join(ks)})')
        sys.exit(1 if probs else 0)
    cfg = get(a[0])
    print(json.dumps(field(cfg, a[1]) if len(a) > 1 else cfg, indent=1, ensure_ascii=False))
