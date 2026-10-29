"""Builds ../newpi-review.json from captures.sqlite (every quote verified by evid.ev)."""
from evid import ev, adv, save
OUT = "/n/fs/resemble/cs-atlas/work/hierarchy/chain-research-20261028/newpi-review.json"
OA = "https://openalex.org/"
ORC = "https://pub.orcid.org/v3.0/{}/employments"
EECS = "https://www2.eecs.berkeley.edu/Faculty/Homepages/{}.html"
rows = []
def add(r): rows.append(r); save(OUT, rows)

# ---------------- Loianno
arp = "https://arplaboratory.github.io/people/"
L = [("Narek Harutyunyan", "phd", "Narek Harutyunyan EECS PhD"), ("JoonHo Lee", "phd", "JoonHo Lee EECS PhD"),
     ("Pratyaksh P. Rao", "phd", "Pratyaksh P. Rao EECS PhD"), ("Mrunal Sarvaiya", "phd", "Mrunal Sarvaiya EECS PhD"),
     ("Jonas Eschmann", "phd", "Jonas Eschmann EECS PhD"), ("Jaeyoung Lim", "postdoc", "Jaeyoung Lim EECS Postdoctoral Researcher"),
     ("Long Quang", "phd_nyu", "Long Quang ECE PhD (NYU)"), ("Manohari Goarin", "phd_nyu", "Manohari Goarin MAE PhD (NYU)"),
     ("Jiuhong Xiao", "phd_nyu", "Jiuhong Xiao ECE PhD (NYU)"), ("Yang Zhou", "phd_nyu", "Yang Zhou ECE PhD (NYU)"),
     ("Luca Morando", "postdoc_nyu", "Luca Morando ECE Postdoctoral Researcher (NYU)")]
add({"school": "berkeley", "pi": "Giuseppe Loianno",
     "openalex": [OA + "A5077485450"], "orcid": "https://orcid.org/0000-0002-3263-5401", "not_openalex": [],
     "period": {"start": "2025-07", "end": None, "evidence": [
        ev(ORC.format("0000-0002-3263-5401"), "Giuseppe Loianno 2025 07 University of California, Berkeley"),
        ev("https://www.tii.ae/team/prof-giuseppe-loianno", "Before joining UC Berkeley in 2025, he was an associate professor at NYU"),
        ev("https://arplaboratory.github.io/", "Aug 27, 2025 ARPL has moved to UC Berkeley!"),
        ev("https://vcresearch.berkeley.edu/node/29334", "Giuseppe Loianno Associate Professor Division of Electrical Engineering (EECS) Faculty Site Publications (Google Scholar) ORCID", note="the ORCID link on this Berkeley research-office profile points to orcid.org/0000-0002-3263-5401")]},
     "advisees": [adv(arp, n, r, [2026, 2026], q) for n, r, q in L],
     "notes": "Single OpenAlex profile A5077485450 (174 works; NYU 2018-2025, Penn 2014-2019, Naples 2011-2020, Berkeley 2025-26); works match ARPL coauthors throughout, no merge seen. ORCID record (employment UC Berkeley from 2025-07) and Berkeley vcresearch profile link the same ORCID. Only works from 2025-07 on are inside the Berkeley appointment; NYU-era (2018-2025) papers must not count. Lab people page (undated, observed 2026-10-28) mixes Berkeley EECS members with NYU members labeled '(NYU)'; roles *_nyu are NYU-enrolled and probably should not count as Berkeley lab students."})

# ---------------- Salahuddin
diss = "https://www2.eecs.berkeley.edu/Pubs/Dissertations/Faculty/salahuddin.html"
S = [("Pratik Brahma", 2025, "Accelerating Atomistic Simulations Using Neural Networks and Ising Computing Pratik Brahma [2025]"),
     ("Jong Ho Park", 2025, "Jong Ho Park [2025]"), ("Nirmaan Shanker", 2024, "Nirmaan Shanker [2024]"),
     ("Jason Cheng-Hsiang Hsu", 2023, "Jason Cheng-Hsiang Hsu [2023]"), ("Adi Jung", 2023, "Adi Jung [2023]"),
     ("Saavan Patel", 2023, "Saavan Patel [2023]"), ("Yu-Hung Liao", 2021, "Yu-Hung Liao [2021]"), ("Ava Tan", 2021, "Ava Tan [2021]"),
     ("Korok Chatterjee", 2018, "Korok Chatterjee [2018]"), ("Justin Wong", 2018, "Justin Wong [2018]"),
     ("Dominic Labanowski", 2017, "Dominic Labanowski [2017]"), ("Varun Mishra", 2017, "Varun Mishra [2017]")]
add({"school": "berkeley", "pi": "Sayeef Salahuddin",
     "openalex": [OA + "A5078295678"], "orcid": "https://orcid.org/0000-0002-0315-2208", "not_openalex": [],
     "period": {"start": "2008", "end": None, "evidence": [
        ev(EECS.format("salahuddin"), "He joined the faculty of Electrical Engineering and Computer Science at University of California, Berkeley in 2008.")]},
     "advisees": [adv(diss, n, "phd_dissertation", [y, y], q) for n, y, q in S],
     "notes": "Single OpenAlex profile A5078295678 (449 works; UC Berkeley/LBNL every year 2012-2026). ORCID 0000-0002-0315-2208 is the one OpenAlex attaches; the public ORCID record has no employment entries, so the ORCID is supported by OpenAlex only. Profile appears to have a few pre-2005 speech-enhancement papers (2002-2004) from someone else - outside the window, harmless. Appointment covers the whole 2016-2026 window."})

# ---------------- Sipahigil
team = "https://quantumdevices.berkeley.edu/team"
A = [("Lukasz Komza", "phd", None, "Lukasz Komza Physics"), ("Kadircan Godeneli", "phd", None, "Kadircan Godeneli EECS"),
     ("Hanbin Song", "phd", None, "Hanbin Song MSE"), ("Enrique Garcia", "phd", None, "Enrique Garcia EECS"),
     ("Darius Vera", "phd", None, "Darius Vera EECS"), ("Ahmet Oguz Sakin", "phd", None, "Ahmet Oguz Sakin EECS"),
     ("Tae Gyu Ahn", "phd", None, "Tae Gyu Ahn EECS"), ("Hanson Nguyen", "phd", None, "Hanson Nguyen EECS"),
     ("Nicholas Yama", "postdoc", None, "Postdocs Nicholas Yama"), ("Yuxiao Jiang", "postdoc", None, "Yuxiao Jiang Co-advisor: Feng Wang"),
     ("Yuan Zhan", "postdoc", None, "Yuan Zhan Tonghang Han"), ("Tonghang Han", "postdoc", None, "Tonghang Han Co-advisor: Feng Wang"),
     ("Mutasem Odeh", "phd", [2021, 2023], "Mutasem Odeh EECS 2021-2023 Apple Phonon-protected superconducting qubits"),
     ("Haoxin Zhou", "postdoc", [2023, 2026], "Haoxin Zhou 2023-2026"), ("Zihuai Zhang", "postdoc", [2022, 2026], "Zihuai Zhang 2022-2026"),
     ("Hong Qiao", "postdoc", [2026, 2026], "Hong Qiao 2026"), ("Mi Lei", "postdoc", [2024, 2026], "Mi Lei 2024-2026"),
     ("Leo Sementilli", "postdoc", [2025, 2026], "Leo Sementilli 2025-2026"), ("Niccolo Fiaschi", "postdoc", [2024, 2025], "Niccolo Fiaschi 2024-2025"),
     ("Xueyue (Sherry) Zhang", "postdoc", [2023, 2024], "Xueyue (Sherry) Zhang 2023-2024"), ("Polnop Samutpraphoot", "postdoc", [2021, 2022], "Polnop Samutpraphoot 2021-2022")]
add({"school": "berkeley", "pi": "Alp Sipahigil",
     "openalex": [OA + "A5064615305"], "orcid": "https://orcid.org/0000-0003-1469-5272", "not_openalex": [],
     "period": {"start": "2021-01-01", "end": None, "evidence": [
        ev(ORC.format("0000-0003-1469-5272"), "Alp Sipahigil Electrical Engineering and Computer Sciences and Physics Assistant Professor 2021 01 01 University of California, Berkeley"),
        ev(EECS.format("alp"), "Prior to joining Berkeley in 2021, he was an Institute for Quantum Information and Matter postdoctoral scholar at Caltech.")]},
     "advisees": [adv(team, n, r, y if y else [2026, 2026], q, **({} if y else {"years_basis": "current member on undated page observed 2026-10-28"})) for n, r, y, q in A],
     "notes": "Single OpenAlex profile A5064615305 (98 works; Harvard 2012-2018, Caltech 2018-2021, Berkeley/LBNL 2022-2026), clean. Self-asserted ORCID employment: UC Berkeley Assistant Professor from 2021-01-01. Pre-2021 Harvard/Caltech papers must not count. Team page gives tenure years for alumni; current members are undated."})

# ---------------- Meng
mh = "https://guanghanmeng.com/"; mt = "https://guanghanmeng.com/team"
add({"school": "berkeley", "pi": "Guanghan Meng",
     "openalex": [OA + "A5075371622"], "orcid": "https://orcid.org/0000-0001-7620-2205", "not_openalex": [],
     "period": {"start": "2025-01-01", "end": None, "evidence": [
        ev(mh, "2025.01 Guanghan became an Assistant Professor on Jan. 1st, 2025! This is the first day of VOILA!"),
        ev(ORC.format("0000-0001-7620-2205"), "Guanghan Meng Assistant Professor 2025 University of California, Berkeley"),
        ev("https://web.archive.org/web/20240417062453id_/https://guanghanmeng.com/", "I am a postdoctoral scholar at University of California Berkeley, working with Professor Laura Waller", note="pre-faculty status (postdoc) in April 2024")]},
     "advisees": [
        adv(mh, "Xue Dong", "postdoc", [2025, 2026], "2025.08 Welcome to Dr. Xue Dong who joined VOILA as a postdoc! Welcome to our two PhD students: Yuanlong and Vasilisa!"),
        adv(mt, "Yuanlong Zhao", "phd", [2025, 2026], "yuanlong_zhao [at] berkeley [dot] edu PhD Student, Vision Science", start_basis="homepage news 2025.08 'Welcome to our two PhD students: Yuanlong and Vasilisa!'"),
        adv(mt, "Vasilisa Sergeyevna Ponomarenko", "phd", [2025, 2026], "ponoma [at] berkeley [dot] edu PhD Student, EECS", start_basis="homepage news 2025.08"),
        adv(mt, "William Xu", "masters_coadvised", [2024, 2025], "William Xu, EECS Master (co-advised), 2024 - 2025")],
     "notes": "Single OpenAlex profile A5075371622 (30 works; SJTU 2016, Janelia/HHMI 2018-19, Berkeley 2018-2026), clean. She was a Berkeley PhD student (PhD 2021, Na Ji lab) and then Berkeley postdoc (Waller lab) before the faculty start, so Berkeley-affiliated works before 2025-01-01 are student/postdoc era and must not count. William Xu is a co-advised master's student (not PhD) - include only if the atlas counts master's advisees."})

# ---------------- Siddiqi
qnl = "https://qnl.berkeley.edu/group-members"
Q = [("Akel Hashim", "phd", "Akel Hashim Graduate Student"), ("Marie Lu", "phd", "Marie Lu Graduate Student"),
     ("Trevor Chistolini", "phd", "Trevor Chistolini Graduate Student"), ("Brad Mitchell", "phd", "Brad Mitchell Graduate Student"),
     ("John Mark Kreikebaum", "phd", "John Mark Kreikebaum graduate student"), ("William Livingston", "phd", "William Livingston Graduate student"),
     ("Larry Chen", "phd", "Larry Chen Graduate Student"), ("Ravi Naik", "postdoc", "Dr. Ravi Naik Post-Doctoral Researcher"),
     ("Gerwin Koolstra", "postdoc", "Dr. Gerwin Koolstra Post-doctoral Researcher"), ("Kasra Nowrouzi", "postdoc", "Dr. Kasra Nowrouzi Post-doctoral Researcher"),
     ("Alexis Morvan", "postdoc", "Dr. Alexis Morvan Post-doctoral Researcher"), ("Jean-Loup Ville", "postdoc", "Dr. Jean-Loup Ville Post-Doctoral Researcher"),
     ("Archan Banerjee", "postdoc", "Dr. Archan Banerjee Post-doctoral Researcher"), ("Machiel Blok", "postdoc", "Dr. Machiel Blok Post-doctoral Researcher"),
     ("Jie Luo", "postdoc", "Dr. Jie Luo Post-doctoral Researcher")]
add({"school": "berkeley", "pi": "Irfan Siddiqi",
     "openalex": [OA + "A5000947887", OA + "A5121819049"], "orcid": "https://orcid.org/0000-0003-2200-1090",
     "not_openalex": [OA + "A5088079668", OA + "A5013806472", OA + "A5068706736"],
     "period": {"start": "2006", "end": None, "evidence": [
        ev("https://physics.berkeley.edu/people/faculty/irfan-siddiqi", "Irfan joined the faculty at the physics department at the University of California, Berkeley in the summer of 2006. He is also a professor of Electrical Engineering and Computer Science"),
        ev(ORC.format("0000-0003-2200-1090"), "Irfan Siddiqi Physics Professor 2015 06 30 University of California Berkeley", note="rank of full Professor from 2015-06-30")]},
     "advisees": [adv(qnl, n, r, None, q, years_basis="QNL group page is undated (footer 'Copyright 2015'); several listed people (e.g. Akel Hashim, Larry Chen) coauthor 2024-2026 QNL papers, others may be stale") for n, r, q in Q],
     "notes": "A5000947887 is the main profile (412 works; ORCID 0000-0003-2200-1090). A5121819049 (9 works 2024-2026, LBNL/Berkeley, coauthors Akel Hashim, Noah Goss, Trevor Chistolini) is a split of the same person. The three not_openalex ids are other Irfan Siddiqis (1 work each, unrelated fields). Berkeley Physics appointment since summer 2006 covers the whole window; the EECS joint professorship has no stated start (first EECS listing seen 2022) - if the atlas requires the EECS appointment specifically, only 2022+ is proven. The physics page also says he was Department Chair 2023-2026. Advisee years are not proven by the undated QNL page; prefer dissertations if the parent needs dated students."})

# ---------------- Karandikar
sg = "https://sagark.org/group/"
K = [("Angela Cui", "phd", "Ph.D. Students Angela Cui"), ("Raghav Gupta", "phd_coadvised", "Raghav Gupta ( Web ; LinkedIn ), co-advised with Borivoje Nikolic"),
     ("Ferran Hermida-Rivera", "phd", "Ferran Hermida-Rivera ( Web ; LinkedIn )"), ("Ella Schwarz", "phd_coadvised", "Ella Schwarz ( LinkedIn ), co-advised with Borivoje Nikolic"),
     ("Jack Toubes", "phd", "Jack Toubes ( Web ; LinkedIn ) NSF GRFP Recipient"), ("Chengyi (Lux) Zhang", "phd_coadvised", "Chengyi (Lux) Zhang ( LinkedIn ), co-advised with Sophia Shao")]
add({"school": "berkeley", "pi": "Sagar Karandikar",
     "openalex": [OA + "A5017667683"], "orcid": "https://orcid.org/0000-0003-3145-776X", "not_openalex": [],
     "period": {"start": "2025-07", "end": None, "evidence": [
        ev(ORC.format("0000-0003-3145-776X"), "Sagar Karandikar Electrical Engineering and Computer Sciences Assistant Professor 2025 07 University of California, Berkeley"),
        ev("https://web.archive.org/web/20240913092044id_/https://sagark.org/", "I am an incoming Assistant Professor in the Electrical Engineering and Computer Sciences department at UC Berkeley , starting in July 2025. Currently, I am a Visiting Faculty Researcher at Google"),
        ev("https://web.archive.org/web/20240809064306id_/https://sagark.org/", "I am an incoming Assistant Professor in the Electrical Engineering and Computer Sciences department at UC Berkeley , starting in July 2025. Currently, I am wrapping up my Ph.D. in Computer Architecture at UC Berkeley, advised by Krste Asanović"),
        ev("https://web.archive.org/web/20250814114829id_/https://sagark.org/", "I am an Assistant Professor in the Electrical Engineering and Computer Sciences (EECS) department at UC Berkeley"),
        ev(EECS.format("skarandikar"), "Education 2024, Ph.D., Computer Science, UC Berkeley", note="PhD conferred 2024; all earlier Berkeley work is student-era")]},
     "advisees": [adv(sg, n, r, [2026, 2026], q, years_basis="current group page observed 2026-10-28; group cannot predate 2025-07") for n, r, q in K],
     "notes": "Single OpenAlex profile A5017667683 (31 works, Berkeley 2013-2026, Google 2023), clean. Faculty start is July 2025 (ORCID + his own site, which through 2025-07-01 still said 'incoming ... starting in July 2025' and that he was a Visiting Faculty Researcher at Google). CONFLICT: the EECS faculty list captured 2024-11-13 already shows him as 'Acting Assistant Professor'; under the same-year-listing rule that would admit 2024, but his own contemporaneous site says he was then at Google and not yet started - recommend not admitting 2024 papers (they are PhD/Google-era). Only works dated 2025-07 onward should count."})

# ---------------- Song Mei
sm = "https://www.stat.berkeley.edu/~songmei/group.html"
M = [("Kazusato Oko", "phd", [2026, 2026], "Kazusato Oko (EECS PhD)"),
     ("Ruiqi Zhang", "phd_coadvised", [2026, 2026], "Ruiqi Zhang (Stats PhD; Co-advised with Peter Bartlett)"),
     ("Tianyu Guo", "phd_coadvised", [2026, 2026], "Tianyu Guo (Stats PhD; Co-advised with Michael Jordan)"),
     ("Licong Lin", "phd_coadvised", [2026, 2026], "Licong Lin (Stats PhD; Co-advised with Peter Bartlett)"),
     ("Taejoo Ahn", "phd", [None, 2024], "Taejoo Ahn (- 2024; Former Stats PhD; IMC trading)"),
     ("Nikhil Ghosh", "phd_coadvised", [None, 2024], "Nikhil Ghosh (- 2024; Former Stats PhD; Co-advised with Bin Yu; Postdoc at Flatiron institute)"),
     ("Michael Celentano", "postdoc_mentee", [None, 2024], "Michael Celentano (- 2024; Former Berkeley Postdoctoral Miller Fellow; OpenAI)")]
add({"school": "berkeley", "pi": "Song Mei",
     "openalex": [OA + "A5114338138", OA + "A5137196583", OA + "A5139872592"], "orcid": None,
     "not_openalex": [OA + x for x in ["A5102849853", "A5086274249", "A5101792370", "A5021909041", "A5100941475", "A5101066494", "A5100939797"]],
     "period": {"start": "2020 (Fall)", "end": None, "evidence": [
        ev("https://web.archive.org/web/20210418110834id_/https://stat.berkeley.edu/~songmei/", "I finished my Ph.D. at Stanford in June of 2020! In Fall of 2020, I am joining the Department of Statistics at UC Berkeley as an assistant professor. (June, 2020)"),
        ev("https://web.archive.org/web/20210418110834id_/https://stat.berkeley.edu/~songmei/", "I am an Assistant Professor in the Department of Statistics at UC Berkeley. In Spring 2021, I am teaching"),
        ev("https://www.stat.berkeley.edu/~songmei/", "I am an Associate Professor in the Department of Statistics and the Department of Electrical Engineering and Computer Sciences at UC Berkeley. In June 2020, I received my Ph. D. from Stanford")]},
     "advisees": [adv(sm, n, r, y, q) for n, r, y, q in M],
     "notes": "OpenAlex has NO clean main profile for this Song Mei. Of 94 works OpenAlex returns for raw name 'Song Mei' at Berkeley/Stanford, 36 have no author id, and the rest are scattered across merged profiles of other people named Mei Song/Song Mei: A5102849853 (medical researcher, Shanghai; it is in pis.json oaAuthorIds and must be dropped), A5086274249 (BUPT telecom researcher + 8 of his 2023-2025 ML papers), A5101792370 (Mei Na Song, BUPT; 5 of his Stanford/Berkeley papers), A5021909041 (HIV researcher), A5100941475 (pharma chemist), A5101066494 (BIT/Nanjing chemist), A5100939797 (various Chinese institutions). The three ids listed under openalex are single-work Berkeley profiles that are clearly him (transformer/LLM theory with Tianyu Guo, Jiantao Jiao). Recommend identity by DBLP person 93/3618 title/DOI matching at the work level rather than by author id. No public ORCID found (ORCID expanded search given-names Song + family-name Mei + Berkeley: 0 hits). Faculty start Fall 2020 (Assistant Professor in Statistics; EECS lists him 'Below The Line Assistant Professor'); Stanford PhD-era papers (to June 2020) must not count. Michael Celentano is listed as a 'Former Mentee' postdoc (Miller Fellow) - not formal sponsorship; Druv Pai, Yuhang Cai, Jingfeng Wu are collaborators advised by others and were excluded."})

# ---------------- Goenka (Princeton)
gp = "https://web.archive.org/web/20251102130745id_/https://ece.princeton.edu/people/sneha-d-goenka"
add({"school": "princeton", "pi": "Sneha Goenka",
     "openalex": [OA + "A5047804975"], "orcid": "https://orcid.org/0000-0002-1716-7769", "not_openalex": [OA + "A5159710641"],
     "period": {"start": "2025-01", "end": None, "evidence": [
        ev("https://web.archive.org/web/20251102082415id_/https://ece.princeton.edu/news/sneha-d-goenka-named-innovator-year-mit-technology-review", "Goenka joined Princeton in January 2025."),
        ev("https://web.archive.org/web/20241206085626id_/https://www.snehagoenka.com/", "I am thrilled to announce that starting Jan 2025, I will be joining Princeton University as a tenure-track Assistant Professor in the ECE department!"),
        ev(ORC.format("0000-0002-1716-7769"), "Sneha D. Goenka Electrical and Computer Engineering Assistant Professor 2025 01 Princeton University"),
        ev(ORC.format("0000-0002-1716-7769"), "Sneha D. Goenka School of Medicine Postdoctoral Researcher 2024 04 2025 01 Stanford University", note="pre-Princeton postdoc, ends 2025-01")]},
     "advisees": [
        adv("https://web.archive.org/web/20250418031157id_/https://ece.princeton.edu/people/yucan-wu", "Yucan Wu", "phd", [2025, 2026], "Yucan Wu Email [email protected] Adviser Sneha D. Goenka Bio/Description Cohort Year: 2022",
            also=[ev("https://web.archive.org/web/20250418043051id_/https://ece.princeton.edu/people/sneha-d-goenka", "Advisee(s): Yucan Wu"),
                  ev(gp, "Advisee(s): Yucan Wu"),
                  ev("https://web.archive.org/web/20260213235724id_/https://ece.princeton.edu/people/yucan-wu", "Adviser Sneha Goenka Bio/Description Cohort Year: 2022"),
                  ev("https://web.archive.org/web/20241213205637id_/https://ece.princeton.edu/people/yucan-wu", "Yucan Wu Email [email protected] Adviser David August Bio/Description Cohort Year: 2022", note="before Goenka arrived he/she was advised by David August")],
            openalex=[OA + "A5108963894"])],
     "notes": "Single OpenAlex profile A5047804975 (15 works; Stanford 2019-2026, Princeton 2026) with ORCID 0000-0002-1716-7769 (self-asserted employment: Princeton ECE Assistant Professor from 2025-01; Stanford Medicine postdoc 2024-04 to 2025-01). A5159710641 is a gynecology author at Chirayu Medical College. One named PhD advisee: Yucan Wu (ECE PhD cohort 2022), who switched from David August (Dec 2024 capture) to Goenka (Apr 2025 onward); joint 2026 paper 'Pangenome IR' (Goenka, Wu) is a lab paper candidate; Yucan Wu's OpenAlex id at Princeton is A5108963894. No group page exists on snehagoenka.com (pages: Home, Awards, News, Talks, Teaching, Apply) and no postdocs are named anywhere found. ECE pages read only through Wayback captures (live ece.princeton.edu not fetched)."})
print(len(rows), "rows written")
