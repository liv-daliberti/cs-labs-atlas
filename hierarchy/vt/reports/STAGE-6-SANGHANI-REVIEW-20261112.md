# Virginia Tech Sanghani student–adviser review — 2026-11-12

This is a bounded Stage 6 source review, not Stage 6 acceptance. The input is
`reviewed/sanghani-visible-student-advisers.json`: 16 captured Virginia Tech
Sanghani student profiles fetched on 2026-11-10. Each stored profile's SHA-256
matches the capture in the school's web cache, and each quoted role and adviser
sentence appears in the captured page after whitespace normalization.

Nine named students have ten explicit adviser relations to nine supported VT
PIs whose faculty census includes 2026. Those relations are recorded in
`reviewed/few-students-evidence.json` with the captured profile URL, SHA-256,
verbatim quote, role, and 2026 observation year. Ayush Roy has two separately
source-stated advisers, Doug Bowman and Chris North. Amartya Dutta's relation
to T. M. Murali is included; the same source also names Anuj Karpatne, whose
2026 VT appointment remains unresolved in the current census.

Seven profile leads remain held:

| Student | Source-stated adviser | Reason for hold |
| --- | --- | --- |
| Abhilash Neog | Anuj Karpatne | 2026 VT appointment not established in the current census |
| Alexander Kedrowitsch | Danfeng (Daphne) Yao | 2026 VT appointment not established in the current census |
| Aravind Cheruvu | Danfeng (Daphne) Yao | 2026 VT appointment not established in the current census |
| Ahmad Al-Tawaha | Ming Jin | No supported VT PI record in the current census |
| Bilgehan Sel | Ming Jin | No supported VT PI record in the current census |
| Ann Mariya Sunil | Manish Bansal | No supported VT PI record in the current census |
| Bhargav Vasireddy | Sara Hooshangi | Faculty record is not a supported PI role |

These holds are source and appointment questions, not negative judgments about
the students. An isolated build at the same code commit (`b38fe480`) admitted
9 student records and 10 lab–student pairs, with 13 candidate student–paper
links. It produced 706 lab-paper rows versus 555 in the main baseline trial;
the paper difference needs Stage 7 scientific review and is **not** an
admitted school count. The school-local student audit must be rerun after this
review lands. Lab-page discovery, the hand-check sample, and the remaining
student-empty labs remain open; no Stage 6 or full-package gate is claimed.
