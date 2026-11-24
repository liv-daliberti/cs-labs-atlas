"""Build PREFLIGHT: every input a school's build cannot do without, checked BEFORE the build starts. A missing input, or a stub one,
makes the build refuse with a message that names the file, instead of failing late or silently dropping lab papers (Tsinghua 7,901 ->
2,203 lab papers when a 120-byte stub census-faculty.json stood in for the census). The table comes from the inputs the build opened per
school in the build-verification runs (scratch/verify-build-1113: inputs-<school>-vb-1113.tsv, hookrun.py audit hook); optional caches
(pi-works.sqlite, reviewed files with defaults) are not listed because their absence is a legal, counted state."""
from pathlib import Path

import atlas_paths as P

MIN_BYTES = {'census-faculty.json': 300, 'collection.json.gz': 300, 'openalex-sweep.sqlite': 4096}   # smaller than this is a stub, not the input (the smallest real census file is 466 bytes in a test fixture, 39 kB in production)
ADDITIONS_MIN = 1000   # a school whose faculty all sit in reviewed census-additions.json (SJTU) legitimately has an empty census-faculty.json (153 bytes)
ALL_SCHOOLS = ('census-faculty.json',)
REQUIRED = {   # data name -> schools whose build opens it (an absent school key means "not required for that school")
    'census-faculty.json': None,   # every school
    'openalex-sweep.sqlite': {'berkeley', 'cmu', 'hkust', 'mit', 'ntu', 'princeton', 'stanford', 'zju'},
    'collection.json.gz': {'berkeley', 'hkust', 'ntu', 'stanford', 'zju'},
}


class MissingInput(RuntimeError):
    pass


def required_for(school):
    return [name for name, schools in REQUIRED.items() if schools is None or school in schools]


def _additions_hold_the_census(school, root):
    path = Path(P.data('census-additions.json', school, root=root)) if root is not None else Path(P.data('census-additions.json', school))
    return path.exists() and path.stat().st_size >= ADDITIONS_MIN


def problems(school, root=None):
    """[(path, why)] for every required input of the school that is missing or a stub."""
    out = []
    for name in required_for(school):
        path = Path(P.data(name, school, root=root)) if root is not None else Path(P.data(name, school))
        if not path.exists():
            out.append((str(path), 'missing'))
        elif path.stat().st_size < MIN_BYTES.get(name, 1):
            if name == 'census-faculty.json' and _additions_hold_the_census(school, root):
                continue
            out.append((str(path), f'a stub: {path.stat().st_size} bytes, the input is at least {MIN_BYTES[name]}'))
    return out


def check(school, root=None):
    """Raise MissingInput naming every missing / stub input; otherwise return."""
    bad = problems(school, root)
    if bad:
        raise MissingInput(f'build preflight for {school}: refusing to run, required input(s) not usable: ' + '; '.join(f'{p} ({why})' for p, why in bad))
