"""Pinyin of Han names from the vendored pypinyin 0.55.0 (vendor/pypinyin_0_55_0, MIT; owner ruling 2026-11-12: a signal that a page names a Han-keyed PI, never
identity binding). Loaded by file location, so there is no sys.path edit and nothing is installed (tests/test_imports_and_sys_path)."""
import importlib.util
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / 'vendor' / 'pypinyin_0_55_0' / 'pypinyin'
_mod = None


def _load():
    global _mod
    if _mod is None:
        if 'pypinyin' in sys.modules:   # an installed copy would be the same code; use whatever is already imported
            _mod = sys.modules['pypinyin']
        else:
            spec = importlib.util.spec_from_file_location('pypinyin', PKG / '__init__.py', submodule_search_locations=[str(PKG)])
            _mod = importlib.util.module_from_spec(spec)
            sys.modules['pypinyin'] = _mod
            try:
                spec.loader.exec_module(_mod)
            except Exception:
                sys.modules.pop('pypinyin', None)
                raise
    return _mod


def syllables(han):
    """Lower-case toneless pinyin syllables of a Han string (non-Han characters dropped)."""
    return [s.lower() for s in _load().lazy_pinyin(''.join(han.split())) if s.isalpha()]
