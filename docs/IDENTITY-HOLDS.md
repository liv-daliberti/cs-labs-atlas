# Explicit unresolved bibliography identities

A reviewed census override with both `no_identity: true` and a nonempty `why_no_identity` holds scientific attribution for that PI. This was already the documented stage-5 and paper-gap meaning; it is now enforced in the native builder.

The PI remains in the census with their faculty role, own lab, website source, appointment evidence and members. `pis.json` records the decision as `identityHold: {status: "reviewed_no_identity", reason: ...}`. A hold on any merged census spelling follows the merged PI. Explicit source input identifiers are retained, but automatic cached-DBLP/official-dump person and ORCID inference is withheld. No raw bibliography or capture is edited.

An ORCID, a unique-name DBLP inference, a verified collection-paper link, an anchored author ID or a coauthor cannot bypass the hold. All native paper-admission routes obey it, including direct DBLP, lab-page and primary-page recoveries. A paper can still belong to another PI with independent supported attribution. Held papers create no member–paper links for the held PI; their members and advising evidence remain present. Build counters distinguish held PIs, candidate authorships and recovered rows.

Resolve the reviewed decision only after a source-bound identity review. Then set `no_identity` false (or remove the resolved hold) in the reviewed input, recording the new source evidence and reason. Rebuilding resumes the ordinary identity, university-affiliation, appointment-year, paper-type and edition gates; clearing a hold alone does not admit a paper. A direct recovery or new name match does not silently clear the decision.

A read-only November 8 impact audit found 21 such PI decisions across Georgia Tech, Johns Hopkins, UChicago and staged Zhejiang. Three current canonical relations sat under two held PI names; their scientific validity requires source-specific adjudication, so the audit does not label all three false. The 11 new unresolved Zhejiang bibliography contexts have not been built. The code change does not itself rewrite any canonical package, global identity registry or copy catalog. Future reviewed rebuilds must account for their exact paper/link changes before promotion.

Regression coverage runs the native stages and package writer in both layouts. It checks retained PI/member/appointment/source data, ordinary behavior after source-review resolution, blocked automatic PID/ORCID inference, blocked direct recovery, independent other-PI papers, strict output schema and a hold attached only to a secondary merged spelling.
