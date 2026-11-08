# Stated advisees are a separate paper authority

`identity.anchors` builds two indexes used by R-PAP-04 (a stated advisee as identity evidence), R-PAP-11 (a stated advisee's own school affiliation) and R-PAP-12 (a stated advisee on an unaffiliated byline). Lab membership, a degree role and a generic students heading do not establish that authority.

The selector changes only these two indexes. It does not rewrite members, relation types, roles, years, source observations, person IDs, aliases or student-paper statuses. Ordinary member-paper candidate matching remains unchanged. Papers can nevertheless correctly lose identity or affiliation support, including downstream author-ID anchors; their dependent links may consequently disappear in a future authorized build. No legacy paper-equality promise is made.

## Exact-source recovery

A qualifying relation needs an actual source with URL, hash and quote. The source decision is keyed by PI, literal member name (including already recorded within-lab aliases) and the exact URL/hash/quote tuple. There is no automatic URL, hash, quote, surname or initials equivalence.

An existing native relation label such as `researched_advising` is not sufficient: older compilers generated it from degree roles. Advisory proof can instead be recovered from:

- An explicitly reviewed `relationship: advising` row in an already consumed reviewed evidence input. `relationship: membership` is a hard negative for the same bound source, including stale compiled advising labels.
- A reviewed, PI-owned `Advisees`/supervised-students section with a complete PI-role source. The entry quote may omit the heading; the exact registered row carries that context.
- A finite prior reviewed relationship-basis form: `PI-owned personally named roster`; `PI personal Students and Postdoctoral Fellows; explicit dates and full co-adviser statements`; or the existing `PI-owned current Students roster; source explicitly names … appointment, no doctoral inference` format. These require the same reviewed flag, exact source-owner PI and complete role source. They are compatibility for recorded source decisions, not a rule granting authority to unknown owned-student headings. Explicit membership still overrides them.
- A named-adviser collection context with its exact native source tuple and the PI's full name in that source. A suggested person ID or an expanded initial/surname is insufficient.
- The PI's reviewed `advises_phd` basis for a matching `pi_basis_advising` relation.
- A literal full-name adviser, co-supervision or doctoral/master's-student-of statement in the relation source, including the existing named-adviser/DSpace parsers and labelled adviser metadata. A degree label alone remains insufficient.

Membership-only and unknown relation types furnish no advisory anchor. Program/reader roles, administrative postdoctoral faculty sponsorship, weak relations and a student's own entry naming other advisers only are excluded. Genuine named PI co-advising survives another adviser being present. A generic `Academic Advisor` label alone is not treated as a research-advising decision. One independently supported advising episode can qualify a person who also has separate membership/weak episodes.

## Review and validation

The cross-school audit uses read-only, hash-bound copies of saved member, paper and link records, plus available original compiled contexts/reviewed inputs. A missing or changed historical proof is **unavailable advisory authority**, not evidence that the person, membership or paper is false. Source-age, same-name/ORCID conflicts and wrong-university attribution remain separate questions.

Focused regressions exercise actual native paper identity and affiliation consumers, an independent-paper membership candidate control, exact source-preimage mismatches, compiler-omitted contextual headings, explicit membership overrides, named co-advising, weak/reader/program/sponsor cases and initials/surname-only negatives. Static impact reports identify potential direct and transitive paper dependencies and their existing verified/candidate link statuses. They do not substitute for serialized source-bound native trials or authorize canonical/global-ID writes.
