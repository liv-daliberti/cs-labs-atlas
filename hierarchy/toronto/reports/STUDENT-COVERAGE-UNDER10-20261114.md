# Toronto Stage 6: student coverage follow-up

## Current result

The latest private rebuild contains **216 PIs**. **215 have student records** and **one has none** (Uma Girish). This closes seven of the eight previously empty labs and puts Toronto below the requested threshold of 10. The zero-record share is **0.5%**. The one remaining zero is researched: the PI page says she is recruiting but names no students, and the reviewed evidence records the sources checked. No student was inferred or invented to force the count to zero.

The build contains **1,583 distinct student records** and **1,668 PI–student pairs**. The previous build had 1,651 pairs; this pass added 17 PI–student links after reviewing more current rosters. New source-backed evidence covers Fan Long, Andreas Veneris, Ben Rossman, and Farid N. Najm, in addition to the roster work recorded earlier in this pass. Raw source pages are preserved under `raw/student-coverage-stage6-20261114/`.

## Stage 6 status

**Stage 6 remains open.** A fresh 30-PI stratified recall draw (seed `20261126`) is saved at `reviewed/student-recall-check.json` and bound to the latest `pis.json` and `students.json`. The capture store is at `work/student-recall-captures.sqlite`. The sample has not yet been transcribed: all 30 entries still need readable/unverifiable verdicts, page references, and (for readable pages) roster names. The record then needs a checker name and signoff from a fresh independent reviewer. Do not sign the record as its drawer or filler.

The latest Stage 6 gate reports the zero-reason metric passing (**0 unreasoned zero-record PIs**). It remains open on the unfilled recall record and whole-school current-PhD recall estimate, which cannot be computed until readable sample entries are filled. The broader chain gate also reports **23 PIs missing lab-paper coverage, 103 missing student coverage, and 84 missing student-paper-link coverage**; those are separate repair queues.

## Recent coverage repairs

- Fan Long’s current team page added eight missing members (PhD, MSc, and undergraduate) alongside the previously recorded co-supervised student.
- Andreas Veneris’s current roster and Ben Rossman’s current roster added members absent from the build.
- An upcoming 2026 ECE oral-exam listing explicitly names Mahdi Harb with Farid N. Najm as supervisor.
- The latest rebuild increased PI–student pairs from 1,651 to 1,668 and distinct student records from 1,573 to 1,583.

## Next steps

1. Transcribe and classify the 30 sampled PIs using the captured pages; include only dated names or names in an explicit current-members section.
2. Repair any missing relationships discovered by that sample. Any rebuild after the draw invalidates the sample and requires a fresh draw.
3. Have a different reviewer verify the filled sample and sign it, then rerun `student_recall.py check toronto` and `bin/atlas stage-gate toronto 6`.
4. Work the separate chain-coverage gaps for lab papers, students, and student-paper links.
