"""Guarded entrypoint for future collector starts; vendored code stays unchanged.

The existing wrapper still owns robots, redirects, pacing, identity, retries and
catalog locks. Reject an inadequate asset before its successful result is saved;
other candidates remain available. Running collector processes are untouched.
"""
import importlib.util, os, sys
from pathlib import Path
from urllib.parse import urlsplit


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HOLD_HOSTS = ('web.archive.org', 'archive.org')
HOLD_REASON = 'source_paused: web.archive.org is reserved for the project listing captures (WAYBACK_HOLD=1); asked again in a later pass'


def wayback_held(url, environ=os.environ):
    """WAYBACK_HOLD=1 (the default in the loop scripts, 2026-11-10): the download loops do not ask web.archive.org / archive.org at all. The 429 cooldown of
    2026-11-10 04:59Z that stopped the NTU / Tsinghua / ZJU / Harvard capture jobs was drawn by loop collectors (michigan, gatech, epfl) fetching Wayback
    snapshot candidates already in their catalogs; trimming the wayback_acm channel does not stop those. The attempt is recorded as 'source_paused:' so
    the pass-start requeue asks again once WAYBACK_HOLD is 0."""
    return environ.get('WAYBACK_HOLD') == '1' and (urlsplit(str(url)).hostname or '') in HOLD_HOSTS


def install(wrapper, quality):
    """Only byte eligibility changes; the original client's policy checks run first."""
    client = wrapper.c.PublicClient
    original_get = client.get
    original_validate = wrapper.c.base.validate_pdf

    def get(self, *args, **kwargs):
        if args and wayback_held(args[0]):
            raise RuntimeError(HOLD_REASON)
        data, final, content_type = original_get(self, *args, **kwargs)
        if urlsplit(final).path.lower().endswith('.xml'):
            result = quality.xml_quality(data)
            if not result['ok']:
                raise ValueError('copy_quality: ' + result['reason'])
        return data, final, content_type

    def validate_pdf(data, path):
        pages = original_validate(data, path)
        result = quality.file_quality(path, 'pdf')
        if not result['ok']:
            raise ValueError('copy_quality: ' + result['reason'])
        return pages

    client.get = get
    wrapper.c.base.validate_pdf = validate_pdf


def main():
    # Explicit trusted code paths retain python -I without adding import paths.
    tools = Path(os.environ.get('CS_ATLAS_TOOLS', Path(__file__).resolve().parents[1] / 'tools'))
    paths = _load('atlas_paths', tools / 'atlas_paths.py')
    quality = _load('copy_quality', paths.TOOLS / 'copy_quality.py')
    wrapper = _load('collector_wrapper', paths.vendor('cmu_tools') / 'collector_wrapper.py')
    install(wrapper, quality)
    out = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else None
    if out:
        import store_layout
        store_layout.ensure(out)
        wrapper.requeue(out)
    wrapper.c.main()


if __name__ == '__main__':
    main()
