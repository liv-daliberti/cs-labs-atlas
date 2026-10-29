# Stanford computing faculty census

Built 2026-10-27 19:43 UTC by `claude-stanford-20261027/tools/st_census.py` from dated Wayback captures of the Stanford CS faculty listings (cs.stanford.edu/directory/faculty 2016-2023: Regular, Lecturers, Emeritus, Courtesy, Adjunct, Visiting and Acting sections; the 2023- Drupal pages people-cs/faculty-name, emeritus, adjunct, courtesy, visiting), the EE faculty listing (ee.stanford.edu/people/faculty and its paged views 2016-2026; EE-only faculty kept when they publish in CS venues by the cs_related_candidates rule, people/ee_cs.json), Stanford Profiles pages (live 2026 and Wayback captures: title, appointments, Stanford Advisees), curated faculty homepage student lists (people/homepage_advising.json) and SDR dissertation MODS (degree supervisor).

People listed (faculty ranks, research staff excluded): 239 (on a 2026 listing: 156).

| rank | people | listed in 2026 | PIs |
|---|---|---|---|
| ladder | 101 | 89 | 97 |
| teaching | 2 | 2 | 2 |
| courtesy | 42 | 34 | 37 |
| adjunct | 18 | 5 | 3 |
| emeritus | 26 | 22 | 7 |
| visiting | 32 | 4 | 0 |
| lecturer | 15 | 0 | 0 |
| unknown | 3 | 0 | 0 |

PIs: 146 (advises_phd 144, sole_lab_head 1, advises_postdoc 1); not PIs: 93.

PIs by listing department: CS 101, CS+EE 27, EE 18.

CS-related additions from other departments (census/stanford-additions.json): 84.

Professor-rank faculty with no PI evidence found (no PhD / postdoc advisee on any captured profile, no curated homepage list, no 2016-2026 SDR dissertation they supervised, no sole lab):

- Andrea Goldsmith (ladder; EE; listed 2016-2020)
- Jennifer Widom (ladder; CS, EE; listed 2016-2026)
- Mehran Sahami (ladder; CS; listed 2016-2026)
- Serafim Batzoglou (ladder; CS; listed 2016-2017)

Not PIs by rule (lecturers, visiting and acting faculty): Alex Russo, Aurore Fass, Axel Hochstein, Bruno Ribeiro, Christina Wodtke, Christopher Hahn, Cynthia Lee, David Broman, David Varodayan, Dolière Francis Somé, Dominik Michels, Giancarlo Pellegrino, Hamed Nemati, Jay Borenstein, Jeff Heer, Jerry Cain, Jidong Zhai, Jonathan Kelly, Jonathan Ullman, Julie Stanford, Julie Zelenski, Kamil Krzysztof Kluczniak, Keith Schwarz, Kwang Yi, Leonardo Barbosa e Oliveira, Lisa Yan, Lucjan Hanzlik, Marco Patrignani, Marty Stepp, Micah Steven Siegel, Michael Chang, Mike Carbin, Mohamed Elhoseiny, Nate Foster, Nick Parlante, Nick Troccoli, Norbert Pohlmann, Patrick Young, Scott Klemmer, Shahar Dobzinski, Shobha Vasudevan, Sridhar Mahadevan, Victor Ostromooukhov, Victoria Kirst, Yaron Singer, Youngkeun Kwon, Zhikun Zhang.

