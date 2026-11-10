# Virginia Tech stage 0: charter and source preflight

2026-11-10. The school remains `onboarding`; no research or site release includes it.

- The local OpenAlex institution snapshot identifies Virginia Tech as `I859038795`, ROR `02smfhw86`. Its lineage also contains the transportation institute, agriculture station, veterinary/biomedical entities, and Carilion clinics. A lineage hit alone never qualifies a computing PI or a Virginia Tech appointment. The configured scope is full Computer Science plus source-reviewed computing faculty in other units.
- `school_config.py --check vt` passed. `school_hosts.py vt` checked the charter's 12 hosts: zero inconsistent. The Statistics, AOE, and CEE listing URLs were repaired to their observed destinations; Hume's dead `/people.html` probe was changed to its current home page. Plant and Environmental Sciences was added after official Sanghani and SPES pages showed computing-method faculty outside the initial nine affiliated units. Its `spes.vt.edu` host passed robots and live-page checks. The VTechWorks host stays `wayback-only` pending path-specific access review.
- `stage-gate vt 0 --traps` reported zero charter traps; `stage-gate vt 0` passed with zero open items and 176,380 works visible for the institution in the local snapshot after the SPES addition. That count is a broad source inventory, not admitted computing papers or a completeness measurement.
- Saved host receipt: `hierarchy/vt/derived/hosts.json` SHA-256 `c1594fca59355f26f49ad74087d9c8b850fb673ac9771af14c79779df8912766`.

No faculty-year, lab, member, paper, or copy admission is implied by the stage-0 gate.
