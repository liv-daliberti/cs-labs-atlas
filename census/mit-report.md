# MIT CS faculty census and PIs (2016-2026)

Built by `census/build_mit_census.py` from existing captures (see its docstring); every source carries URL, sha256 and a verbatim quote.

## Counts

- People in scope: 218
- By rank: {'ladder_faculty': 154, 'emeritus': 19, 'adjunct_visiting': 4, 'teaching': 20, 'research_scientist_pi': 20, 'unknown': 1}
- PIs: 167 ({'own_group': 80, 'advises_phd': 18, 'named_group': 69})
- With a unique collection person id: 191; ambiguous: 23
- Lead an existing collection research-group unit: 68; units to create ("<Name> group"): 99
- EE faculty leading CSAIL groups (flagged): 2; research-staff PIs: 20

## Structure vs listings

- Structure faculty (184) that no census listing confirms (0): 
- Census people the structure lacks (34), by rank: {'teaching': 18, 'ladder_faculty': 10, 'adjunct_visiting': 1, 'research_scientist_pi': 4, 'unknown': 1}: Adam Hartz, Adrian Dalca, Alexandru Damian, Alfred Spector, Ana Bell, Andrew Wang, Bailey Flanigan, Ben Lindquist, Brendan O’Neill, Brian Hedden, Brynmor Chapman, David Alexander Bruns-Smith, Erik Hemberg, Gabriele Farina, Gim P Hom, Jayson Lynch, Jonathan Rosenfeld, Joseph Steinmeyer, Katrina LaCurts, Kimberle Koile, Lindsey Raymond, Mariana Popescu, Martin Fleming, Max Goldman, Roger Mark, Shen Shen, Silvina Hanono Wachman, Srini Raghuraman, Stephen Bates, Tao Schardl, Tony Eng, Vince Monardo, William Leiserson, Zachary Abel
  (the structure kept professors only: lecturers, research scientists leading groups and EE faculty listed as CSAIL PIs enter here)

## Evidence gaps

- PIs whose named-group basis has no verbatim leadership quote in our captures: Christina Delimitrou, Dylan Hadfield-Menell, Henry Corrigan-Gibbs, John Fisher, Mina Konakovic Lukovic, Nickolai Zeldovich, Phillip Isola, Pulkit Agrawal, Regina Barzilay, Roger Mark, Sara Beery, Song Han
- Rank unknown: Jonathan Rosenfeld (FutureTech xAI Program Manager)
- Collection person id ambiguous (several collection records, none with the profile URL): 23; no collection record: 4

## Codex's 101-unit lab audit

- Audit units that are someone's own lab (at most two leaders; centers, institutes, Lincoln Laboratory and Sloan groups excluded): 72 of 101
- Their leaders not in this census (3): Camilo Mora, Miguel Rodríguez García, Sertac Karaman
- Leaders of the other audit units (centers such as CCSE and CBMM, Lincoln Laboratory staff groups, Sloan, IDSS) are outside this census's scope: 173 names
- Census PIs who lead no audited unit (100): Adam Belay, Alan Oppenheim, Alan Willsky, Albert R. Meyer, Aleksander Mądry, Anand V Natarajan, Anant Agarwal, Anantha Chandrakasan, Andreea Bobu, Andrew Lo, Ankur Moitra, Antonio Torralba, Arvind, Asu Ozdaglar, Berthold Horn, Bill Long, Butler Lampson, Caroline Uhler, Charles Leiserson, Cheng Zhi (Anna) Huang, Christopher Terman, Collin Stultz, Constantinos Daskalakis, Dana Moshkovitz, Daniel Huttenlocher, Daniel Sanchez, Daniel Weitzner, David Gifford, Devavrat Shah, Erik Demaine, F. J. Corbato, Fadel Adib, Frederic Durand, Gregory Wornell, Guy Bresler, Hal Abelson, Howard Shrobe, Isaac Chuang, Jack Dennis, Jacob Andreas, Jacob White, Jas Brooks, Jeffrey Jaffe, Jerome Saltzer, Joel Moses, Jonathan Kelner, Jonathan Ragan-Kelley, Judy Brewer, Julian Shun, Kaiming He, Li-Shiuan Peh, M. Frans Kaashoek, Manya Ghobadi, Martin Rinard, Martin Wainwright, Mengjia Yan, Michael Cafarella, Michael Goemans, Michael Sipser, Michael Stonebraker, Mitchell Gordon, Mohsen Ghaffari, Muriel Médard, Neil Thompson, Omar Khattab, Pablo Parrilo, Patrick Jaillet, Piotr Indyk, Rachit Nigam, Robert Berwick, Robert Morris, Rodney Brooks, Ronald Rivest, Ronitt Rubinfeld, Ruth Rosenholtz, Ryan Williams, Sam Hopkins, Samuel Madden, Scott Aaronson, Shafrira Goldwasser

Codex's audit (atlas/data/mit-lab-audit.json.gz, credited) covers CSAIL research groups and communities; the census adds every CS faculty member and CSAIL PI, and proposes a "<Name> group" unit for PIs without one.
