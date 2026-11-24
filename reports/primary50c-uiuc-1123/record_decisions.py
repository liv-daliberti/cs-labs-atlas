"""Record independently approved home-only decisions and export only their views."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import atlas_paths as P
import evidence_store as E

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location('batch_home_application', HERE / 'apply.py')
    application = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(application)
    application.verify_reviews()
    decisions = application.selection_map()
    stores = [school for school in decisions if E.source_of(school) == 'store']
    before = E.backup(stores)
    changes = []
    reviewer = read(HERE / 'independent-review.json')['reviewer']
    for school in stores:
        for name, entry in decisions[school].items():
            old = E.find(school, 'home-department-decisions.json', key=name)
            assert len(old) <= 1
            if old and old[0][5] == entry:
                changes.append(dict(school=school, name=name, evidence_id=old[0][0], unchanged=True))
                continue
            ident = E.record(school, 'home-department-decisions.json', entry,
                             source=entry['home_department_evidence'][0]['url'],
                             decided_by='codex-primary50c-uiuc-1123', reviewed_by=reviewer,
                             supersede=old[0][0] if old else None,
                             entry_key=None if old else name,
                             note='D-0048/R-HOME-02; independent50 af28ec3366f334ab1b00ae9b9b27f6706d7ef02d747f246a1ca97ed3631f27de; home fields only')
            changes.append(dict(school=school, name=name, evidence_id=ident,
                                superseded=old[0][0] if old else None,
                                prior_record_sha256=digest(old[0][5]) if old else None,
                                record_sha256=digest(entry)))
        output = P.SCRATCH / 'primary50c-uiuc-1123/store-export'
        E.sync(school, root=output)
        relative = P.data('home-department-decisions-school.json', school).relative_to(P.CODE)
        source = output / relative
        view = read(source)
        assert all(view.get(name) == entry for name, entry in decisions[school].items())
        target = CODE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for school, entries in decisions.items():
        if school in stores:
            continue
        relative = P.data('home-department-decisions-school.json', school).relative_to(P.CODE)
        target = CODE / relative
        original = target.read_text() if target.exists() else '{}\n'
        view = json.loads(original)
        previous = {name: digest(value) for name, value in view.items() if name not in entries}
        view.update(entries)
        assert all(digest(view[name]) == sha for name, sha in previous.items())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(view, ensure_ascii='\\u' in original, indent=1) + '\n')
    after = E.backup(stores)
    (HERE / 'store-receipts.json').write_text(json.dumps(
        dict(stores=stores, recorded=changes, backups_before=before, backups_after=after),
        ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(store_decisions=len(changes), json_decisions=sum(len(d) for s, d in decisions.items() if s not in stores))))


if __name__ == '__main__':
    main()
