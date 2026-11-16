"""Repeated publication entries still need an audit verdict for each source entry."""
import gzip
import json
import sqlite3

import labpage_audit as A
import labpage_recover as R


def test_duplicate_publication_gets_a_separate_auditable_verdict(tmp_path, monkeypatch):
    school = "sjtu"
    recovery = tmp_path / "recovery"
    data = recovery / "hierarchy" / school
    data.mkdir(parents=True)
    monkeypatch.setattr(R, "D", lambda name, school=None, write=False: data / name)
    monkeypatch.setattr(R, "known_venues", lambda school: set())
    monkeypatch.setattr(R, "sweep_pages", lambda path: iter(()))
    monkeypatch.setattr(R, "ARXIV_OAI", tmp_path / "empty_arxiv")
    monkeypatch.setattr(A, "recover_dir", lambda school: recovery)
    (data / "pis.json").write_text(json.dumps([dict(pi="Alice Smith", names=["Alice Smith"])]))
    title = "Reliable distributed inference with bounded communication"
    rows = [dict(pi="Alice Smith", title=title, quote=title, year=2020,
                 url="https://example.org/" + page, audit_key=page)
            for page in ("publications", "archive")]
    with gzip.open(data / "labpage-pubs.jsonl.gz", "wt") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    with gzip.open(data / "lab_papers.jsonl.gz", "wt"):
        pass
    result = R.run(school, dry=True)
    assert len(result["cands"]) == 1
    verdicts = A.recover_verdicts(school)
    assert set(verdicts) == {"publications", "archive"}
    assert verdicts["publications"][0] == "candidate"
    assert verdicts["archive"][:2] == ("junk", "duplicate_listing")
    assert A.paper_reason(*verdicts["archive"][:2], 2020, 2010) == "parse_artifact"
    with sqlite3.connect(data / "labpage-recover.sqlite") as conn:
        assert conn.execute("select count(*) from accepted").fetchone()[0] == 0
