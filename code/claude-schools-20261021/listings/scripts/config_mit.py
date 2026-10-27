"""MIT listing slots -> URL eras (YYYYMMDD inclusive). CDX `url` matching ignores the www prefix.

EECS: the Drupal 'Faculty & Advisors' page (one page, A-Z, emeriti inline) until the 2021 site move,
then the WordPress role pages (role/faculty is all faculty; emeriti and lecturers have their own roles).
CSAIL: 2022-2026 csail.mit.edu/people renders from a Solr endpoint (api-proxy/angular-solr), whose
PI-filtered responses Wayback captured and are used. 2016-2017 the PI page (biographies/PI/biolist.php) was a SIMILE Exhibit view whose rows came
from the JSON endpoint /csaildirectoryoutput/pi, so that endpoint is captured; from 2018 the
'Principal Investigators' role filter of csail.mit.edu/people (role:299) lists every PI on one page.
"""
D = "20160101", "20261231"
API = "csail.mit.edu/api-proxy/angular-solr"
# first 216 rows of the people index filtered to exactly the PI role groups (130-ish records: complete) ...
PI_ONLY = (r'_api_proxy_uri=people&.*rows=216&start=0&fq(\[\])?=ss_name:"Principal Investigators" OR '
           r'ss_name:"Core/Dual" OR ss_name:"Associates" OR ss_name:"Emeritus"(?! OR)')
# ... else any start=0 filter that includes the PI group (may add researchers; can be truncated at 216 rows)
PI_ANY = r'_api_proxy_uri=people&.*rows=216&start=0&fq(\[\])?=.*ss_name:"Principal Investigators"'

SLOTS = [
    {"dept": "EECS", "slot": "EECS faculty", "kind": "main", "urls": [
        ("eecs.mit.edu/people/faculty-advisors", "20160101", "20211231"),
        ("eecs.mit.edu/role/faculty/", "20210101", "20261231"),
    ]},
    {"dept": "EECS", "slot": "EECS faculty emeritus", "kind": "emeritus", "urls": [
        ("eecs.mit.edu/role/emeritus/", *D),
    ]},
    {"dept": "EECS", "slot": "EECS lecturers", "kind": "sub", "urls": [
        ("eecs.mit.edu/people/lecturers", "20160101", "20201231"),
        ("eecs.mit.edu/role/lecturers/", "20210101", "20261231"),
    ]},
    {"dept": "CSAIL", "slot": "CSAIL principal investigators", "kind": "main", "urls": [
        ("csail.mit.edu/csaildirectoryoutput/pi", "20160101", "20171231"),
        ("csail.mit.edu/people?person%5B0%5D=role%3A299", "20170101", "20261231"),
        # from 2022 the people page is script-rendered; its Solr endpoint, filtered to the PI role groups
        (API, "20220101", "20261231", {"prefix": True, "match": PI_ONLY}),
        (API, "20220101", "20261231", {"prefix": True, "match": PI_ANY}),
    ]},
]

DEPT_CODES = {"EECS": ["EECS"], "CSAIL": ["CSAIL"]}


def relevant_slots(pi, slot_name, slot):
    return slot["dept"] in pi.get("departments", [])
