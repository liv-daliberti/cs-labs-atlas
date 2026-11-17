# Toronto student coverage: below 25 missing PIs

## Result

The completed private Toronto hierarchy build has student records for **193 of 217 PIs**; **24 PIs remain without student records**. The prior checkpoint had 49 missing, so the count fell by 25. The work added **74 reviewed student records across 25 PI groups**.

## New source-reviewed PI groups

| PI | Records added | Source |
|---|---:|---|
| Alan Moses | 7 | [Grad. students and postdocs](https://moses.csb.utoronto.ca/people/) |
| Berj L. Bardakjian | 1 | [Purple Day: Meet U of T students researching new ways to understand epilepsy](https://www.utoronto.ca/news/purple-day-meet-u-t-students-researching-new-ways-understand-epilepsy) |
| Blair Armstrong | 4 | [PhD & Master Students](https://www.utsc.utoronto.ca/labs/caplab/personnel/) |
| Dionne M. Aleman | 9 | [Graduate Students](https://morlab.netlify.app/people/) |
| Faith Ellen | 1 | [source page](https://www.cs.toronto.edu/~guan/) |
| Fritz Roth | 1 | [source page](https://www.varianteffect.org/person/adrine-de-souza/) |
| Greg A. Jamieson | 1 | [Cognitive Engineering Laboratory](https://news.engineering.utoronto.ca/u-of-t-engineering-student-integrates-indigenous-perspectives-into-the-operation-of-small-modular-nuclear-reactors/) |
| Hannes Rӧst | 1 | [Graduate student Shubham Gupta receives Dorrington Award](https://www.utoronto.ca/celebrates/graduate-student-shubham-gupta-receives-dorrington-award) |
| Henry Yuen | 1 | [source page](https://www.cs.utoronto.ca/~ashe/) |
| Hugh H. T. Liu | 12 | [current FSC members](https://flight.utias.utoronto.ca/index.php/team) |
| Jamie Stafford | 1 | [source page](https://noahripstein.com/) |
| Jessica Burgner-Kahrs | 8 | [Graduate Students](https://crl.utm.utoronto.ca/team/) |
| Lueder Kahrs | 1 | [Graduate Students](https://crl.utm.utoronto.ca/team/) |
| Mark Chignell | 1 | [author biography](https://www.alvinychin.com/_files/ugd/3bb735_bddfd8f7ab13db4fb7ee4dcec8d721c4.pdf) |
| Masayuki Yano | 5 | [PhD Students](https://www.utias.utoronto.ca/ace/ace-people/) |
| Nathan Wiebe | 1 | [EDUCATION](https://abhinavmuraleedharan.com/data/Abhinav_Muraleedharan_CV_Sep.pdf) |
| Nick Koudas | 1 | [2011 University of Toronto Inventors of the Year](https://utsc.utoronto.ca/news-events/archived/professor-and-phd-student-named-inventors-year) |
| Philip Kim | 1 | [Kim lab](https://www.utoronto.ca/news/researchers-use-generative-ai-design-novel-proteins) |
| Prasanth B. Nair | 1 | [source page](https://www.ilersich.com/pdfs/andrew_f_ilersich_cv.pdf) |
| Rhonda N. McEwen | 1 | [source page](https://www.utoronto.ca/news/seven-u-t-students-receive-inaugural-inlight-research-fellowships-support-mental-health) |
| Silvana M. Pesenti | 4 | [PhD students](https://pesenti.utstat.utoronto.ca/?page_id=101) |
| Suzanne Stevenson | 2 | [Students](https://www.cs.toronto.edu/~suzanne/students.html) |
| Vahid Sarhangian | 6 | [Current Graduate Students](https://sarhangian.mie.utoronto.ca/students/) |
| William Yu | 1 | [source page](https://jshaw-lab-compbio.github.io/team) |
| Zhaolei Zhang | 2 | [Lab Members](https://sites.utoronto.ca/zhanglab/people.html) |

## Evidence handling

Each new record carries a verbatim quote, extracted-text SHA-256, raw-source SHA-256, capture path, and the source-stated role. Co-advisers are recorded where the page names them. Suzanne Stevenson’s and Blair Armstrong’s rosters name students without assigning a degree to each person, so those rows retain the generic student role. Nick Koudas’s and Mark Chignell’s records are marked historical because their sources are dated 2011 and 2007.

## Remaining PIs without student records

- Anthony Bonner
- Anthony N. Sinclair
- Arvind Gupta
- Barend Beekhuizen
- Ben Rossman
- Carolina Nobre
- Elias B. Khalil
- Hau-Tieng Wu
- James K. Mills
- Javed Mostafa
- Jonathan Kelly
- Joseph Jay Williams
- Mariano P. Consens
- Michael Evans
- Moshe Gabel
- Paul Milgram
- Roy H. Kwon
- Salma Emara
- Stephen Brown
- Uma Girish
- Varinia Bernales
- Vassos Hadzilacos
- Wei Wang
- Yuchong Zhang

## Build and gate checks

`bin/atlas build toronto` completed in the private overlay at `hierarchy/toronto/tmp/overlay-under25`. The build reports 1,259 student records, 1,303 PI/student lab pairs, and 148 complete chains.

`bin/atlas validate toronto --reviewed` reports the edited `few-students-evidence` file as valid. It also reports 27 violations in the unchanged shared `student-identity-review` file and eight other reviewed files missing from the current tree. `bin/atlas evidence toronto` remains blocked by existing Toronto unavailability records (1,705 stale and 1,304 incomplete). This coverage result does not certify the full Stage 6/release gate.
