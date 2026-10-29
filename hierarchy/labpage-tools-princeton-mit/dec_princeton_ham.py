"""Lab-page decisions: Princeton, Manoel Horta Ribeiro (Humans and Machines Lab). Worked example for the batch modules.

Sources: the live members page https://humans.cs.princeton.edu/people/ (2026-10-22) and its Wayback id_ captures
(only 2026 captures exist; the lab started at Princeton in 2025), the members directory index
https://humans.cs.princeton.edu/members/ (first names: alejandro alia brian cannoli francesco hayoung inhwa jason liv
manoel mattew reva romina; the subdirectories are empty), plus the lab publications page.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lpev import M, MS, Lab, Pubs  # noqa: E402,F401

SCH = "princeton"
D = {}

PPL = "https://humans.cs.princeton.edu/people/"
W0412 = "https://web.archive.org/web/20260412233049id_/https://humans.cs.princeton.edu/people/"
MEMBERS_DIR = "https://humans.cs.princeton.edu/members/"   # directory index, live 2026-10-22

D["Manoel Horta Ribeiro"] = Lab(
    lab_site="https://humans.cs.princeton.edu/",
    people_page=PPL,
    students=[
        M(SCH, "Jason Greenfield", "phd", None, PPL, quote="Jason Greenfield PhD Student"),
        M(SCH, "Inhwa Song", "phd", None, PPL, quote="Inhwa Song PhD Student"),
        M(SCH, "Matthew Munoz", "masters", None, PPL, quote="Matthew Munoz MSE Student"),
        M(SCH, "Alia ElKattan", "postdoc", None, PPL, quote="Alia ElKattan Postdoc w/ Andy Guess and Brandon Stewart"),
        M(SCH, "Francesco Salvi", "phd", None, PPL, quote="Francesco Salvi PhD Student"),
        M(SCH, "Hayoung Jung", "phd", None, PPL, quote="Hayoung Jung PhD Student w/ Aleksandra Korolova"),
        M(SCH, "Reva Hirave", "masters", None, PPL, quote="Reva Hirave MSE Student"),
        M(SCH, "Romina Mahinpei", "phd", None, PPL, quote="Romina Mahinpei PhD Student w/ Andrés Monroy-Hernández"),
        M(SCH, "Alejandro Cuevas", "postdoc", None, PPL, quote="Alejandro Cuevas Postdoc"),
        M(SCH, "Liv G. d'Aliberti", "phd", None, PPL, quote="Liv G. d'Aliberti PhD Student"),
        M(SCH, "Brian Phillips", "masters", None, PPL, quote="Brian Phillips MSE Student"),
        M(SCH, "Marianne Aubin Le Quéré", "postdoc", None, PPL,
          quote="Alumni Marianne Aubin Le Quéré Postdoc Assistant Professor, University of Illinois Urbana-Champaign"),
        M(SCH, "Marianne Aubin Le Quéré", "postdoc", None, W0412, quote="Marianne Aubin Le Quéré Postdoctoral Fellow"),
        M(SCH, "Tri-An Nguyen", "other", [2026, 2026], PPL, quote="Visitors 2026 Tri-An Nguyen (Rutgers University)",
          note="visitor (Rutgers University)"),
        M(SCH, "Hannah Hollosi", "other", [2026, 2026], PPL, start="Visitors 2026", end="Hannah Hollosi (Rutgers University)",
          note="visitor (Rutgers University)"),
        M(SCH, "Omar El Malki", "other", [2025, 2025], W0412, quote="Omar El Malki Visiting Student (EPFL) Summer 2025",
          note="visiting student (EPFL)"),
        M(SCH, "Abdurahman Maarouf", "other", [2025, 2025], W0412,
          quote="Abdurahman Maarouf Visiting Student (LMU Munich) Summer 2025", note="visiting student (LMU Munich)"),
        M(SCH, "Om Vyas", "undergraduate", [2026, 2026], PPL, quote="Undergrads 2026 Om Vyas (Senior Thesis)"),
        M(SCH, "Jongnam Ahn", "undergraduate", [2026, 2026], PPL, start="Undergrads 2026", end="Jongnam Ahn (Senior Thesis)"),
        M(SCH, "Allen Liu", "undergraduate", [2026, 2026], PPL, start="Undergrads 2026", end="Allen Liu (Senior Thesis)"),
        M(SCH, "Stephanie Oh", "undergraduate", [2025, 2025], PPL, start="2025", end="Stephanie Oh (Senior Thesis)",
          after="Allen Liu (Senior Thesis)"),
        M(SCH, "Skylor Wong", "undergraduate", [2025, 2025], PPL, start="2025", end="Skylor Wong (Senior Thesis)",
          after="Allen Liu (Senior Thesis)"),
        M(SCH, "Denish Patel", "undergraduate", [2025, 2025], PPL, start="2025", end="Denish Patel (Senior Thesis)",
          after="Allen Liu (Senior Thesis)"),
    ] + [
        # the members directory (Apache index of /members/, first names only; 'mattew' sic). Each joins the full-name
        # row above as an extra source (build merges a first-name-only listing into the one compatible row).
        M(SCH, n, "member", None, MEMBERS_DIR, start="Index of /members", end=f"{n}/",
          note="HAM members directory entry (first name only)")
        for n in ("alejandro", "alia", "brian", "francesco", "hayoung", "inhwa", "jason", "liv", "mattew", "reva", "romina")
    ],
    pubs=[Pubs("https://humans.cs.princeton.edu/publications.html",
               spec={"split": "hr", "title": "div.col-lg-9 > p", "year": "div.col-lg-1", "venue": "div.col-lg-2"},
               note="column layout separated by <hr>; 'preprint' rows take their year from the arXiv id")],
    notes=("Members page lists 12 people plus the PI and the mascot Cannoli (a dog, not recorded); the /members/ "
           "directory index lists the same 11 non-PI people by first name ('mattew' = Matthew Munoz) and is attached to "
           "each as an extra source. Wayback has only 2026 "
           "captures (lab founded 2025); the 2026-04-12 capture adds the past visitors and Marianne Aubin Le Quéré as "
           "'Postdoctoral Fellow' before she moved to Alumni. Liv G. d'Aliberti is the held Olivia d'Aliberti. The "
           "publications page includes the PI's pre-Princeton (EPFL) papers; affiliation is checked elsewhere."),
)
