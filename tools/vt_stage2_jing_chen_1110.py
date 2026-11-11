"""Resolve the Jing Chen bibliography candidate to a VT CS doctoral student."""

import json

import atlas_paths as P


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Jing Chen'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=[], source='dblp_affiliation',
        decision='not_faculty_listed',
        reason=('The person-authored profile identifies Jing Chen as a Virginia Tech '
                'CS PhD student from August 2025, previously a Zhejiang University '
                'master’s student, and an AIWaves intern mentored by Wangchunshu Zhou '
                'in August–October 2023. The candidate DBLP PID lists Zhejiang and VT '
                'and the 2023 Agents paper coauthored with Wangchunshu Zhou at AIWaves. '
                'Those independent identity details link this candidate to the student '
                'profile; they do not establish a VT professor-rank appointment.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/27/4364-60'], dblp_window=10,
                      affiliation_notes=['Zhejiang University', 'Virginia Tech']),
        faculty_evidence=[], status_evidence=[dict(
            url='https://jingchen123.notion.site/jc', observed='2026-11-10',
            quote=('Virginia Tech 2025 -- Present Ph.D. in Computer Science; '
                   'Zhejiang University 2022 -- 2025 Master in Software Engineering; '
                   'AIWaves 2023.08 -- 2023.10 Mentor: Wangchunshu Zhou'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional=('Reopen if the DBLP PID is shown to belong to another Jing Chen '
                     'or a dated VT professor-rank appointment is found.'),
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Jing Chen student role with identity bridge')


if __name__ == '__main__':
    main()
