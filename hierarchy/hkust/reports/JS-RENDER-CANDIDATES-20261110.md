# HKUST pages to try with a Selenium render when tools/js_render_capture.py lands (2026-11-10)

Owner rule 10:45 EST: JS-rendered pages get a render attempt before being recorded unreadable or blocked; robots and challenge rules still apply. These are CANDIDATES from the register checks (static fetch failed or live host unreadable); whether each is a JS shell is not yet verified.

| PI | check | URL | static result |
|---|---|---|---|
| Xiaofang ZHOU 周曉方 | prior_labpage_pass_2026-10-22 | https://sites.google.com/view/xiaofang-zhou | recorded_lab_site |
| Xiaofang ZHOU 周曉方 | prior_labpage_pass_2026-10-22 | https://sites.google.com/view/xiaofang-zhou/home/research-research-students | recorded_people_page |
| Xiaofang ZHOU 周曉方 | pubs_link_not_used_by_prior_pass | https://sites.google.com/view/xiaofang-zhou/home/publications-home | ok |
| Song GUO 郭嵩 | school_profile | javascript:msend('songguo') | unreachable |
| Lei CHEN 陳雷 | school_profile | javascript:msend('leichen') | unreachable |
| Yike GUO 郭毅可 | school_profile | javascript:msend('yikeguo','ust.hk') | unreachable |
| Kai CHEN 陳凱 | school_profile | javascript:msend('kaichen') | unreachable |
| Dan XU 徐旦 | school_profile | javascript:msend('danxu') | unreachable |
| Long CHEN 陳隆 | school_profile | javascript:msend('longchen') | unreachable |
| Yi-Kuen Lee | department_listing | https://www.mae.ust.hk/en/people/faculty | ok_wayback |
| Yi-Kuen Lee | department_listing | https://www.mae.ust.hk/people/faculty.html? | ok_wayback |
| Yi-Kuen Lee | school_profile | http://www.mae.ust.hk:80/people/faculty_details.html?uid=397b8276-b75e-11e0-9e13-001cc47a7474 | ok_wayback |
| Kar Yan Tam | department_listing | https://isom.hkust.edu.hk/faculty-and-staff/directory | ok_wayback |
| Ajay Joneja | wayback_capture | https://web.archive.org/web/20260412093617id_/https://ieda.ust.hk/dfaculty/ajay/ | ok_wayback |
| Jian-Feng Cai | wayback_capture | https://web.archive.org/web/20260208024902id_/https://www.math.hkust.edu.hk/~jfcai/ | ok_wayback |
| Jian-Feng Cai | wayback_capture | https://web.archive.org/web/20260824140541id_/https://www.math.hkust.edu.hk/~jfcai/ | ok_wayback |

Also: ECE people listings (ece.ust.hk people_list: the person rows are embedded JSON, read statically by unit_listing_alias_links; no render needed unless that changes), and the 36 labs whose audited site has `no_people_section` (the static page named no members; some may render members client-side). Hongbo Fu: hongbofu.people.ust.hk was read statically (sha c2ba64526c3f...); his blocker is robots on facultyprofiles.hkust.edu.hk, which a render does not lift.
