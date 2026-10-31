"""Builds ../stanford-pi-check.json (every quote verified by evid.ev)."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[3] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
from evid import ev, adv, save
OUT = str(P.HIERARCHY / 'chain-research-20261028/stanford-pi-check.json')
OA = "https://openalex.org/"
W = "https://web.archive.org/web/{}id_/https://profiles.stanford.edu/{}"
rows = []
def add(r): rows.append(r); save(OUT, rows)

# ---------------- Goldsmith
g = lambda ts: W.format(ts, "andrea-goldsmith")
wa = "https://wsl.stanford.edu/people/alumni"
add({"pi": "Andrea Goldsmith", "verdict": "pi",
  "reason": "Stanford Profiles list her as Postdoctoral Faculty Sponsor in every capture 2015-12 through 2021-01 and as Doctoral Dissertation Advisor (AC) of Tom Dean in 2019-11 and 2020-05 captures; she headed the Wireless Systems Lab (WSL), whose alumni page names PhD graduates in 2017 and 2019. Research (wireless communications/information theory, ML for communications) is a computing area; the census row already flags ee_cs cs=true (cs_share 0.92). The census 'no advising' result most likely came from reading only the current emerita profile, which no longer shows the advising sections.",
  "periods": [{"start": "1999", "end": "2020-08-31", "rank": "Professor of Electrical Engineering (Stephen Harris Professor from 2012)", "evidence": [
      ev("https://ee.stanford.edu/news/2020/apr/andrea-goldsmith-named-dean-engineering-princeton-university", "After 21 years as a professor of electrical engineering at Stanford, Andrea Goldsmith has been named dean of Princeton University's School of Engineering and Applied Science, effective September 1."),
      ev("https://wsl.stanford.edu/node/106", "has been named dean of Princeton University’s School of Engineering and Applied Science, effective September 1, 2020"),
      ev("https://pub.orcid.org/v3.0/0000-0001-5686-800X/employments", "Andrea Goldsmith School of Engineering Stephen Harris Professor in the School of Engineering 2012 2020 Stanford University"),
      ev("https://pub.orcid.org/v3.0/0000-0001-5686-800X/employments", "Andrea Goldsmith Arthur LeGrand Doty Professor of Electrical Engineering, Dean, School of Engineering & Applied Science 2020 Princeton University"),
      ev(g("20210115181935"), "Academic Appointments Professor Emeritus, Electrical Engineering", note="emerita at Stanford after leaving; not an active appointment")]}],
  "advisees": [
      adv(g("20191117222333"), "Tom Dean", "phd_dissertation_advisor_AC", [2019, 2020], "Doctoral Dissertation Advisor (AC) Tom Dean"),
      adv(wa, "Milind Rao", "phd", [None, 2019], "Milind Rao 2019 Amazon"),
      adv(wa, "Mainak Chowdhury", "phd", [None, 2017], "Mainak Chowdhury 2017 Stanford University"),
      adv(wa, "Alon Kipnis", "phd", [None, 2017], "Alon Kipnis 2017 Postdoctoral Scholar, Statistics, Stanford University"),
      adv(g("20160312101957"), "Mahnoosh Alizadeh", "postdoc_sponsor", [2016, 2016], "Postdoctoral Faculty Sponsor Mahnoosh Alizadeh , Jinyuan Chen , Nariman Farsad , Yonathan Morin"),
      adv(g("20160312101957"), "Jinyuan Chen", "postdoc_sponsor", [2016, 2016], "Postdoctoral Faculty Sponsor Mahnoosh Alizadeh , Jinyuan Chen , Nariman Farsad , Yonathan Morin"),
      adv(g("20170302005912"), "Nariman Farsad", "postdoc_sponsor", [2016, 2017], "Postdoctoral Faculty Sponsor Nariman Farsad , Felipe Gomez Cuba , Yonathan Morin"),
      adv(g("20170302005912"), "Felipe Gomez Cuba", "postdoc_sponsor", [2016, 2017], "Postdoctoral Faculty Sponsor Nariman Farsad , Felipe Gomez Cuba , Yonathan Morin"),
      adv(g("20170302005912"), "Yonathan Morin", "postdoc_sponsor", [2016, 2017], "Postdoctoral Faculty Sponsor Nariman Farsad , Felipe Gomez Cuba , Yonathan Morin"),
      adv(g("20181204143340"), "Michal Yemini", "postdoc_sponsor", [2018, 2020], "Postdoctoral Faculty Sponsor Michal Yemini"),
      adv(g("20191117222333"), "Ali Hashemi", "postdoc_sponsor", [2019, 2020], "Postdoctoral Faculty Sponsor Ali Hashemi , Anusha Lalitha , Michal Yemini"),
      adv(g("20191117222333"), "Anusha Lalitha", "postdoc_sponsor", [2019, 2020], "Postdoctoral Faculty Sponsor Ali Hashemi , Anusha Lalitha , Michal Yemini")],
  "openalex": [OA + "A5074116801"],
  "evidence": [ev(g("20161206122919"), "Academic Appointments Professor, Electrical Engineering"),
               ev("https://wsl.stanford.edu/people", "WSL Members Andrea Goldsmith The Stephen Harris Professor in the School of Engineering Professor of Electrical Engineering, Emerita"),
               ev("https://ee.stanford.edu/news/2020/apr/andrea-goldsmith-named-dean-engineering-princeton-university", "who has supervised 27 doctoral students and 23 postdoctoral scholars")],
  "notes": "Years for postdocs are the span of Profiles captures naming them, capped at the 2020-08-31 departure (the 2021-01 capture still lists Hashemi, Lalitha, Yemini under an emerita profile - treat as stale). WSL alumni years are PhD completion years. OpenAlex A5074116801 (953 works, ORCID 0000-0001-5686-800X) is the main profile; small name-match profiles (A5113852082, A5034944654, A5042560476, A5151205394; A5007214664 is 'Andrea E. Goldsmith') were not reviewed. princeton.edu news returned a bot challenge and was not used."})

# ---------------- Bailis
b = lambda ts: W.format(ts, "peter-bailis")
bh = "https://bailis.org/"
add({"pi": "Peter Bailis", "verdict": "pi",
  "reason": "As a CS assistant professor he is listed on Stanford Profiles as Doctoral Dissertation Advisor (AC) of Edward Gan, Sahaana Suri, Kai Sheng Tai, Daniel Kang and Doctoral Dissertation Co-Advisor (AC) of Peter Kraft (2019-11 and 2020-09 captures), and he led the Future Data Systems group / DAWN project. Data systems is a computing area. The census row's 'no advising' result reflects the current adjunct profile, which has no advising sections. The lab should be dated to the assistant-professor years; as an adjunct (2021 on) he co-advised students to completion (with Zaharia) but no Profiles advising role is shown.",
  "periods": [
     {"start": "2016-05-26", "end": "2020", "rank": "Assistant Professor of Computer Science", "evidence": [
        ev("https://web.archive.org/web/20160906145126id_/http://bailis.org/", "5/26/2016 Officially started at Stanford as an assistant professor of Computer Science!"),
        ev("https://web.archive.org/web/20160119112558id_/http://bailis.org/", "Peter Bailis will join Stanford Computer Science as an assistant professor in 2016."),
        ev(b("20200926093743"), "Academic Appointments Assistant Professor, Computer Science", note="last capture showing assistant professor"),
        ev("https://web.archive.org/web/20200729105832id_/http://bailis.org/", "Founder and CEO, Sisu Data peter@sisu.ai Assistant Professor, Stanford CS"),
        ev("https://web.archive.org/web/20201031235220id_/http://bailis.org/", "Before Sisu, I was an assistant professor of CS at Stanford", note="by 2020-10-31 he describes the assistant professorship in the past tense; no stated end date found")]},
     {"start": "2021", "end": None, "rank": "Adjunct Professor, Computer Science", "evidence": [
        ev(b("20210115182932"), "Peter Bailis Adjunct Professor, Computer Science", note="first capture showing adjunct; no stated start"),
        ev("https://profiles.stanford.edu/peter-bailis", "Peter Bailis Adjunct Professor, Program-Bailis, P.")]}],
  "advisees": [
     adv(b("20191117223641"), "Edward Gan", "phd_dissertation_advisor_AC", [None, 2020], "Doctoral Dissertation Advisor (AC) Edward Gan, Sahaana Suri, Kai Sheng Tai", completion_quote="Edward Gan (PhD 2020, software engineer at Databricks)"),
     adv(b("20200926093743"), "Sahaana Suri", "phd_dissertation_advisor_AC", [None, 2022], "Doctoral Dissertation Advisor (AC) Daniel Kang, Sahaana Suri, Kai Sheng Tai", completion_quote="Sahaana Suri (PhD 2022, stealth startup)"),
     adv(b("20200926093743"), "Kai Sheng Tai", "phd_dissertation_advisor_AC", [None, 2021], "Doctoral Dissertation Advisor (AC) Daniel Kang, Sahaana Suri, Kai Sheng Tai", completion_quote="Kai Sheng Tai (PhD 2021, research scientist at Facebook AI; w/ Greg Valiant )"),
     adv(b("20200926093743"), "Daniel Kang", "phd_dissertation_advisor_AC", [None, 2022], "Doctoral Dissertation Advisor (AC) Daniel Kang, Sahaana Suri, Kai Sheng Tai", completion_quote="Daniel Kang (PhD 2022, faculty at UIUC; w/ Matei Zaharia )"),
     adv(b("20200926093743"), "Peter Kraft", "phd_dissertation_coadvisor_AC", [None, None], "Doctoral Dissertation Co-Advisor (AC) Peter Kraft"),
     adv(bh, "Kexin Rong", "phd_coadvised_homepage", [None, 2021], "Kexin Rong (PhD 2021, faculty at Georgia Tech; w/ Phil Levis )"),
     adv(bh, "Cody Coleman", "phd_coadvised_homepage", [None, 2021], "Cody Coleman (PhD 2021, founder at Coactive AI; w/ Matei Zaharia )"),
     adv(bh, "Firas Abuzaid", "phd_coadvised_homepage", [None, 2022], "Firas Abuzaid (PhD 2022, founder at neo.tax; w/ Matei Zaharia )"),
     adv(bh, "Fiodar Kazhamiaka", "postdoc_homepage", [None, 2022], "Fiodar Kazhamiaka (postdoc 2022, researcher at Microsoft Research; w/ Matei Zaharia )")],
  "openalex": [OA + "A5002538469"],
  "evidence": [ev(b("20191117223641"), "Doctoral Dissertation Co-Advisor (AC) Peter Kraft"),
               ev("https://web.archive.org/web/20190425225232id_/https://profiles.stanford.edu/peter-bailis", "Peter's research in the Future Data Systems group focuses on the design and implementation of next-generation")],
  "notes": "Homepage-only advisees (Rong, Coleman, Abuzaid, Kazhamiaka) are co-advised per his own list but not shown as AC advisor on Profiles - include only if the homepage counts under the owner's rules (they are not 'Doctoral (Program)' or 'Reader'). The completion_quote fields are verbatim from https://bailis.org/ (live, sha in the capture db). CS department listings show him as Regular Faculty 2016-2020 and Adjunct 2021-2026, consistent with the Profiles captures. OpenAlex A5002538469 (163 works, ORCID 0000-0003-1166-7823 attached by OpenAlex; public ORCID record has no employments). Theses on purl.stanford.edu were not checked (SearchWorks is a bot wall)."})

# ---------------- Demszky
d = lambda ts: W.format(ts, "dorottya-demszky")
lab = "https://edunlp.stanford.edu/people"
add({"pi": "Dora Demszky", "verdict": "pi",
  "reason": "Stanford Profiles list her as Doctoral Dissertation Co-Advisor (AC) of Rose Wang (captures 2023-12 to 2025-01) and Postdoctoral Faculty Sponsor of Jim Malamut (2024-11 to 2026-06) and, live, Jeannette Garcia Coppersmith; she heads the EduNLP Lab, whose people page lists PhD students and postdocs. Research is NLP/ML for education, a computing area (CS courtesy appointment). The census row had profile_url null, which is why no advising was found: her Profiles slug is 'dorottya-demszky'.",
  "periods": [{"start": "2022-12 (first dated observation; no stated start found)", "end": None, "rank": "Assistant Professor, Graduate School of Education (by courtesy CS from 2023-12 observation)", "evidence": [
      ev(d("20220704035431"), "Dorottya Demszky Ph.D. Student in Linguistics, admitted Autumn 2017", note="still a PhD student in July 2022"),
      ev(d("20221203201351"), "Dora Demszky Assistant Professor (Subject to PhD) of Education Ph.D. Student in Linguistics, admitted Autumn 2017 Graduate School of Education"),
      ev(d("20230315002220"), "Academic Appointments Assistant Professor, Graduate School of Education"),
      ev(d("20231204174208"), "Academic Appointments Assistant Professor, Graduate School of Education Assistant Professor (By courtesy), Computer Science"),
      ev("https://pub.orcid.org/v3.0/0000-0002-6759-9367/employments", "Dorottya Demszky Graduate School of Education Assistant Professor Stanford University", note="ORCID employment has no start date")]}],
  "advisees": [
      adv(d("20231204174208"), "Rose Wang", "phd_dissertation_coadvisor_AC", [2023, 2025], "Doctoral Dissertation Co-Advisor (AC) Rose Wang"),
      adv(d("20241102151217"), "Jim Malamut", "postdoc_sponsor", [2024, 2026], "Postdoctoral Faculty Sponsor Jim Malamut"),
      adv("https://profiles.stanford.edu/dorottya-demszky", "Jeannette Garcia Coppersmith", "postdoc_sponsor", [2026, 2026], "Postdoctoral Faculty Sponsor Jeannette Garcia Coppersmith"),
      adv(lab, "Liliana Deonizio", "phd_lab_member", [2026, 2026], "Liliana Deonizio PhD Student"),
      adv(lab, "Anya Ma", "phd_lab_member", [2026, 2026], "Anya Ma PhD Student"),
      adv(lab, "Alex Nam", "phd_lab_member", [2026, 2026], "Alex Nam PhD Student"),
      adv(lab, "Lena Phalen", "phd_lab_member", [2026, 2026], "Lena Phalen PhD Student"),
      adv(lab, "Mei Tan", "phd_lab_member", [2026, 2026], "Mei Tan PhD Student"),
      adv(lab, "Chris Mah", "phd_lab_alumni", [None, None], "Chris Mah PhD Student"),
      adv(lab, "Tolúlọpẹ́ Ògúnrẹ̀mí", "phd_lab_alumni", [None, None], "Tolúlọpẹ́ Ògúnrẹ̀mí PhD Student")],
  "openalex": [OA + "A5052171928"],
  "evidence": [ev(lab, "Faculty Dora Demszky Faculty Staff Jeannette Garcia Coppersmith Postdoctoral Scholar"),
               ev("https://edunlp.stanford.edu/people/dora-demszky", "Dora Demszky Assistant Professor in Education Data Science, Assistant Professor (By courtesy) in Computer Science")],
  "notes": "Period start is the first dated Profiles capture showing the faculty title (2022-12-03); per the rules that proves 2022 (listing year) but is not a stated start. CS courtesy is first seen 2023-12-04 (CS department listings in the census start 2024). EduNLP lab-page students are undated (observed 2026-10-28) and may be co-advised or lab-affiliated rather than her dissertation advisees; Chris Mah and Ògúnrẹ̀mí are listed under Alumni as 'PhD Student'. OpenAlex A5052171928 (132 works, ORCID 0000-0002-6759-9367) is the main profile; A5129072461 ('Dora Demszky', 4 works) is a likely split but its works did not resolve in a filtered query and was not verified."})
print(len(rows))
