"""A people page can itself be the selected lab site and link to alumni."""

import labpage_audit as audit


def test_previous_students_link_on_selected_people_page_is_alumni():
    people = "https://arbabianlab.stanford.edu/people"
    alumni = "https://arbabianlab.stanford.edu/previous-students-researchers"
    links = [(alumni, "previous students/researchers")]

    assert audit.classify_links(links, people, r"stanford\.edu")["alumni"] == [alumni]


def test_unrelated_people_link_is_not_alumni():
    people = "https://arbabianlab.stanford.edu/people"
    current = "https://arbabianlab.stanford.edu/people/student"

    assert audit.classify_links([(current, "Current students")], people, r"stanford\.edu").get("alumni") is None
