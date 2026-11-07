# Targeted student evidence discovery

`tools/labpage_students_school.py sources` supplements the existing lab-page, thesis,
student-homepage, and roster pipelines. It writes **unreviewed proposals only**. An
empty lab or a lab with a few students is a search priority, never evidence of completeness.

```sh
$CS_ATLAS_PY -I tools/labpage_students_school.py sources gatech \
  --seeds /path/to/seeds.json --out /path/to/proposals --max-fetches 100
```

A seed file is a JSON list of `{ "url": "https://...", "kind": "..." }` objects.
Kinds: `defense_index`, `defense`, `lab_people`, and `gatsby_team`. Known pilot sources:

- Georgia Tech ECE: `https://ece.gatech.edu/taxonomy/term/16445`. Follow its explicit
  pagination and dated defense links. Other committee members are not advisers.
- HPArch: `https://sites.gatech.edu/hparch/people/`. Review students by section and
  alumni by stated year; exclude out-of-window alumni and do not infer missing dates.
- UChicago Knowledge Lab: `https://knowledgelab.org/team` renders affiliated faculty
  initially; its public `/page-data/team/page-data.json` contains the student and alumni
  tabs. The team component consumes `contentfulKLabPage.kLabContents`. Read category
  and biography together: visitors, students at other universities, and people supervised
  by other researchers must not become the director's doctoral advisees automatically.

Run with `--offline` to reparse the saved captures. Reruns reuse cached pages and spend
the fetch budget only on unseen URLs. `--hierarchy` selects the built package used to
resolve adviser names. Outputs contain URL, capture hash, timestamp, result, pending
sources, and review proposals. Contact fields from roster data are not exported.

Network work uses `school_web` and its robots/AI-agent rules, crawl delays, hashed
storage, and challenge handling. The collector stops new requests to a host after a
403, 429, or challenge. It never calls Wayback. Submit larger runs through
`tools/student-sources.slurm` with `SCHOOL`, `SEEDS`, `SOURCE_OUT`, optionally
`SOURCE_HIERARCHY` and `MAX_FETCHES`; test the submission first and pin the commit.

Review proposals against existing students, the source bytes, the PI's appointment,
the student's degree/visitor status, and the 2016–2026 window before copying evidence
into the school's reviewed inputs. A dated defense announcement supports a PhD student
relationship, not proof that a degree was conferred. Future announcements remain held.
For tabbed rosters, follow a person's own page or another explicit source to establish
individual advising when the roster is shared. Rebuild in an overlay and check student
and paper-link changes before landing reviewed data.
