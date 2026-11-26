# Public NIH project query provenance

An original anonymous NIH RePORTER project-search POST response can support a
source-reviewed contact-PI claim. It is kept outside the GET capture cache.
Actual academic appointment, computing scope, candidate identity and PI
qualification remain separate requirements. A grant start or end never supplies
an employment boundary.

Keep the original response and collection receipt privately in
`stores/<school>/metadata/nih-reporter-post/<sha256>.json`. A hand-review entry
uses the actual API URL, `method: POST`, `request_json`, its canonical semantic
`request_fingerprint_sha256`, the original response hash, and an exact
`json_pointer` to the selected investigator's `full_name`.

Its `post_source_binding` names the actual endpoint, method, status, capture time,
request and fingerprint; response file/hash; receipt file/hash; and the exact
`receipt_query_index`. The receipt retains the original collection metadata.
The fingerprint is SHA-256 of UTF-8
`json.dumps(request_json, sort_keys=True, separators=(',', ':'))`. It is not a
claim about the bytes transmitted on the wire.

Offline replay rehashes both original artifacts and binds the receipt's method,
request, response, status and time. It checks that the selected project matches
the recorded application-ID or project-number query and the researcher is the
contact PI. Any supplied structured summary is replayed at its exact pointers.
Missing, altered or mismatched evidence fails closed. No GET request is invented
and distinct POST queries cannot overwrite each other at one URL.
