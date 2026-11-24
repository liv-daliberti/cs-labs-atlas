# Reviewed DBLP ORCID inheritance

An owned DBLP person binding establishes a bibliography identity; it does not require importing every ORCID listed on that record. Source review found multiple ORCIDs on two Zhejiang person records. These identifiers are unresolved, not proven false. Keep the original XML and person sidecars intact.

A per-PI census override can opt into controlled inheritance:

```json
{
  "dblp_orcid_review": {
    "allowed": [],
    "why": "No independently reviewed owned ORCID source has been admitted.",
    "evidence": []
  }
}
```

An empty `allowed` list withholds all additional ORCIDs from the DBLP dump. For every nonempty allowed entry, add an evidence object with that bare `orcid`, original source `url`, `sha256` and a literal `quote` containing the same identifier. The source must actually establish that identifier for this PI; a DBLP link alone is not independent corroboration for an uncertain DBLP identifier. Invalid or unbacked allowlists, duplicate identifiers and conflicting reviews across merged census spellings fail before native admission.

The native PI record carries `dblpOrcidReview`. The dump still supplies its ordinary owned PID, publication DOI/title anchors and original metadata. ORCIDs outside the review are recorded under `dblpOrcidsWithheld` and counted once per PI. They do not become authorship or person-ID anchors. Independently reviewed explicit census/override ORCIDs remain unchanged; this policy governs automatic dump inheritance. An active `identityHold` continues to block bibliography inference and paper attribution even if the ORCID inheritance review has positive entries.

Without this optional input, existing behavior is unchanged. No new ORCID or PID is created merely by listing it in the policy: only permitted identifiers actually present on the source DBLP record can be inherited. The new contract does not declare any withheld identifier false, merge people, rewrite raw records or change public/private copy rights.

Regression checks cover empty and positive allowlists, complete source preservation, repeated-run idempotence, explicit census identifiers, unresolved identity holds, ordinary default behavior, native round trips and strict PI output schemas in both data layouts.
