# CS Labs Atlas

An open, evidence-backed dataset of computer-science research labs, 2016–2026:

1. **The CS PI-lab hierarchy** of five universities (Princeton, Carnegie Mellon, EPFL, MIT, UC Berkeley; Stanford is
   being built and will be added the same way): school → department → PI lab → lab papers + students → student papers.
   Every PI, every lab paper and every advising link carries the public source that supports it (URL, page hash,
   verbatim quote).
2. **The wider atlas** of 300 universities in 32 countries: 37,060 research units in all fields (9,545 in computer-science
   scope), their linked papers, their people, and the PI identities behind them.
3. **The code** that builds both, as it was run.

It is meant to be built on: the tables are plain gzip JSONL (plus CSVs for the main joins), every id is stable, and
`tests/verify_release.py` re-checks the whole release.

## Scope and rules

These are the owner's decisions; the full rules and the evidence model are in [docs/METHODS.md](docs/METHODS.md).

- **A PI lab is one faculty PI plus their advisees.** Every faculty member who is a PI gets exactly one own lab. Centres,
  institutes, initiatives, programs, projects and multi-PI groups are *collectives*, not labs; they are not counted as
  labs (they appear only as context on a PI's lab record).
- **A PI** is a faculty member of the school (2016–2026) with stated PhD advising in the window, or the head of their own
  lab/group, documented by a quoted public source.
- **A lab paper** is a paper where (a) the PI is on the byline **and that authorship lists the school** (OpenAlex
  institution lineage, the raw affiliation string, or the paper's own first page), (b) the authorship is **anchored to the
  PI's identity** (the PI's DBLP person page, ORCID, a reviewed OpenAlex author id, an author id anchored on such works,
  the PI's own publication list, or a stated advisee as co-author), and (c) it falls **inside a reviewed appointment
  period**, or in a calendar year for which a **dated department faculty listing** names the PI.
- **Scope** is all faculty doing CS-related work, in any department (CS-related = publishes in CS venues, i.e. has
  DBLP-indexed papers), not only the computing departments. Each PI is labelled `core_computing_department` or
  `cs_related_addition`.
- **Students** are the PI's stated advisees (thesis records, rosters, alumni pages, lab pages) and members of the PI's
  own unit, named as in those public sources, with role, years, advisor, source URL and quote. No e-mail addresses or
  other contact details are included.
- **Departments** are assigned exactly as the project's site assigns them (the site builder's `department()`): a
  reviewed home department where one is recorded, else the computing department that lists the PI.

## Coverage

<!-- coverage:start -->
| | Princeton | Carnegie Mellon | EPFL | MIT | UC Berkeley | Stanford |
|---|---|---|---|---|---|---|
| PI labs | 140 | 458 | 169 | 277 | 209 | 232 |
| … core computing departments | 97 | 343 | 111 | 167 | 134 | 145 |
| … CS-related, other departments | 43 | 115 | 58 | 110 | 75 | 87 |
| Home departments | 14 | 25 | 17 | 18 | 19 | 37 |
| Unique lab papers | 8,680 | 25,817 | 13,223 | 19,943 | 13,876 | 19,093 |
| Lab–paper rows (a paper can belong to several labs) | 9,469 | 31,359 | 13,992 | 22,306 | 16,366 | 21,853 |
| Median lab papers per PI | 41 | 52 | 59 | 60 | 50 | 65 |
| Students (unique people) | 3,093 | 7,737 | 3,682 | 7,115 | 3,874 | 2,803 |
| Lab–student pairs | 3,524 | 9,382 | 3,986 | 7,652 | 4,452 | 3,218 |
| Student–paper links | 7,620 | 29,341 | 15,037 | 20,976 | 16,775 | 18,537 |
| Labs with papers | 137 | 456 | 167 | 275 | 208 | 232 |
| Labs with students | 140 | 458 | 169 | 277 | 208 | 232 |
| Labs with papers, students and links | 132 | 445 | 162 | 267 | 196 | 225 |
| DBLP-published papers we hold | 83% | 82% | 88% | 88% | 84% | 87% |

Wider atlas: 300 universities, 37,060 units, 131,309 works, 130,192 unit–paper links, 23,404 unit–person rows,
<!-- coverage:end -->

"DBLP-published papers we hold" is the share of the PIs' own DBLP-listed, non-preprint papers in their appointment
years that the lab-paper set contains (the independent completeness reference). Per-school detail (departments,
papers per year, top venues, student roles, zero-paper labs and why) is in
[docs/SCHOOL-PROFILES.md](docs/SCHOOL-PROFILES.md).

## Layout

```
data/
  schools/
    profiles.json                 per-school coverage profile (the numbers above)
    student_audit.json            probable duplicate student records and missed student-paper links, for review
    <school>/
      pis.jsonl.gz                one row per PI lab
      papers.jsonl.gz             one row per unique lab paper, with every lab it belongs to and why
      students.jsonl.gz           one row per student, with every advising PI and the sources
      student_papers.jsonl.gz     one row per (PI, student, paper) link
      pis.csv  lab_papers.csv  lab_students.csv  student_papers.csv     flat joins, no Python needed
      zero_labs.json              labs with zero papers / zero students, with the diagnosis and reviewed verdict
      excluded_pis.json           census PIs excluded by review (no appointment in the window)
      scope_review.json.gz        the CS-related-scope review: every candidate, the decision and its evidence
      build_report.json           the build's own counters (the verification reference)
  atlas/
    universities.jsonl.gz  units.jsonl.gz  works.jsonl.gz  unit_papers.jsonl.gz
    unit_people.jsonl.gz  unit_person_papers.jsonl.gz  pi_identities.jsonl.gz
    metrics.json.gz  scope_rule.json  atlas_summary.json
docs/       SCHEMA.md (every file and field), METHODS.md (sources, rules, evidence, gaps), SCHOOL-PROFILES.md
code/       the build tools as run (see code/README.md)
tests/      verify_release.py
MANIFEST.json   every data and code file with its size, sha256 and row count, plus the export summary
```

Tables larger than ~45 MB compressed are split into `<table>/<university_id>.jsonl.gz` shards automatically; the loader
below handles both. (In this release no table needed splitting.)

## Loading the data

```python
import gzip, json
from pathlib import Path

def rows(path):
    """One table: <name>.jsonl.gz, or a directory <name>/ of shards."""
    p = Path(path)
    files = [p] if p.exists() else sorted(Path(str(p)[:-len('.jsonl.gz')]).glob('*.jsonl.gz'))
    for f in files:
        with gzip.open(f, 'rt', encoding='utf-8') as fh:
            for line in fh:
                yield json.loads(line)

school = 'data/schools/princeton'
pis = {p['pi_id']: p for p in rows(f'{school}/pis.jsonl.gz')}
papers = {x['paper_id']: x for x in rows(f'{school}/papers.jsonl.gz')}

# lab papers per department and year
from collections import Counter
per = Counter((pis[l['pi_id']]['department'], x['year']) for x in papers.values() for l in x['labs'])

# a PI's students and their papers in the lab
pi = 'princeton:jennifer-rexford'
students = [s for s in rows(f'{school}/students.jsonl.gz') if any(a['pi_id'] == pi for a in s['advisors'])]
links = [r for r in rows(f'{school}/student_papers.jsonl.gz') if r['pi_id'] == pi]
```

With pandas: `pd.read_json('data/schools/cmu/papers.jsonl.gz', lines=True)`, or `pd.read_csv('data/schools/cmu/lab_papers.csv')`.

## How it was built

Per school: a faculty census of the computing departments from dated department listings (live pages and Wayback
captures), extended to CS-related faculty in any department; reviewed appointment periods; PI status from advising
records; an OpenAlex sweep of every 2016–2026 work affiliated with the school; identity anchors from DBLP person pages,
ORCID, reviewed OpenAlex ids, the PIs' own and their labs' publication lists; recovery of DBLP-listed papers whose
affiliation only the paper's first page states; and students from thesis repositories, graduate rosters, alumni and lab
pages. Every quoted piece of evidence was checked as an exact substring of the captured page. The wider atlas comes from
the earlier 300-university inventory of research units (official directories, reviewed leadership, lab bibliographies).
The order of the steps and the tools are in [code/README.md](code/README.md); the rules in [docs/METHODS.md](docs/METHODS.md).

The data files are regenerated by `code/claude-schools-20261021/tools/export_release.py <repo dir>` (deterministic: sorted
rows, gzip without timestamps), which ends by running `tests/verify_release.py`.

## Limitations

- Coverage is high but not complete: against the PIs' own DBLP pages 82–88% of their published (non-preprint) papers in
  appointment years are held. The rest are mostly papers whose OpenAlex record lists no affiliation for the PI and has no
  readable first page, or papers outside the PI's documented appointment years.
- Appointment periods are reviewed but year-granular at the boundaries; a paper in a boundary year counts when a dated
  listing or period supports that year.
- Student lists come from public sources and are incomplete, especially for master's and undergraduate students and for
  years without archived rosters. Student–paper links with status `candidate` are name matches on a school-affiliated
  byline, not verified identities.
- A few labs have zero papers or zero students; each has a recorded reason in `zero_labs.json`.
- The wider atlas is an inventory with uneven depth: many units have no named leader, no papers or no people yet
  (`leadership_status`, `paper_counts`, `cs_hidden` say which). Its paper links come in three views (`strict`,
  `reviewed`, `combined`) whose rules differ from the five schools' lab-paper rule.
- Bibliographic metadata (titles, venues, bylines) is as OpenAlex/DBLP/the source recorded it.

## Personal data

Names of faculty and students appear as they do in public university sources (directories, thesis records, lab pages).
E-mail addresses, phone numbers and office addresses were removed from every quote, and personal homepage links of atlas
people were dropped. If you are listed and want a record corrected or removed, please open an issue.

## Citation

See [CITATION.cff](CITATION.cff).

## Licenses

- **Code** (`code/`, `tests/`): MIT, see [LICENSE](LICENSE). `code/claude-schools-20261021/hierarchy/nicknames/names.csv`
  is the public carltonnorthern/nicknames table (Apache-2.0), kept with its own license terms.
- **Data** (`data/`, `docs/`): Creative Commons Attribution 4.0 International (CC BY 4.0), see
  [data/LICENSE.md](data/LICENSE.md).
- Bibliographic metadata from **OpenAlex** and **DBLP** is CC0; it is redistributed here under their terms.
- **Quoted evidence snippets** (the `quote` fields) are short verbatim excerpts of public web pages, kept only so that each
  claim can be verified against its source. They remain the property of their publishers and are not relicensed.
