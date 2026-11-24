"""Persist independently approved home-only reviews and export their exact views."""
import importlib.util
import json
import shutil

import atlas_paths as P
import evidence_store as E

from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]


def main():
    spec = importlib.util.spec_from_file_location('final_home_application', HERE / 'apply.py')
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    decisions = app.verify_reviews()
    stores = [s for s in decisions if E.source_of(s) == 'store']
    before = E.backup(stores)
    changes = []
    for school in stores:
        part = 'cmu' if school == 'cmu' else 'joint'
        review = app.read(HERE / f'{part}-independent-review.json')
        for name, entry in decisions[school].items():
            old = E.find(school, 'home-department-decisions.json', key=name)
            assert len(old) <= 1
            if old and old[0][5] == entry:
                changes.append(dict(school=school, name=name, evidence_id=old[0][0], unchanged=True))
                continue
            ident = E.record(school, 'home-department-decisions.json', entry,
                             source=entry['home_department_evidence'][0]['url'],
                             decided_by='codex-homes-finish-1123', reviewed_by=review['reviewer'],
                             supersede=old[0][0] if old else None, entry_key=None if old else name,
                             note='D-0048/R-HOME-02; exact source-reviewed final homes, home fields only')
            changes.append(dict(school=school, name=name, evidence_id=ident,
                                superseded=old[0][0] if old else None,
                                prior_record_sha256=app.digest(old[0][5]) if old else None,
                                record_sha256=app.digest(entry)))
        output = P.SCRATCH / 'homes-finish-1123/store-export'
        E.sync(school, root=output)
        relative = P.data('home-department-decisions-school.json', school).relative_to(P.CODE)
        source = output / relative
        assert all(app.read(source).get(name) == entry for name, entry in decisions[school].items())
        target = CODE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for school, entries in decisions.items():
        if school in stores:
            continue
        relative = P.data('home-department-decisions-school.json', school).relative_to(P.CODE)
        source = P.CODE / relative
        original = source.read_text() if source.exists() else '{}\n'
        view = json.loads(original)
        preserved = {name: app.digest(value) for name, value in view.items() if name not in entries}
        view.update(entries)
        assert all(app.digest(view[name]) == sha for name, sha in preserved.items())
        target = CODE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(view, ensure_ascii='\\u' in original, indent=1) + '\n')
    after = E.backup(stores)
    app.write(HERE / 'store-receipts.json', dict(stores=stores, recorded=changes,
                                               backups_before=before, backups_after=after))
    print(json.dumps(dict(store_records=len(changes), schools=len(decisions), records=sum(map(len, decisions.values())))))


if __name__ == '__main__':
    main()
