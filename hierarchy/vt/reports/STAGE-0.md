# Virginia Tech stage 0: charter and source preflight

2026-11-10. The school remains `onboarding`; no research or site release includes it.

- The local OpenAlex institution snapshot identifies Virginia Tech as `I859038795`, ROR `02smfhw86`. Its lineage also contains the transportation institute, agriculture station, veterinary/biomedical entities, and Carilion clinics. A lineage hit alone never qualifies a computing PI or a Virginia Tech appointment. The configured scope is full Computer Science plus source-reviewed computing faculty in other units.
- `school_config.py --check vt` passed. `school_hosts.py vt` checked the charter's 11 hosts: zero inconsistent. The Statistics, AOE, and CEE listing URLs were repaired to their observed destinations; Hume's dead `/people.html` probe was changed to its current home page. The VTechWorks host stays `wayback-only` pending path-specific access review.
- `stage-gate vt 0 --traps` reported zero charter traps; `stage-gate vt 0` passed with zero open items and 176,380 works visible for the institution in the local snapshot. That count is a broad source inventory, not admitted computing papers or a completeness measurement.
- Saved host receipt: `hierarchy/vt/derived/hosts.json` SHA-256 `8d8fac8a77058393d1dfb39a8dd861de67872d0a57fbb42749461df01e55be00`.

No faculty-year, lab, member, paper, or copy admission is implied by the stage-0 gate.
