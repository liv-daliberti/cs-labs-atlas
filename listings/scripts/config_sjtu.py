"""SJTU School of Computer Science listing slots -> URL eras (YYYYMMDD inclusive). CDX `url` matching ignores the www prefix.

Evidence (CDX probes of 2026-11-10, scratch/sjtu-coverage-1110/cdx-evidence.json and cdx-evidence2.json; status 200 html, collapsed):
  www.cs.sjtu.edu.cn/Faculty.aspx and /People.aspx      captured through 2016-2025 (71 and 2723 captures by prefix)
  www.cs.sjtu.edu.cn/en/Faculty.aspx                     the English faculty list, captured every year 2016-2024
  cs.sjtu.edu.cn/cse/Faculty.aspx                        the 2025 move (School of Computer Science, Cyber Science and Engineering, Cryptography)
  cs.sjtu.edu.cn/active/ajax_teacher_list.html           the script-rendered directory of 2025-2026 (the ajax endpoint holds the rows)
  cs.sjtu.edu.cn/jiaoshiml.html                          2025-2026 only (594 captures), the current directory
"""
D = "20160101", "20261231"

SLOTS = [
    {"dept": "CS", "slot": "CS faculty (Chinese list)", "kind": "main", "urls": [
        ("cs.sjtu.edu.cn/Faculty.aspx", "20160101", "20241231"),
        ("cs.sjtu.edu.cn/cse/Faculty.aspx", "20250101", "20261231"),
        ("cs.sjtu.edu.cn/active/ajax_teacher_list.html", "20250101", "20261231"),
    ]},
    {"dept": "CS", "slot": "CS faculty (English list)", "kind": "sub", "urls": [
        ("cs.sjtu.edu.cn/en/Faculty.aspx", "20160101", "20241231"),
    ]},
]

DEPT_CODES = {"CS": ["CS"]}


def relevant_slots(pi, slot_name, slot):
    return slot["dept"] in pi.get("departments", [])
