"""Reviewed census overrides of one school: the shared tracked file or, for a school being onboarded, its own file.

hierarchy/reviewed/census-overrides.json is TRACKED and shared by the released schools; only their reviews edit it. A school in onboarding
(charter status) keeps its section in hierarchy/<key>/reviewed/census-overrides-school.json instead ({person: entry}, committed on the
school's branch), so a stage tool never dirties a tracked file of the main checkout while a release is frozen (UChicago PROTOCOL-FRICTION 31).
Readers call section(key); writers call open_section(key) and save(). An onboarding school's reviewed identity bindings
(identity-bindings-school.json) are overlaid by section(), see bind(). Sourced home
decisions live separately in home-department-decisions.json; this final layer may
change only home fields, preserving identity, eligibility and period reviews.
"""
import json

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402


def onboarding(key):
    try:
        return S.get(key).get('status') == 'onboarding'
    except KeyError:
        return False


def _read(p):
    return json.loads(p.read_text()) if p.exists() else {}


HOME_FIELDS = {'home_department', 'home_department_evidence', 'why_home_department',
               'primary_stated', 'primary_unresolved', 'also_home_departments', 'no_academic_department'}


def section(key, resolve=None):
    """{person: override entry} of the school: the shared file's section, overlaid per person by the school-local file.
    `resolve(name, school)` finds the data file (default atlas_paths.data; a build root or release passes its own)."""
    resolve = resolve or P.data
    sec = dict(_read(resolve('census-overrides.json')).get(key) or {})
    for name, v in _read(resolve('census-overrides-school.json', key)).items():
        sec[name] = {**(sec.get(name) or {}), **v}
    for name, v in _read(resolve('identity-bindings-school.json', key)).items():
        sec[name] = bind(sec.get(name) or {}, v)
    for name, v in _read(resolve('home-department-decisions-school.json', key)).items():
        if not isinstance(v, dict) or set(v) - HOME_FIELDS:
            raise ValueError(f'{key}/{name}: home-department decisions may contain only home fields')
        sec[name] = {**(sec.get(name) or {}), **v}
    return sec


def bind(base, binding):
    """A reviewed identity binding (hierarchy/<key>/reviewed/identity-bindings-school.json, {person: entry}) supersedes the person's
    no_identity hold: the hold keys are dropped (the old reason is kept as `superseded_hold`), the binding's keys win. The file is
    separate from census-overrides-school.json so an identity review never edits a file another worker owns (2026-11-10, Tsinghua)."""
    out = {k: v for k, v in base.items() if k not in ('no_identity', 'why_no_identity')}
    if base.get('no_identity'):
        out['superseded_hold'] = base.get('why_no_identity')
    out.update(binding)
    out['no_identity'] = False
    return out


def open_section(key):
    """(section dict to edit in place, save()). An onboarding school edits and saves its own file; any other school the shared
    file, with the formatting it had (escape style, final newline)."""
    if onboarding(key):
        f = P.data_w('census-overrides-school.json', key)
        sec = _read(f)
        return sec, lambda: f.write_text(json.dumps(sec, indent=1, ensure_ascii=False) + '\n')
    f = P.data('census-overrides.json')
    txt = f.read_text()
    ov = json.loads(txt)
    sec = ov.setdefault(key, {})
    return sec, lambda: f.write_text(json.dumps(ov, indent=1, ensure_ascii='\\u' in txt) + ('\n' if txt.endswith('\n') else ''))
