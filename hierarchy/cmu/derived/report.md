# CMU School of Computer Science faculty census, 2016–2026

Step 0 of the four-school build: every person the CMU sweep files as faculty, checked against dated department listings, with a rank and a PI decision. Built by `tools/build_cmu_census.py`; this report by `tools/build_cmu_report.py`.

- `cmu-faculty.json`: one record per person, with sources, verbatim quotes, rank, rank_by_year, PI basis, lab units and notes.
- `cmu-listing-only.json`: names on the department listings that the structure lacks.
- `captures-cmu.sqlite`: the yearly Wayback captures this census added (MLD core, affiliated and adjunct; CSD faculty directory; SCS directory), from `tools/fetch_listings.py`.

**967 people** carry the faculty role in the sweep's `structure.json`. They are backed by 7,702 sources, each with a verbatim quote. **364 are PIs.** 618 held a core SCS appointment at some point in the period, 165 appear only on affiliated / adjunct listings, and 184 appear on no department listing.

## Counts by rank and department

Rank is taken from the latest dated title. A person listed in more than one department is counted in each, so the department columns sum to more than the total. `rank_by_year` in the JSON keeps the earlier ranks: for example, faculty who left and now hold an adjunct title were ladder faculty earlier in the period.

| rank | people | CSD | RI | HCII | S3D | MLD | LTI | CBD | PIs |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| ladder | 306 | 126 | 67 | 60 | 56 | 65 | 52 | 29 | 248 |
| research | 112 | 16 | 56 | 12 | 7 | 8 | 28 | 7 | 47 |
| teaching | 67 | 33 | 3 | 12 | 18 | 2 | 2 | 5 | 3 |
| adjunct_courtesy | 228 | 41 | 54 | 83 | 25 | 22 | 7 | 11 | 40 |
| visiting | 48 | 28 | 0 | 2 | 5 | 1 | 2 | 10 | 1 |
| emeritus | 31 | 17 | 11 | 8 | 5 | 5 | 3 | 1 | 19 |
| not_faculty | 97 | 51 | 6 | 26 | 5 | 1 | 1 | 11 | 0 |
| unknown | 78 | 11 | 14 | 4 | 12 | 27 | 6 | 4 | 6 |
| **all** | 967 | 323 | 211 | 207 | 133 | 131 | 101 | 78 | 364 |

## PIs

A PI leads a research group. The basis is recorded in order of strength, with the quote and URL in `pi_basis`:

- **named_lab** (34): the person is the named leader of a non-umbrella lab (no center, institute, program or research area in the name; at most three leaders), quoted from the lab's own page.
- **own_group** (54): the person alone leads a collection research unit, or their homepage or group page lists students under a heading ('Current PhD Students', 'Lab Members').
- **advises_phd** (276): a PhD student or alumnus names the person as adviser, thesis chair or supervisor on a captured page.

Adjunct and courtesy faculty count as PIs only when the group is at CMU. Advising alone does not make an external adjunct a PI unless they held a core SCS appointment in the period. Faculty who left CMU but led groups here in 2016–2026 stay PIs; their latest rank is shown.

PIs by latest rank: ladder 248, research 47, teaching 3, adjunct_courtesy 40, visiting 1, emeritus 19, unknown 6.

**58 ladder-rank people have no PI evidence.** For 8 of them the sweep records advisees, but no captured page states the advising. The rest have no recorded advisees and no lab or group page. Three kinds of record land here. Some are faculty of other colleges carried on SCS lists, whose titles name Psychology, Statistics, Tepper or Philosophy. Some are SCS faculty whose students the sweep never captured (for example Philip Koopman, Danny Sleator and Raj Reddy). Some are duplicate records of a person whose other record is a PI (see the duplicates below). They are listed here so a reviewer can add a basis by hand:

Adam Paulisick, Alan Montgomery, Alexandra Ion (4 advisees), Ana Maria Sande do Vale Pinto da Silva, Andrew Moore, Andrew Spielberg (1 advisees), Ari Lightman, Brian Macwhinney, Christian Kaestner, Dan Saffer, Danny Sleator, David O'Hallaron, Ding Zhao, Douglas Sicker, Eni Halilaj, Eric H Nyberg III, Fernando Diaz (4 advisees), Frederike Duembgen, Gary K. Fedder, Ge Yang, Irene Kaplow, James Baker, Jean Yang, Jim Berardone, Jim McCann, Joel Mcmanus, John Vu, Josh Bloch, Justine Sherry Martins, Kathryn Roeder (1 advisees), Kiron Skinner, Lenore Blum, Madhavi Ganapathiraju, Malihe Alikhani, Matthias Grabmair, Michael Erdmann, Michael Ian Shamos, Olivia Weiya Hsu, Paul Pangaro, Philip Koopman, Rahul Panat, Raj Reddy, Richard M Stern Jr., Richard Scheines, Richard Stern, Roberta Klatzky, Sanjiv Singh (1 advisees), Sarah Bergbreiter (2 advisees), Sivaraman Balakrishnan (3 advisees), Steven Rudich, Subra Suresh, Tanja Schultz (1 advisees), Vickie Webster-Wood, Wolfgang Gatterbauer, Xu Wang, Yang Liu, Yong-chan Park, Yorie Nakahira

## People the structure has that no listing confirms

184 faculty-role people appear on no department faculty listing (core or affiliated):

| why | people |
|---|--:|
| latest titles are postdoc / student / TA titles | 66 |
| named on profile, thesis or lab pages, but on no department faculty listing | 54 |
| only the SCS-wide directory (lists staff, students and visitors too) | 45 |
| no source page names the person | 13 |
| not a person name (a title or unit string) | 6 |

- *no source page names the person* (13): Alex Waibel, Alfred Blumstein, Amir Barati Farimani, Andrea Zanette, Brian Junker, Isabella Verdinelli, Janelle Feather, Joel Greenhouse, Joel Welling, Maggie Henderson, Marcel Just, Ramayya Krishnan, Will Townes
- *not a person name (a title or unit string)* (6): Professor & Dean, Heinz College, Professor & Dept. Head (Statistics), Professor in Residence, Professor, Director CCBI, Project Leader - Informedia, Sr. Scientific Specialist
- *only the SCS-wide directory (lists staff, students and visitors too)* (45): Abhi Silwal, Alex Potanin, Alexander Nolte, Allan Schiffman, Amir Ivry Mark, Ana Maria Sande do Vale Pinto da Silva, Ari Lightman, Ashok Kumar Pradhan, Benjamin Titzer, Christian Kaestner, Deniz Gencaga, Eric H Nyberg III, Faryn Campbell, Hemantha Kumar Kalluri, James Joshi, Jeff Ichnowski, Jim McCann, Joshua Bloch, Kazuki Yano, Koustav Rudra, Kuang-Da Wang, Mahmood Sharif, Martim Cruz Silva Jales, Miguel Serra Carvalho, Mihovil Bartulovic, Moritz Sattlegger, Murali Krishna Enduri, Naveena Yanamala, Olivia Weiya Hsu, Pradyut Kumar Sanki, Praveen Garimella, Pravin Chandrakant Mote, Rebekka Wohlrab, Richard M Stern Jr., Rodrigo Farate Laia, Rouli Freeman, Steven Xia, Tse-Lun Wang, Vickie Webster-Wood, Xin Xu, Youcan Xu, Yugo Hayashi, Yuhao Li, Zhen-Yin Chen, Zitian Guo

Across the whole census, 97 people the structure files as faculty have postdoc, PhD-student or TA titles as their latest stated titles. Most are in CSD (51) and HCII (26); 23 are CSD postdocs whose profiles sit under CSD's `people/adjunct-faculty/` path. Their latest title and quote are in the JSON. They are kept in the census but marked `not_faculty: true`, and none is a PI.

Collection ids: 938 people match exactly one collection person by name. 16 match several collection records, which are duplicates to merge. 13 match none.

**Probable duplicate records in the structure (15 pairs).** Each pair is the same family name with a short form, nickname, transliteration or suffix variant. The census keeps both records as the structure has them; the PI flag can differ between the two, and they should be merged before any counts are used:

Abhi Silwal [not PI] / Abhisesh Silwal [not PI]; Alex Hauptmann [PI] / Alexander Hauptmann [PI]; Alex Waibel [PI] / Alexander Waibel [PI]; Ben Titzer [PI] / Benjamin Titzer [PI]; C. Joel McManus [PI] / Joel Mcmanus [not PI]; Chris Atkeson [PI] / Christopher Granger Atkeson [PI]; Christian Kaestner [not PI] / Christian Kästner [PI]; Chunqiu Steven Xia [not PI] / Steven Xia [PI]; Eric H Nyberg III [not PI] / Eric Nyberg [PI]; Jeff Ichnowski [PI] / Jeffrey Ichnowski [PI]; Josh Bloch [not PI] / Joshua Bloch [not PI]; Ken Holstein [PI] / Kenneth J Holstein [PI]; Matt Fredrikson [PI] / Matthew Fredrikson [PI]; Richard M Stern Jr. [not PI] / Richard Stern [not PI]; Yong-chan Park [not PI] / Yongchan Park [not PI]

## People the listings show that the structure lacks

19 names on the captured department listings match no structure person, after matching on full names, given-name short forms, nicknames and family name plus initial:

| name | rank | dept | years | title (verbatim) |
|---|--:|--:|--:|--:|
| Alex Smola | ladder | MLD | 2016–2017 | Professor |
| Carlos Guestrin | ladder | MLD | 2016–2017 | Professor of Computer Science & Engineering, University of Washington |
| Charles Kemp | ladder | MLD | 2016–2018 | Assistant Professor, Department of Psychology |
| Daniel Neill | ladder | MLD | 2016–2018 | Assistant Professor, Heinz College |
| Estevam Hruschka | ladder | MLD | 2016–2021 | Associate Professor, Computer Science, Federal University of Sao Carlos |
| Fernando De la Torre | research | MLD | 2019–2022 | Associate Research Professor, Robotics Institute, School of Computer Science |
| Gregory Kesden | adjunct_courtesy | CSD | 2016 | Affiliated Faculty |
| Haokang An | research | SCS | 2019 | Project Scientist |
| Henry Chai | teaching | MLD | 2023–2025 | Assistant Teaching Professor, Machine Learning, School of Computer Science |
| Justin Aglio | visiting | SCS | 2019–2020 | Visiting Learnlab Fellow |
| Kayhan Batmanghelich | ladder | MLD | 2017–2021 | Assistant Professor, Biomedical Informatics & Intelligent Systems, University of Pittsburg |
| Mads Andersen | visiting | SCS | 2016 | Visiting Researcher |
| Mary Amasia | teaching | SCS | 2016–2017 | Instructor - Portugal |
| Nina Balcan | ladder | CSD | 2016–2019 | Associate Professor |
| Ryan Tibshirani | adjunct_courtesy | MLD | 2016–2025 | Adjunct Faculty, Machine Learning, School of Computer Science |
| Ryuhei Mori | visiting | CSD | 2017 | Visiting Scholar` |
| Sandip Aine | research | SCS | 2020–2021 | Project Scientist |
| Stephen Fienberg | ladder | MLD | 2016 | University Professor |
| Victor Adamchik | teaching | CSD,SCS | 2016 | Associate Teaching Professor |

Most are MLD core or affiliated faculty whose last listing is early in the period (Smola, Guestrin and Fienberg in 2016–2017), or who are based in other colleges or universities (Kemp, Neill, Batmanghelich, Hruschka, Tibshirani). The others are CSD visitors and lecturers, and SCS-directory project scientists. 'Nina Balcan' on the 2016–2019 CSD directory is Maria-Florina Balcan, who is in the structure; that alias is not matched automatically.

## Units to create

**241 PIs lead no group-type unit in the collection.** Group-type means a department-, SCS- or research-listed lab, or a project-lab row, that is not an umbrella and has at most three leaders. Of these, 164 have only their per-adviser listing unit (`adviser_group_units`), which AGENTS.md keeps distinct from a lab. Each gets a proposed `<name> research group` in `lab_units`, carrying the PI basis as its evidence (206 advising, 35 own-group page). 123 PIs already have a group-type unit. 4 of the names below are duplicate pairs from the list above, so merging them leaves 237 units to create.

Aaditya Ramdas, Aaron M Johnson, Aarti Singh, Aayush Jain, Abhinav Gupta, Aditi Raghunathan, Adrien Treuille, Aisling Kelliher, Akari Asai, Akshitha Sriraman, Alan Black, Albert Gu, Alessandro Acquisti, Alex Hauptmann, Alex Waibel, Alexander Hauptmann, Alexander I Rudnicky, Alexander Waibel, Alon Lavie, Alonzo J Kelly, Ameet Talwalkar, Amy Elizabeth Ogan, Anatole Gershman, Andre Platzer, Andrea Zanette, Andreas Robert Pfenning, Andrej Risteski, Andrew Ilyas, Aniket D Kittur, Anind Dey, Ann Lee, Anthony Rowe, Anthony Stentz, Anupam Datta, Anupam Gupta, Ariel Procaccia, Aviral Kumar, Avrim Blum, Barnabas Poczos, Ben Titzer, Benjamin Titzer, Bernhard Haeupler, Bhiksha Raj, Bhiksha Raj Ramakrishnan, Brad A Myers, Brandon Lucia, Brett Browning, Bryan Wilder, Byron Yu, Carolyn P Rose, Chinmay Kulkarni, Chris Donahue, Christian Cuba Samaniego, Christian Kästner, Christina Harrington, Christopher Dyer, Christopher Granger Atkeson, Christopher J Langmead, Christopher Timperley, Cosma Shalizi, Dana Scott, Dannie Durand, Daphne Ippolito, David Andersen, David Brumley, David Wettergreen, David Woodruff, Deva Ramanan, Dimitrios S Apostolopoulos, Dimitrios Skarlatos, Edmund Clarke, Eduard Hovy, Elaine Shi, Emma Brunskill, Eric Nyberg, Eric Xing, Erik Harpstead, Farzaneh Derakhshan, Fei Fang, Feras Saad, Florian Metze, Frank Pfenning, Fraser Brown, Gabe Gomes, Garth Gibson, Gary Miller, Gauri Joshi, Geoff Kaufman, Geoffrey J Gordon, George Amvrosiadis, Giulia Fanti, Graham Neubig, Gregory Ganger, Guy Blelloch, Hanan Hibshi, Hirokazu Shirado, Hoda Heidari, Hui Zhang, Ioannis Gkioulekas, J. Andrew (Drew) Bagnell, Jaime Carbonell, James D Herbsleb, Jan Hoffmann, Jason Li, Jeff Ichnowski, Jennifer Mankoff, Jeremy Avigad, Jessica Hammer, Jessica Hodgins, Jodi L Forlizzi, Joern Dengjel, John C Stamper, John D Zimmerman, Jonathan Aldrich, Jonathan Francis, Joseph Anthony Calandrino, Joshua S Sunshine, Justine Cassell, Justine Sherry, Jürgen Pfeffer, Karl Crary, Katerina Fragkiadaki, Kathleen M Carley, Kayvon Fatahalian, Keenan Crane, Kenneth J Holstein, Larry A Wasserman, Lauren Herckis, Leila Wehbe, Leman Akoglu, Limin Jia, Luis von Ahn, Lujo Bauer, Maggie Henderson, Mahadev Satyanarayanan, Manuel Blum, Marcel Bruchez, Maria Balcan, Marijn Heule, Mary Shaw, Matt Fredrikson, Matthew Fredrikson, Matthew Mason, Matthew O'Toole, Matthew O’Toole, Max Simchowitz, Maxine Eskenazi, Mayank Goel, Michael Tarr, Min Xu, Minchen Li, Mona Diab, Mor Harchol-Balter, Motahhare Eslami, Natasa Miskov-Zivanov, Nathan Beckmann, Nathan Michael, Nicholas Boffi, Nicolas Christin, Nihar Shah, Nikol Elisabet Rummel, Nikolas Martelaro, Niloofar Mireshghallah, Norman M Sadeh, Nuno Nunes, Olexandr Isayev, Onur Mutlu, Patrick Park, Peter Steenkiste, Phillip Compeau, Phillip Gibbons, Pradeep Ravikumar, Pravesh Kothari, R. Ravi, Randal Bryant, Randi Williams, Rashmi Korlakai Vinayak, Ravi Starzl, Riad Wahby, Riccardo Paccagnella, Richard Peng, Richard Schuster Border, Rita Singh, Robert E Frederking, Robert E Kass, Robert E Kraut, Robert F Murphy, Robert Harper, Roger Dannenberg, Ronald Rosenfeld, Roni Rosenfeld, Roy Maxion, Ruben Martins, Ruslan Salakhutdinov, Russell Schwartz, Ryan O'Donnell, Sarah Cen, Sarah Scheffler, Sauvik Das, Scott E Hudson, Scott Fahlman, Seth Goldstein, Seyoung Kim, Srinivasan Seshan, Stefan Mitsch, Stelian Coros, Stephanie Balzer, Stephen Brookes, Steve James Rathje, Steven Dow, Steven Michael Chase, Steven Wu, Steven Xia, Tai-Sing Lee, Teruko Mitamura, Theophilus Benson, Tianqi Chen, Tim Dettmers, Todd Mowry, Tom Costello, Tom Mitchell, Umut Acar, Valentina Nisi, Venkatesan Guruswami, Vincent Aleven, Vincent Josua Hellendoorn, Vipul Goyal, Virginia Smith, Vyas Sekar, Wei Wu, Weina Wang, Wenting Zheng, William Kuszmaul, William L Scherlis, William Red L Whittaker, William W Cohen, Yuejie Chi, Yulia Tsvetkov, Zachary Chase Lipton, Zhihao Jia, Zico Kolter

## Gaps and limits

- Listings: RI, HCII and CBD are covered every year 2016–2026. LTI has no 2018 capture. ISR/S3D has none for 2016 or 2019. MLD core, affiliated and adjunct cover 2016–2025. CSD covers 2016, 2017 and 2019 (directory/faculty) and 2023–2026 (people/faculty). The SCS-wide directory captures hold only their first page (50 rows) for 2016–2021, and are script-rendered with no rows from 2022.
- Rank is the latest year's title. When titles conflict within a year, a ladder title beats an adjunct one, unless the person appears only on affiliated listings and no title names an SCS department as their home. People cross-appointed elsewhere and listed as core by an SCS department are therefore ranked by their home title.
- 78 people have unknown rank: they are named only on untitled pages (the S3D 'Read full bio' index, HCII name lists, lab pages).
- advises_phd rests on the advisers the sweep recorded. Faculty whose students the sweep never captured have no basis even when they run a group. The ladder list above names them.
