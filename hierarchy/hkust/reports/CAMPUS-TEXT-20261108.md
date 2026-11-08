# Explicit excluded-campus source text, 2026-11-08

The refreshed isolated HKUST build (`32148999`, 848 PI–paper relations, 253 member–lab pairs) exposed four additional Guangzhou-only literal affiliations that the earlier parenthesis-sensitive regex treated as Hong Kong evidence:

- `W4387724855`: `Hong Kong University of Science and Technology Guangzhou Information Hub`.
- `W7128537928`: `HKUST(GZ) / HKUST Guangzhou / Hong Kong , China`.
- `W7154488741`: `DSA , HKUST (GZ)&HKUST Guangzhou , China`.
- `W7163196877`: `Hong Kong University of Science and Technology , Guangzhou , China`.

The final record has a derived primary Hong Kong institution ID without the excluded Guangzhou ID. A derived institution mapping is not independent evidence against the literal excluded-campus affiliation. The charter now recognizes these unparenthesized/comma-separated variants and declares an explicit `affiliation.excluded_regex`. The generic own-authorship guard holds such a record even without an excluded institution ID. No campus policy or institutional lineage is added: this enforces the existing separation of Guangzhou from primary Hong Kong appointments.

Independent own primary or dual raw affiliation remains eligible. A separately reviewed primary-paper byline can still rescue misassigned metadata through the ordinary R-PAP-10 path. A coauthor’s school, an anchored PI identity or a derived primary institution ID alone cannot override the explicit exclusion. Ambiguous Fok Ying Tung/Shenzhen or bare-HKUST contexts remain source-review questions; this change does not relabel them.

A replay checked the exact four original 2026 OpenAlex authorships, identified by their saved work IDs and Lei Chen’s own author ID, against the unchanged source SQLite SHA-256 `30ef739ee69e6848643a00c207b1d18a5343ae9cdcceb2232556a22dbcefb094`. The originals and shared scientific packages were not modified. All four now fail only the ordinary own-school evidence path. Full PDFs and individual affiliation evidence, where available, remain the means to adjudicate genuine dual appointments.

Focused verification: 72 tests passed, covering the four actual variants with primary-only, excluded-only, both and absent institution IDs; exact source preservation; independent primary/dual raw positives; native PI/coauthor fallback negatives in both layouts; primary-paper rescue; and invalid-regex validation. The 18,043,539,456-byte Tsinghua discovery extension and other school policies are untouched. No newly accepted paper, person registry or copy status is created by this change. The earlier native trial remains isolated until the revised source-scope behavior is rebuilt and reviewed.
