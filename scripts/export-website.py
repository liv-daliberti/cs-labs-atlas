#!/usr/bin/env python3
"""Export current website source for GitHub, without historical/provider scaffolding.

Creates a new directory. Does not copy Git history, data, credentials or receipts;
does not commit, push or deploy. Regenerate from the maintainer checkout after edits.
"""
import argparse
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = '''release.py release_inputs.py publication_io.py verify_publication.py upload-atlas.py
bundle-site.py test-bundle.py export-website.py build-cs-hierarchy.py build-cs-scope.py cs_scope.py
import-reader-release.py source-atlas-assets.mjs prepare-atlas.mjs test-release.py
test-reader-release.py test-cs-hierarchy.py test-cs-scope.py test-cs-scope-app.cjs
test-site-pages.py test-cs-departments-page.mjs test-paper-reader.mjs
test-atlas-storage.mjs test-atlas-update-auth.mjs test-princeton-release.mjs
test-chunked-transport.mjs'''.split()


def export(output):
    if output.exists():
        raise ValueError('Destination already exists; export to a new directory')
    files = [ROOT / 'scripts' / name for name in SCRIPTS]
    files += [p for p in (ROOT / 'atlas').rglob('*') if p.is_file() and
              p.suffix in ('.html', '.js', '.css', '.LICENSE') and not p.relative_to(ROOT / 'atlas').parts[0] in ('papers', 'data', 'downloads')]
    files += [ROOT / 'lib' / name for name in ('atlas-storage.mjs', 'atlas-update-auth.mjs', 'chunked-graph.mjs',
                                             'princeton-release.mjs', 'atlas-release.json', 'atlas-bootstrap.json')]
    files += [p for p in (ROOT / 'portable').rglob('*') if p.is_file() and 'node_modules' not in p.parts]
    files += [ROOT / name for name in ('AGENTS.md', 'CLAUDE.md', '.prettierrc.json', '.dockerignore',
                                     'requirements-publishing.txt', 'deployment/asset-manifest.json')]
    for source in files:
        if source.is_symlink():
            raise ValueError('Source export refuses symlinks')
        destination = output / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    pin = json.loads((ROOT / 'deployment/release.json').read_text())
    safe_pin = {name: pin[name] for name in ('release', 'manifestSha256', 'researchCommit', 'origin')}
    (output / 'deployment/release.json').write_text(json.dumps(safe_pin, indent=2) + '\n')
    for source, name in [('portable/package.json', 'package.json'), ('portable/package-lock.json', 'package-lock.json'),
                         ('portable/README.md', 'README.md'), ('portable/README.md', 'docs/PUBLISHING.md'),
                         ('portable/ci.yml', '.github/workflows/website.yml')]:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, destination)
    (output / '.gitignore').write_text('node_modules/\n.env\n.env.*\n!.env.example\n__pycache__/\noutputs/\ndist/\n'
                                     'atlas/data/\natlas/downloads/\natlas/data.json\natlas/papers/\natlas-source/\natlas-storage/\n')
    print(json.dumps({'directory': str(output), 'files': len(list(output.rglob('*'))), 'dataIncluded': False, 'published': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    export(args.output.resolve())
