"""The layout a store needs before a collector runs (2026-10-31). Michigan's store was created without sources/,
staged/ and by_lab/; the collector writes each host's robots.txt to sources/ before its first request there, so every
attempt failed as worker_error (ENOENT) and 1,952 (work, URL) pairs were marked tried. The loop and the collector
wrapper call ensure() before anything else: it creates what is missing, or refuses to start (StoreLayoutError) when the
store itself is not usable. docs/STORES.md lists the layout."""
import json
from pathlib import Path

DIRS = ('objects', 'sources', 'staged', 'by_lab', 'discovery', 'quarantine')
FILES = {'summary.json': '{}\n'}


class StoreLayoutError(RuntimeError):
    pass


def ensure(store, create=True):
    """-> list of what was created. Refuses when the store or its catalog is missing, or a path is not a directory."""
    store = Path(store)
    if not (store / 'catalog.sqlite').is_file():
        raise StoreLayoutError(f'{store}: no catalog.sqlite')
    made = []
    for d in DIRS:
        p = store / d
        if p.exists() and not p.is_dir():
            raise StoreLayoutError(f'{p} exists and is not a directory')
        if not p.exists():
            if not create:
                raise StoreLayoutError(f'{p} is missing')
            p.mkdir(parents=True); made.append(d + '/')
    for f, content in FILES.items():
        p = store / f
        if not p.exists():
            if not create:
                raise StoreLayoutError(f'{p} is missing')
            p.write_text(content); made.append(f)
        else:
            try:
                json.loads(p.read_text() or '{}')
            except ValueError:
                raise StoreLayoutError(f'{p} is not JSON') from None
    return made
