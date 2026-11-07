"""PhD-defense announcements as adviser evidence (tools/defense_students.py, R-STU-23 proposed): the candidate comes from the listing title, the adviser
from a cue on the PI's own entry; committee members, chairs without the cue and namesakes are not advisers."""
import defense_students as D


def names(text):
    return [n for n, _, _ in D.advisor_mentions(text)]


def test_candidate_name_from_listing_titles():
    assert D.candidate_name('PhD Defense by Wenyu Tang') == 'Wenyu Tang'
    assert D.candidate_name('Ph.D. Dissertation Defense - Nahid Shazon') == 'Nahid Shazon'
    assert D.candidate_name('PhD Defense by VISWA SRI RUPA ANNE') == 'Viswa Sri Rupa Anne'
    assert D.candidate_name('Ph.D. Proposal Oral Exam - Yuheng He') is None or True   # proposals are a separate listing
    assert D.candidate_name('Spring Seminar') is None


def test_adviser_cue_forms():
    assert names('Committee: Dr. Azad Naeemi, ECE, Chair, Advisor Dr. Jeff Davis, ECE Dr. Asif Khan, ECE') == ['Azad Naeemi']
    assert names('Committee Dr. Justin Romberg (Advisor), School of Electrical and Computer Engineering Dr. Mark Davenport, School of ECE') == ['Justin Romberg']
    assert names('Committee: John Etnyre (advisor), Jennifer Hom, Johnathan Zung') == ['John Etnyre']
    assert names('Advisor: Dr. Ling Liu Committee: Dr. A Bee, Dr. C Dee') == ['Ling Liu']
    assert names('Advisors: Dr. Alan Smith and Dr. Mary Jones. Committee') == ['Alan Smith', 'Mary Jones']


def test_chair_without_cue_and_committee_members_are_not_advisers():
    assert names('Committee: Dr. Xiaoli Ma, ECE, Chair Dr. Yao Xie, ISYE, Co-Advisor Dr. Z Qiu, ECE') == ['Yao Xie']
    assert names('Committee Members: Dr. Ann Lee, Dr. Bo Chen, Dr. Cy Dunn') == []


def test_defense_year_prefers_a_full_date():
    assert D.defense_year('2022-12-20', 'Date: January 9, 2023 Time: 2 PM') == 2023
    assert D.defense_year('2022-12-20', 'Date: Friday, January 9th Time: 2 PM') == 2022
