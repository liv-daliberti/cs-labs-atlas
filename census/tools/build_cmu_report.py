"""census/cmu-report.md from census/cmu-faculty.json and census/cmu-listing-only.json (tools/build_cmu_census.py).
usage: build_cmu_report.py
"""
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cmu_census import name_match, toks  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
RANKS = ['ladder', 'research', 'teaching', 'adjunct_courtesy', 'visiting', 'emeritus', 'not_faculty', 'unknown']
DEPTS = ['CSD', 'RI', 'HCII', 'S3D', 'MLD', 'LTI', 'CBD']


def why_unlisted(r):
    if any('not a person' in n for n in r['notes']):
        return 'not a person name (a title or unit string)'
    if not r['sources']:
        return 'no source page names the person'
    if r['rank'] == 'not_faculty':
        return 'latest titles are postdoc / student / TA titles'
    if all('directory' in s['kind'] for s in r['sources']):
        return 'only the SCS-wide directory (lists staff, students and visitors too)'
    return 'named on profile, thesis or lab pages, but on no department faculty listing'


def canon(n):
    """Family-name key and given name, with suffixes dropped and umlaut transliterations folded (Kaestner = Kästner)."""
    t = [x for x in toks(n) if x not in ('jr', 'sr', 'ii', 'iii', 'iv')]
    t = [re.sub(r'([aou])e', r'\1', x) for x in t]
    return t


def dup_pairs(d):
    fam = defaultdict(list)
    for r in d:
        t = canon(r['name'])
        if len(t) >= 2:
            fam[t[-1]].append(r)
    out = []
    for rs in fam.values():
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                x, y = canon(a['name']), canon(b['name'])
                if name_match(' '.join(x), ' '.join(y)) or x == y:
                    out.append((a['name'], a['is_pi'], b['name'], b['is_pi']))
    return sorted(out)


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '|'.join('---' if i == 0 else '--:' for i in range(len(head))) + '|']
    out += ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows]
    return '\n'.join(out)


def main():
    d = json.loads((HERE / 'cmu-faculty.json').read_text())
    lo = json.loads((HERE / 'cmu-listing-only.json').read_text())
    pis = [r for r in d if r['is_pi']]
    L = []
    w = L.append
    w('# CMU School of Computer Science faculty census, 2016–2026\n')
    w('Step 0 of the four-school build: every person the CMU sweep files as faculty, checked against dated department '
      'listings, with a rank and a PI decision. Built by `tools/build_cmu_census.py`; this report by `tools/build_cmu_report.py`.\n')
    w('- `cmu-faculty.json`: one record per person, with sources, verbatim quotes, rank, rank_by_year, PI basis, lab units and notes.')
    w('- `cmu-listing-only.json`: names on the department listings that the structure lacks.')
    w('- `captures-cmu.sqlite`: the yearly Wayback captures this census added (MLD core, affiliated and adjunct; CSD faculty directory; SCS directory), from `tools/fetch_listings.py`.\n')
    w(f"**{len(d)} people** carry the faculty role in the sweep's `structure.json`. They are backed by {sum(len(r['sources']) for r in d):,} sources, each with a verbatim quote. "
      f"**{len(pis)} are PIs.** {sum(1 for r in d if r['scs_appointment'] == 'core')} held a core SCS appointment at some point in the period, "
      f"{sum(1 for r in d if r['scs_appointment'] == 'affiliated')} appear only on affiliated / adjunct listings, and "
      f"{sum(1 for r in d if r['scs_appointment'] == 'unlisted')} appear on no department listing.\n")

    w('## Counts by rank and department\n')
    w('Rank is taken from the latest dated title. A person listed in more than one department is counted in each, so the department columns sum to more than the total. '
      '`rank_by_year` in the JSON keeps the earlier ranks: for example, faculty who left and now hold an adjunct title were ladder faculty earlier in the period.\n')
    rows = []
    for k in RANKS:
        rs = [r for r in d if r['rank'] == k]
        rows.append([k, len(rs)] + [sum(1 for r in rs if dp in r['departments']) for dp in DEPTS] + [sum(r['is_pi'] for r in rs)])
    rows.append(['**all**', len(d)] + [sum(1 for r in d if dp in r['departments']) for dp in DEPTS] + [len(pis)])
    w(table(['rank', 'people'] + DEPTS + ['PIs'], rows) + '\n')

    w('## PIs\n')
    b = Counter(r['pi_basis']['kind'] for r in pis)
    w("A PI leads a research group. The basis is recorded in order of strength, with the quote and URL in `pi_basis`:\n")
    w(f"- **named_lab** ({b['named_lab']}): the person is the named leader of a non-umbrella lab (no center, institute, program or research area in the name; at most three leaders), quoted from the lab's own page.")
    w(f"- **own_group** ({b['own_group']}): the person alone leads a collection research unit, or their homepage or group page lists students under a heading ('Current PhD Students', 'Lab Members').")
    w(f"- **advises_phd** ({b['advises_phd']}): a PhD student or alumnus names the person as adviser, thesis chair or supervisor on a captured page.\n")
    w('Adjunct and courtesy faculty count as PIs only when the group is at CMU. Advising alone does not make an external adjunct a PI unless they held a core SCS appointment in the period. '
      'Faculty who left CMU but led groups here in 2016–2026 stay PIs; their latest rank is shown.\n')
    pr = Counter(r['rank'] for r in pis)
    w('PIs by latest rank: ' + ', '.join(f'{k} {pr[k]}' for k in RANKS if pr[k]) + '.\n')
    lad = [r for r in d if r['rank'] == 'ladder' and not r['is_pi']]
    w(f"**{len(lad)} ladder-rank people have no PI evidence.** For {sum(1 for r in lad if r['advised_phd'])} of them the sweep records advisees, but no captured page states the advising. "
      "The rest have no recorded advisees and no lab or group page. Three kinds of record land here. "
      "Some are faculty of other colleges carried on SCS lists, whose titles name Psychology, Statistics, Tepper or Philosophy. "
      "Some are SCS faculty whose students the sweep never captured (for example Philip Koopman, Danny Sleator and Raj Reddy). "
      "Some are duplicate records of a person whose other record is a PI (see the duplicates below). "
      "They are listed here so a reviewer can add a basis by hand:\n")
    w(', '.join(sorted(f"{r['name']}" + (f" ({r['advised_phd']} advisees)" if r['advised_phd'] else '') for r in lad)) + '\n')

    w('## People the structure has that no listing confirms\n')
    un = [r for r in d if r['scs_appointment'] == 'unlisted']
    c = Counter(why_unlisted(r) for r in un)
    w(f"{len(un)} faculty-role people appear on no department faculty listing (core or affiliated):\n")
    w(table(['why', 'people'], c.most_common()) + '\n')
    for reason in ['no source page names the person', 'not a person name (a title or unit string)', 'only the SCS-wide directory (lists staff, students and visitors too)']:
        names = sorted(r['name'] for r in un if why_unlisted(r) == reason)
        if names:
            w(f"- *{reason}* ({len(names)}): " + ', '.join(names))
    nf = [r for r in d if r['rank'] == 'not_faculty']
    w(f"\nAcross the whole census, {len(nf)} people the structure files as faculty have postdoc, PhD-student or TA titles as their latest stated titles. "
      f"Most are in CSD ({sum(1 for r in nf if 'CSD' in r['departments'])}) and HCII ({sum(1 for r in nf if 'HCII' in r['departments'])}); "
      f"{sum(1 for r in nf if any('adjunct-faculty' in s['url'] for s in r['sources']))} are CSD postdocs whose profiles sit under CSD's `people/adjunct-faculty/` path. Their latest title and quote are in the JSON. "
      "They are kept in the census but marked `not_faculty: true`, and none is a PI.\n")
    multi = [r for r in d if any('collection records' in n for n in r['notes'])]
    nocoll = [r for r in d if r['collection_person_id'] is None and r not in multi]
    w(f"Collection ids: {sum(1 for r in d if r['collection_person_id'])} people match exactly one collection person by name. "
      f"{len(multi)} match several collection records, which are duplicates to merge. {len(nocoll)} match none.\n")

    dups = dup_pairs(d)
    w(f"**Probable duplicate records in the structure ({len(dups)} pairs).** Each pair is the same family name with a short form, nickname, transliteration or suffix variant. "
      "The census keeps both records as the structure has them; the PI flag can differ between the two, and they should be merged before any counts are used:\n")
    w('; '.join(f"{a} [{'PI' if pa else 'not PI'}] / {b} [{'PI' if pb else 'not PI'}]" for a, pa, b, pb in dups) + '\n')

    w('## People the listings show that the structure lacks\n')
    w(f"{len(lo)} names on the captured department listings match no structure person, after matching on full names, given-name short forms, nicknames and family name plus initial:\n")
    w(table(['name', 'rank', 'dept', 'years', 'title (verbatim)'], [[x['name'], x['rank'], ','.join(x['departments']), f"{min(x['years'])}–{max(x['years'])}" if len(x['years']) > 1 else x['years'][0], x['titles'][-1][:90]] for x in lo]) + '\n')
    w("Most are MLD core or affiliated faculty whose last listing is early in the period (Smola, Guestrin and Fienberg in 2016–2017), or who are based in other colleges or universities (Kemp, Neill, Batmanghelich, Hruschka, Tibshirani). "
      "The others are CSD visitors and lecturers, and SCS-directory project scientists. 'Nina Balcan' on the 2016–2019 CSD directory is Maria-Florina Balcan, who is in the structure; that alias is not matched automatically.\n")

    w('## Units to create\n')
    prop = [r for r in pis if r['lab_units'] and isinstance(r['lab_units'][0], dict)]
    pnames = {r['name'] for r in prop}
    pb = Counter(r['pi_basis']['kind'] for r in prop)
    w(f"**{len(prop)} PIs lead no group-type unit in the collection.** Group-type means a department-, SCS- or research-listed lab, or a project-lab row, that is not an umbrella and has at most three leaders. "
      f"Of these, {sum(1 for r in prop if r['adviser_group_units'])} have only their per-adviser listing unit (`adviser_group_units`), which AGENTS.md keeps distinct from a lab. "
      f"Each gets a proposed `<name> research group` in `lab_units`, carrying the PI basis as its evidence ({pb['advises_phd']} advising, {pb['own_group']} own-group page). "
      f"{len(pis) - len(prop)} PIs already have a group-type unit. "
      f"{sum(1 for a, pa, b, pb in dups if pa and pb and a in pnames and b in pnames)} of the names below are duplicate pairs from the list above, so merging them leaves "
      f"{len(prop) - sum(1 for a, pa, b, pb in dups if pa and pb and a in pnames and b in pnames)} units to create.\n")
    w(', '.join(sorted(r['name'] for r in prop)) + '\n')

    w('## Gaps and limits\n')
    w('- Listings: RI, HCII and CBD are covered every year 2016–2026. LTI has no 2018 capture. ISR/S3D has none for 2016 or 2019. '
      'MLD core, affiliated and adjunct cover 2016–2025. CSD covers 2016, 2017 and 2019 (directory/faculty) and 2023–2026 (people/faculty). '
      'The SCS-wide directory captures hold only their first page (50 rows) for 2016–2021, and are script-rendered with no rows from 2022.')
    w("- Rank is the latest year's title. When titles conflict within a year, a ladder title beats an adjunct one, "
      'unless the person appears only on affiliated listings and no title names an SCS department as their home. '
      'People cross-appointed elsewhere and listed as core by an SCS department are therefore ranked by their home title.')
    w(f"- {sum(1 for r in d if r['rank'] == 'unknown')} people have unknown rank: they are named only on untitled pages (the S3D 'Read full bio' index, HCII name lists, lab pages).")
    w('- advises_phd rests on the advisers the sweep recorded. Faculty whose students the sweep never captured have no basis even when they run a group. The ladder list above names them.')
    (HERE / 'cmu-report.md').write_text('\n'.join(L) + '\n')
    print(json.dumps(dict(report=str(HERE / 'cmu-report.md'), lines=len(L))))


if __name__ == '__main__':
    main()
