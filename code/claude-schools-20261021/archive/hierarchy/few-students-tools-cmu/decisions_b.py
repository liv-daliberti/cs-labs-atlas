"""Worker B decisions (CMU few-students investigation, 2026-10-21/22): Benson, Chi, Ghani, Joshi, Kanade, Ann Lee,
Tai-Sing Lee, Rowe, Saad, Shaw, Wahby, Zanette, Hui Zhang. See dhelp.py for the spec format."""
from dhelp import Q, SE, ST, WB

D = {}
FS = "https://api.figshare.com/v2/articles/"


def KH(art, author, adv_prefix):
    """KiltHub (figshare API JSON) thesis record: span from the author's full_name to the Advisor(s) value."""
    return SE(FS + str(art), '"full_name": "' + author + '"', '"name": "Advisor(s)", "value": "' + adv_prefix,
              raw=True, long=True)


# ---------------------------------------------------------------------------------------------- Feras Saad
SA = "https://www.cs.cmu.edu/~fsaad/"
D["Feras Saad"] = dict(
    students=[
        ST("Wonyeol Lee", "postdoc", [2023, 2024],
           Q(SA, "Alumni Dr. Wonyeol Lee Postdoctoral Associate, 2023–2024")),
        ST("Jesse Michel", "other", [2024, 2024],
           Q(SA, "Jesse Michel Visiting Graduate Student, 2024 Massachusetts Institute of Technology"),
           note="Visiting graduate student from MIT hosted in the lab in 2024."),
    ],
    lab_note=("Probabilistic Computing Systems Lab, founded 2023 when he joined CSD; homepage lists 2 current graduate "
              "students (both already held) and 2 alumni (a postdoc and a visiting student)."),
    notes=("Homepage 'Probabilistic Computing Systems Lab' section is the only roster; CSD profile Advisees = Gaurav Arya, "
           "Thomas Draper (already held). No KiltHub/SCS thesis chaired by him yet (lab founded 2023)."),
)

# ---------------------------------------------------------------------------------------------- Andrea Zanette
ZA = "https://azanette.com/"
ZH = "Current PhD Students and Close Collaborators"
D["Andrea Zanette"] = dict(
    students=[
        ST("Zhaoyi Zhou", "phd", None, SE(ZA, "Daman Arora Zhaoyi Zhou", "Andy Zhou", after=ZH), must=["Zhaoyi Zhou"]),
        ST("Andy Zhou", "phd", None, SE(ZA, "Andy Zhou (on leave", "co-founded Intology )", after=ZH),
           note="Listed as current PhD student, on leave (co-founded Intology)."),
        ST("Guanning Zeng", "phd", None, Q(ZA, "Guanning Zeng (Intern —> PhD at CMU)"),
           note="Also listed under current PhD students; former intern who joined the CMU PhD program."),
        ST("Yuda Song", "phd", None, Q(ZA, "Yuda Song (primary advisors Aarti Singh and J. Andrew Bagnell)"),
           note="Listed under 'Current PhD Students and Close Collaborators' with other primary advisors; secondary advisee/collaborator."),
        ST("Fahim Tajwar", "phd", None, Q(ZA, "Fahim Tajwar (primary advisors Ruslan Salakhutdinov and Jeff Schneider)"),
           note="Listed under 'Current PhD Students and Close Collaborators' with other primary advisors; secondary advisee/collaborator."),
        ST("Tong Yang", "phd", [2023, None], Q(ZA, "Tong Yang (PhD, primary advisor Yuejie Chi )"),
           note="CMU ECE PhD co-advised with Yuejie Chi (Chi's group page: 2023-current, co-advised with Andrea Zanette)."),
    ],
    lab_note=("New lab, founded Fall 2024 (CMU ECE, courtesy MLD); homepage lists 7 current PhD students/close "
              "collaborators (4 with other primary advisors) plus former interns."),
    notes=("Source: homepage 'Current PhD Students and Close Collaborators' / 'Former Students and Collaborators'. "
           "Former MS students Anmol Agarwal and Hanshi Sun are listed without an institution and were left out "
           "(no source puts them at CMU); remote interns, Berkeley PhDs (Ruiqi Zhang, Yifei Zhou), a Princeton postdoc "
           "(Ming Yin) and CMU RI PhD collaborator Gokul Swamy (listed as collaborator, other advisors) are out. "
           "No KiltHub or SCS thesis yet (lab founded 2024)."),
)

# ---------------------------------------------------------------------------------------------- Gauri Joshi
GJ = "https://www.andrew.cmu.edu/user/gaurij/Group.html"
D["Gauri Joshi"] = dict(
    students=[
        ST("Akash Dhasade", "postdoc", [2024, None], Q(GJ, "Current Group Members Akash Dhasade Post-doctoral Scholar"),
           note="Also a 2024 summer intern of the lab."),
        ST("Neharika Jali", "phd", None, Q(GJ, "Neharika Jali PhD Student, ECE")),
        ST("Baris Askin", "phd", None, Q(GJ, "Baris Askin PhD Student, ECE co-advised by Carlee Joe-Wong")),
        ST("Arian Raje", "phd", None, Q(GJ, "Arian Raje PhD Student, ECE")),
        ST("Anupam Nayak", "phd", None, Q(GJ, "Anupam Nayak PhD Student, ECE")),
        ST("Shivam Patel", "phd", None, Q(GJ, "Shivam Patel PhD Student, ECE")),
        ST("He Wang", "phd", [2022, None], Q(GJ, "He Wang PhD Student, ECE co-advised by Yuejie Chi")),
        ST("Susana Marques", "phd", None, Q(GJ, "Susana Marques PhD Student, CMU Portugal co-advised by Fabio Coelho")),
        ST("Akaash Parthasarathy", "masters", None, Q(GJ, "Akaash Parthasarathy MS Student, CMU MLD")),
        ST("Anirudh Dash", "masters", None, Q(GJ, "Anirudh Dash MS Student, CMU ECE")),
        ST("Pranay Sharma", "postdoc", [2021, 2024], Q(GJ, "Post-Doc Pranay Sharma , 2021-2024")),
        ST("Jiin Woo", "phd", [None, 2026], Q(GJ, "Jiin Woo (co-advised by Yuejie Chi ), PhD 2026")),
        ST("Divyansh Jhunjhunwala", "phd", [None, 2025], Q(GJ, "Divyansh Jhunjhunwala , PhD 2025"),
           note="KiltHub dissertation 2025 (figshare 30128995), Advisor(s): Gauri Joshi."),
        ST("Tuhinangshu Choudhury", "phd", [None, 2024], Q(GJ, "Tuhinangshu Choudhury (co-advised by Weina Wang ), PhD 2024")),
        ST("Yae Jee Cho", "phd", [None, 2024], Q(GJ, "Yae Jee Cho , PhD 2024"),
           note="KiltHub dissertation 2024 (figshare 25922326), Advisor(s): Gauri Joshi."),
        ST("Samarth Gupta", "phd", [None, 2022], Q(GJ, "Samarth Gupta (co-advised by Osman Yaǧan ), PhD 2022"),
           note="KiltHub dissertation 2022 (figshare 21865533), Advisor(s): Gauri Joshi, Osman Yağan."),
        ST("Jianyu Wang", "phd", [None, 2022], Q(GJ, "Jianyu Wang , PhD 2022"),
           note="KiltHub dissertation 2022 (figshare 22144505), Advisor(s): Gauri Joshi."),
        ST("Ankur Mallick", "phd", [None, 2022], Q(GJ, "Ankur Mallick , PhD 2022"),
           note="KiltHub dissertation 2022 (figshare 22091651), Advisor(s): Gauri Joshi."),
        ST("Ahmet Inci", "phd", [None, 2022], Q(GJ, "Ahmet Inci (co-advised by Diana Marculescu ), PhD 2022")),
        ST("Ting-Wu (Rudy) Chin", "phd", [None, 2021], Q(GJ, "Ting-Wu (Rudy) Chin (co-advised by Diana Marculescu ), PhD 2021")),
        ST("Andrea Vigano", "masters", [None, 2025], Q(GJ, "Andrea Vigano , CMU ECE M.S. 2025")),
        ST("Siddharth Shah", "masters", [None, 2025], Q(GJ, "Siddharth Shah , CMU ECE M.S. 2025")),
        ST("Siddharth Ambekar", "masters", [None, 2024], Q(GJ, "Siddharth Ambekar , CMU ECE M.S. 2024")),
        ST("Eshika Pathak", "masters", [None, 2024], Q(GJ, "Eshika Pathak , CMU ECE M.S. 2024")),
        ST("Jiarui Li", "masters", [None, 2024], Q(GJ, "Jiarui Li , CMU ECE M.S. 2024")),
        ST("Rohan Panda", "masters", [None, 2022], Q(GJ, "Rohan Panda , CMU ECE M.S. 2022")),
        ST("Aushim Nagarkatti", "masters", [None, 2022], Q(GJ, "Aushim Nagarkatti , CMU ECE M.S. 2022")),
        ST("Zhiyuan Zhao", "masters", [None, 2021], Q(GJ, "Zhiyuan Zhao , CMU ECE M.S. 2021")),
        ST("Advait Gadhikar", "masters", [None, 2020], Q(GJ, "Advait Gadhikar , CMU ECE M.S. 2020")),
        ST("Shreyas Chaudhari", "masters", [None, 2020], Q(GJ, "Shreyas Chaudhari , CMU ECE M.S. Dec 2020")),
        ST("Chaitanya Dwivedi", "masters", [None, 2020], Q(GJ, "Chaitanya Dwivedi , CMU ECE M.S. June 2020")),
        ST("Hao Liang", "masters", [None, 2020], Q(GJ, "Hao Liang , CMU ECE M.S. June 2020")),
        ST("Zhouyi Yang", "masters", [None, 2020], Q(GJ, "Zhouyi Yang , CMU ECE M.S. June 2020")),
        ST("Sai Bhargav Yalamanchi", "masters", [None, 2018], Q(GJ, "Sai Bhargav Yalamanchi , CMU ECE M.S. Dec 2018")),
        ST("Souptik Sen", "masters", [None, 2018], Q(GJ, "Souptik Sen , CMU INI M.S. Jun 2018")),
        ST("Mani Swetha Mandava", "masters", [None, 2018], Q(GJ, "Mani Swetha Mandava , CMU ECE M.S. Dec 2018")),
        ST("Malhar Chaudhari", "masters", [None, 2017], Q(GJ, "Malhar Chaudhari , CMU ECE M.S. Dec 2017")),
        ST("Tarun Chiruvolu", "undergraduate", [None, 2024], Q(GJ, "Tarun Chiruvolu , CMU SCS, B.S. June 2024")),
        ST("Sophie Smith", "undergraduate", [None, 2021], Q(GJ, "Sophie Smith , CMU SCS, B.S+M.S. Dec 2021")),
        ST("Dhruva Kaushal", "undergraduate", [None, 2019], Q(GJ, "Dhruva Kaushal , CMU ECE, Integrated B.S. and M.S. Dec 2019")),
        ST("Subhojyoti Mukherjee", "other", [2019, 2019], Q(GJ, "Subhojyoti Mukherjee , 2019 → PhD student at Wisconsin-Madison"),
           note="Summer intern of the lab in 2019."),
    ],
    lab_note=("Optimization, Probability and Learning (OPAL) Lab, CMU ECE since Fall 2017; group page lists 10 current "
              "members (1 postdoc, 7 PhD, 2 MS) and ~30 alumni (PhD, MS, undergraduate, postdoc, interns)."),
    notes=("Source: OPAL Lab group page (andrew.cmu.edu/user/gaurij/Group.html); five PhD alumni also have KiltHub "
           "dissertations naming her as advisor. Sanghamitra Dutta (2017 intern 'at IBM Research', before she joined CMU) "
           "is out. Shuli Jiang (PhD 2025) already held."),
)

# ---------------------------------------------------------------------------------------------- Ann Lee
AL = "https://www.stat.cmu.edu/~annlee/"
D["Ann Lee"] = dict(
    students=[
        ST("James Carzon", "phd", None, Q(AL, "Current PhD Students James Carzon")),
        ST("Elizabeth Cucuzella", "phd", None, Q(AL, "Current PhD Students James Carzon Elizabeth Cucuzella")),
        ST("Joshua D. Ingram", "phd", None, Q(AL, "Elizabeth Cucuzella Joshua D. Ingram PhD Graduates")),
        ST("Luca Masserano", "phd", [None, 2025],
           Q(AL, "Luca Masserano – PhD May 2025, Department of Statistics & Data Science and the Machine Learning Department, CMU"),
           note="KiltHub dissertation 2025 (figshare 29169902), Advisor(s): Ann B. Lee, Barnabas Poczos."),
        ST("David Zhao", "phd", [None, 2023],
           Q(AL, "David Zhao – PhD May 2023, Department of Statistics & Data Science and the Machine Learning Department, CMU"),
           note="KiltHub dissertation 2023 (figshare 22776827), Advisor(s): Ann B. Lee."),
        ST("Trey McNeely", "phd", [None, 2022], Q(AL, "Trey (Tria) McNeely – PhD June 2022, Department of Statistics & Data Science, CMU"),
           must=["McNeely"], note="KiltHub dissertation 2022 (figshare 21133555) by Irwin H. McNeely, III, Advisor(s): Ann B. Lee."),
        ST("Niccolò Dalmasso", "phd", [None, 2021], Q(AL, "Niccolò (Nic) Dalmasso – PhD May 2021, Department of Statistics & Data Science, CMU"),
           must=["Dalmasso"], note="KiltHub dissertation 2021 (figshare 15069954), Advisor(s): Ann Lee."),
        ST("Taylor Pospisil", "phd", [None, 2019], Q(AL, "Taylor Pospisil – PhD May 2019, Department of Statistics & Data Science, CMU")),
    ],
    lab_note=("STAMPS research center (co-directed with Mikael Kuusela); homepage 'Group' section lists 3 current PhD "
              "students and PhD graduates ('only listing my main thesis advisees')."),
    notes=("Source: homepage Group section; KiltHub dissertations confirm Masserano, Zhao, McNeely, Dalmasso. "
           "Graduates before 2016 (Izbicki 2014 and earlier) are out. Luca Masserano is already held (new source added)."),
)

# ---------------------------------------------------------------------------------------------- Yuejie Chi
YC = "https://yuejiechi.github.io/group.html"
D["Yuejie Chi"] = dict(
    students=[
        ST("He Wang", "phd", [2022, None], Q(YC, "He Wang Ph.D. Candidate (2022-current, CMU ECE, co-advised with Gauri Joshi)")),
        ST("Tong Yang", "phd", [2023, None], Q(YC, "Tong Yang Ph.D. Candidate (2023-current, CMU ECE, co-advised with Andrea Zanette)")),
        ST("Timofey Efimov", "phd", [2023, None],
           Q(YC, "Timofey Efimov Ph.D. Candidate (2023-current, CMU ECE, co-advised with Aswin Sankaranarayanan)")),
        ST("Xingyu Xu", "phd", [None, 2026], Q(YC, "Xingyu Xu , Ph.D. 2026 (co-advised with Giulia Fanti)"),
           note="Entry omits 'CMU', but co-advisor Giulia Fanti is CMU ECE faculty and the 2026 PhD falls in Chi's CMU period (she left for Yale July 2025)."),
        ST("Harry Dong", "phd", [None, 2026], Q(YC, "Harry Dong , CMU Ph.D. 2026")),
        ST("Jiin Woo", "phd", [None, 2026], Q(YC, "Jiin Woo , CMU Ph.D. 2026 (co-advised with Gauri Joshi)")),
        ST("Pedro Valdeira", "phd", [None, 2025],
           Q(YC, "Pedro Valdeira , CMU Ph.D. 2025 (co-advised with J. Xavier and C. Soares through CMU-Portugal program)"),
           note="KiltHub dissertation 2025 (figshare 30113671), Advisor(s): Yuejie Chi."),
        ST("Shicong Cen", "phd", [None, 2024], Q(YC, "Shicong Cen , CMU Ph.D. 2024")),
        ST("Laixi Shi", "phd", [None, 2023], Q(YC, "Laixi Shi , CMU Ph.D. 2023"),
           note="KiltHub dissertation 2023 (figshare 24025908), Advisor(s): Yuejie Chi."),
        ST("Boyue Li", "phd", [None, 2023], Q(YC, "Boyue Li , CMU Ph.D. 2023"),
           note="KiltHub dissertation 2023 (figshare 23533776), Advisor(s): 'Yueji Chi'."),
        ST("Vince Monardo", "phd", [None, 2022], Q(YC, "Vince Monardo , CMU Ph.D. 2022"),
           note="KiltHub dissertation 2022 (figshare 21529038) by Vincent Monardo, Advisor(s): Yuejie Chi."),
        ST("Tian Tong", "phd", [None, 2022], Q(YC, "Tian Tong , CMU Ph.D. 2022"),
           note="KiltHub dissertation 2022 (figshare 21514656), Advisor(s): Yuejie Chi."),
        ST("Harlin Lee", "phd", [None, 2021], Q(YC, "Harlin Lee , CMU Ph.D. 2021 (co-advised with Jelena Kovacevic)"),
           note="KiltHub dissertation 2021 (figshare 19229556), Advisor(s): Yuejie Chi."),
        ST("Sudeep Salgia", "postdoc", [2023, 2025], Q(YC, "Sudeep Salgia Postdoctoral Researcher (2023-2025)")),
        ST("Zhize Li", "postdoc", [2022, 2023], Q(YC, "Zhize Li Research Scientist (2022-2023)"),
           note="Listed under 'Postdoc alumni' as Research Scientist."),
        ST("Maxime Ferreira Da Costa", "postdoc", [2018, 2020], Q(YC, "Maxime Ferreira Da Costa Post-doctoral researcher (2018-2020)")),
    ],
    lab_note=("CMU ECE group 2018-June 2025 (she moved to Yale Statistics & Data Science in July 2025); her current group "
              "page lists CMU PhD alumni, CMU co-advised current students and CMU-period postdocs."),
    notes=("Source: yuejiechi.github.io/group.html (users.ece.cmu.edu/~yuejiec timed out); 7 KiltHub ECE/MLD dissertations "
           "name her as advisor. Out: Ohio State-era students (Haoyu Fu, Yuanxin Li, Jiaqing Huang), postdocs Liming Wang "
           "(2015-2017) and Myung Cho (2017-2018; before/at her move from OSU), and Yale members (Yuepeng Yang, Ivan Lee). "
           "Zixin Wen and Lingjing Kong are already held."),
)

# ---------------------------------------------------------------------------------------------- Anthony Rowe
WI = "https://wise.ece.cmu.edu/about.html"
D["Anthony Rowe"] = dict(
    students=[
        ST("John Miller", "phd", [None, 2025], Q(WI, "John Miller PhD Candidate, Electrical and Computer Engineering Department"),
           note="KiltHub dissertation 2025 (figshare 30306868), Advisor(s): Anthony Rowe."),
        ST("Tianshu Huang", "phd", None, Q(WI, "Tianshu Huang PhD Candidate (co-advised with Carlee Joe-Wong)")),
        ST("Arjun Ramesh", "phd", None, Q(WI, "Arjun Ramesh PhD Candidate, Electrical and Computer Engineering Department")),
        ST("Tao Jin", "phd", None, Q(WI, "Tao Jin PhD Candidate, Electrical and Computer Engineering Department")),
        ST("Edward Lu", "phd", None, Q(WI, "Edward Lu PhD Candidate, Electrical and Computer Engineering Department")),
        ST("Tarana Laroia", "phd", None, Q(WI, "Tarana Laroia PhD Student, Electrical and Computer Engineering Department")),
        ST("Sruti Srinidhi", "phd", None, Q(WI, "Sruti Srinidhi PhD Candidate, Electrical and Computer Engineering Department")),
        ST("Jihwan Kim", "phd", None, Q(WI, "Jihwan Kim PhD Student, Electrical and Computer Engineering Department")),
        ST("Nuno Pereira", "member", None, Q(WI, "Nuno Pereira Research Scientist, CyLab"), note="Research staff."),
        ST("Mike Farb", "member", None, Q(WI, "Mike Farb Research Programmer, CyLab"), note="Research staff."),
        ST("Ivan Liang", "member", None, Q(WI, "Ivan Liang Research Programmer, CyLab"), note="Research staff."),
        ST("Akarsh Prabhakara", "phd", [None, 2024], Q(WI, "Akarsh Prabhakara PhD Candidate (co-advised with Swarun Kumar)"),
           note="KiltHub dissertation (figshare 28754774, posted 2024-12), Advisor(s): Anthony Rowe, Swarun Kumar."),
        ST("Mallesham Dasari", "postdoc", None, Q(WI, "Mallesham Dasari Postdoctoral Researcher, Now Professor at Northeastern University")),
        ST("Rahul Anand Sharma", "phd", [None, 2023], Q(WI, "Rahul Anand Sharma PhD Candidate (co-advised with Vyas Sekar)"),
           note="KiltHub dissertation 2023 (figshare 25030973), Advisor(s): Vyas Sekar, Anthony Rowe."),
        ST("Artur Balanuta", "phd", None, Q(WI, "Artur Balanuta PhD Candidate, Now at Amazon")),
        ST("John Choi", "member", None, Q(WI, "John Choi Research Programmer, Electrical and Computer Engineering Department"),
           note="Research staff (alumni list)."),
        ST("Kittipat Apicharttrisorn", "postdoc", None, Q(WI, "Kittipat Apicharttrisorn (Patrick) Postdoctoral Researcher, Now at Nokia Bell Labs")),
        ST("Elahé Soltanaghai", "postdoc", None, Q(WI, "Elahé Soltanaghai Postdoctoral Researcher, Now Professor at UIUC")),
        ST("Eric Riebling", "member", None, Q(WI, "Eric Riebling Senior Research Programmer, Electrical and Computer Engineering Department"),
           note="Research staff (alumni list)."),
        ST("Niranjini Rajagopal", "phd", [None, 2019], Q(WI, "Niranjini Rajagopal PhD Candidate, Now at Amazon"),
           note="KiltHub dissertation 2019 (figshare 9735845), Advisor(s): Anthony Rowe, Bruno Sinopoli."),
        ST("Adwait Dongare", "phd", [None, 2020], Q(WI, "Adwait Dongare PhD Candidate, Now at Apple"),
           note="KiltHub dissertation 2020 (figshare 13268855), Advisor(s): Anthony Rowe."),
        ST("Anh Luong", "postdoc", None, Q(WI, "Anh Luong Postdoctoral Researcher, Electrical and Computer Engineering Department")),
        ST("Patrick J.E. Lazik", "phd", [None, 2017], KH(6724088, "Patrick J.E. Lazik", "Anthony Rowe"),
           note="KiltHub ECE dissertation dated 2017-08."),
        ST("Oliver Shih", "phd", [None, 2018], KH(7235738, "Oliver Shih", "Anthony Rowe"),
           note="KiltHub ECE dissertation 2018."),
        ST("Luis Ramos Pinto", "phd", [None, 2018], KH(6714632, "Luis Ramos Pinto", "Luis Almeida,Anthony Rowe"),
           note="KiltHub ECE dissertation 2018 (CMU Portugal), Advisor(s): Luis Almeida, Anthony Rowe."),
        ST("Suma Thota", "masters", [None, 2023], KH(23582190, "Suma Thota", "Anthony Rowe"),
           note="KiltHub INI master's thesis 2023."),
        ST("Faisal Abdelmonem", "masters", [None, 2025],
           SE("http://reports-archive.adm.cs.cmu.edu/anon/2025/abstracts/25-123.html", "Faisal Abdelmonem M.S. Thesis",
              "Anthony Rowe (Chair)", long=True),
           note="CMU-CS-25-123 M.S. thesis; Thesis Committee: Anthony Rowe (Chair)."),
    ],
    lab_note=("Wireless Sensing and Embedded Systems (WiSE) Lab, CMU ECE; 'Team' lists 8 PhD students (+ Sagar Bharadwaj, "
              "held) and 3 research staff; alumni list 6 PhDs, 4 postdocs, 2 programmers; KiltHub/SCS theses add 2016-2018 PhDs "
              "and 2 MS theses."),
    notes=("Sources: wise.ece.cmu.edu/about.html (Team/Alumni), KiltHub ECE/INI theses with Advisor(s) Anthony Rowe, "
           "CMU-CS-25-123. users.ece.cmu.edu/~agr timed out (connect timeout). Research staff recorded as role member. "
           "Alumni on the WiSE page carry no dates; all are post-2016 by their thesis years or current titles."),
)

# ---------------------------------------------------------------------------------------------- Theophilus Benson
TB = "https://www.andrew.cmu.edu/user/theophib/"
TBG = "Current Research Group"
D["Theophilus Benson"] = dict(
    students=[
        ST("Lucas Castanheira", "phd", None, Q(TB, "Current Research Group Lucas Castanheira, PhD")),
        ST("Pragna Mamidipaka", "phd", None, Q(TB, "Pragna Mamidipaka , PhD")),
        ST("Semebia Wurah", "member", None, Q(TB, "Semebia Wurah, Research Associate")),
        ST("Mike Mwanje", "member", None, Q(TB, "Mike Mwanje, Research Associate")),
        ST("Heran Equbay", "member", None, Q(TB, "Heran Equbay, Research Associate")),
    ],
    lab_note=("Moved from Brown to CMU ECE (CSD courtesy) c. 2023; CMU homepage 'Current Research Group' lists 3 PhD "
              "students (Isabel Suizo held) and 3 research associates."),
    notes=("Source: andrew.cmu.edu/user/theophib/ (linked from his Brown page 'I've moved to CMU'). Brown-era students "
           "are out. Hamna Shafqat (held, CSD 'Thesis Advisor') is not on his group list. No KiltHub/SCS thesis with him "
           "as advisor yet. CV marks advisees by underlining, which the text extraction loses."),
)

# ---------------------------------------------------------------------------------------------- Tai-Sing Lee
T26 = WB + "20260811112352id_/https://www.cnbc.cmu.edu/~tai/"
T16 = WB + "20160111193008id_/http://www.cnbc.cmu.edu/~tai/"
TL16 = WB + "20160425174436id_/http://leelab.cnbc.cmu.edu:80/"
_G = "listed under 'Current Ph.D. and M.S. Students' (degree not stated) on the Aug 2026 capture of his homepage."
_U = "Former undergraduate research fellow, listed after the Jan 2016 roster (not on it), i.e. 2016 or later."


def _vis(inst):
    return f"Visiting undergraduate research fellow from {inst}; listed in the lab's former undergraduate fellows after the Jan 2016 roster."


D["Tai-Sing Lee"] = dict(
    students=[
        ST("Ge (Summer) Huang", "phd", None, Q(T26, "Ge (Summer) Huang Neural Computation, Carnegie Mellon. (on leave)"),
           note="Ph.D. student since at least Jan 2016 (on the 2016 roster); on leave in 2026."),
        ST("Zhiwen Bian", "member", None, Q(T26, "Zhiwen Bian Computational Biology, Carnegie Mellon."), note="Graduate student " + _G),
        ST("Jinyi Ye", "member", None, Q(T26, "Jinyi Ye Computational Biology, Carnegie Mellon."), note="Graduate student " + _G),
        ST("Xirui Liu", "member", None, Q(T26, "Xirui Liu Computational Biology, Carnegie Mellon."), note="Graduate student " + _G),
        ST("Yue Li", "member", None, Q(T26, "Yue Li Artificial intelligence engineeering, Carnegie Mellon."), note="Graduate student " + _G),
        ST("Yingjue Bian", "member", None, Q(T26, "Yingjue Bian Biomedical Engineering, Carnegie Mellon."), note="Graduate student " + _G),
        ST("Dongfeng Li", "member", None, Q(T26, "Dongfeng Li Biomedical Engineering, Carnegie Mellon."), note="Graduate student " + _G),
        ST("Yize Wu", "member", None, Q(T26, "Yize Wu Biomedical Engineering, Carnegie Mellon."), note="Graduate student " + _G),
        ST("David Wang", "member", None, Q(T26, "David Wang Computer Science, Carnegie Mellon."), note="Graduate student " + _G),
        ST("Yuxuan Zhu", "member", None, Q(T26, "Yuxuan Zhu Computaitonal Biology, Carnegie Mellon."), note="Graduate student " + _G),
        ST("Haifei Guo", "member", None, Q(T26, "Haifei Guo Biomedical Engineering, Carnegie Mellon."), note="Graduate student " + _G),
        ST("Issac Lin", "undergraduate", None, Q(T26, "Current Undergraduate Research Fellows Issac Lin , Computer Science, Carnegie Mellon, CMU")),
        ST("Alan Ramirez", "undergraduate", None, Q(T26, "Alan Ramirez , Computer Science, Carnegie Mellon, CMU")),
        ST("George Liu", "undergraduate", None, Q(T26, "George Liu , Computer Science, Carnegie Mellon, CMU")),
        ST("Soham Raychaudhuri", "undergraduate", None, Q(T26, "Soham Raychaudhuri , Computer Science, Carnegie Mellon, CMU")),
        ST("Ronav Jaiwal", "undergraduate", None, Q(T26, "Ronav Jaiwal Computer Science, Carnegie Mellon.")),
        ST("Husain Raja", "undergraduate", None, Q(T26, "Husain Raja Computer Science, Carnegie Mellon.")),
        ST("Om Kathira", "undergraduate", None, Q(T26, "Om Kathira Neuroscience, Carnegie Mellon.")),
        ST("Andrew Luo", "masters", [None, 2021], Q(T26, "Andrew Luo Neural Computation, 2021. Ph.D. program, Carnegie Mellon."),
           note="Listed under 'Former Ph.D. and M.S. Students' (Neural Computation 2021, then the CMU Ph.D. program)."),
        ST("Liyuan Liang", "masters", [None, 2021], Q(T26, "Liyuan Liang Neural Computation, 2021. Ph.D. program, Carnegie Mellon."),
           note="Listed under 'Former Ph.D. and M.S. Students' (Neural Computation 2021, then the CMU Ph.D. program)."),
        ST("Gaya Mohankumar", "masters", [None, 2017], Q(T26, "Gaya Mohankumar , M.S. 2017. in Biomedical engineering")),
        ST("Shefali Umrania", "masters", [None, 2017], Q(T26, "Shefali Umrania , M.S. 2017. in Computational Biology")),
        ST("Jingyuan Li", "masters", [None, 2019], Q(T26, "Jingyuan Li , M.S. in Biomedical engineering, 2019.")),
        ST("Yuanyuan Wei", "masters", [None, 2019], Q(T26, "Yuanyuan Wei , M.S. in EECS, Ph.D. program in Biomedical Engineering, 2019.")),
        ST("Mert Inan", "masters", [None, 2019], Q(T26, "Mert Inan M.S. Computational Biology, 2019. Carnegie Mellon.")),
        ST("Jiaxin Wang", "masters", [None, 2021], Q(T26, "Jiaxin Wang M.S. Computaitonal Biology, 2021. Carnegie Mellon.")),
        ST("Yusen Zhu", "masters", [None, 2021], Q(T26, "Yusen Zhu M.S. Biomedical Engineering, 2021. Carnegie Mellon.")),
        ST("Xiaoqi Zhang", "masters", [None, 2021], Q(T26, "Xiaoqi Zhang M.S. Computaitonal Biology, 2021. Carnegie Mellon.")),
        ST("Sicheng Dai", "masters", [None, 2022], Q(T26, "Sicheng Dai M.S. Biomedical Engineering, 2022. Carnegie Mellon.")),
        ST("Mirudhula Mukundan", "masters", [None, 2022], Q(T26, "Mirudhula Mukundan M.S. Comutational Biology 2022, Carnegie Mellon.")),
        ST("Zitong Wang", "masters", [None, 2023], Q(T26, "Zitong Wang MS. Biomedical Engineering, 2023. Carnegie Mellon.")),
        ST("Yung Ying Chen", "masters", [None, 2023], Q(T26, "Yung Ying Chen MS. Biomedical Engineering, 2023. Carnegie Mellon.")),
        ST("Ziqi Wen", "masters", [None, 2024], Q(T26, "Ziqi Wen M.S. Biomedical Engineering, 2024 Carnegie Mellon.")),
        ST("Weifan Wang", "masters", [None, 2023], Q(T26, "Weifan Wang M.S. Biomedical Engineering, 2023 Carnegie Mellon.")),
        ST("Junru Zhao", "masters", [None, 2024], Q(T26, "Junru Zhao M.S. Biomedical Engineering, 2024 Carnegie Mellon.")),
        ST("Shang (Gale) Gao", "masters", [None, 2023], Q(T26, "Shang (Gale) Gao M.S. Biomedical Engineering, 2023. Carnegie Mellon.")),
        ST("Hadrien Helfgott", "masters", [None, 2025], Q(T26, "Hadrien Helfgott M.S. Computer Science, 2025. Carnegie Mellon.")),
        ST("Dunhan Jiang", "masters", [None, 2025], Q(T26, "Dunhan Jiang MS. Computational Biology, 2025 Carnegie Mellon."),
           note="KiltHub master's thesis 2025 (figshare 29120246, Biological Sciences), Advisor(s): Tai-Sing Lee."),
        ST("Leiran Song", "masters", [None, 2025], Q(T26, "Leiran Song MS Electrical Engineering, 2025, Carnegie Mellon.")),
        ST("Jingtao Zhang", "masters", [None, 2025], Q(T26, "Jingtao Zhang MS Computer Science, 2025, Carnegie Mellon.")),
        ST("Wenhao Zhang", "postdoc", None, Q(T26, "Former Postdoctoral Fellows Wenhao Zhang Ph.D. Biophysics (2016)"),
           note="Former postdoc; PhD 2016, so the postdoc falls in 2016 or later (not on the Jan 2016 roster)."),
        ST("Jason Samonds", "postdoc", [None, 2016], Q(T16, "Current Postdoctoral Fellows Jason Samonds , Ph.D. Electrical Engineering (2004) Vanderbilt University."),
           note="Current postdoc on the Jan 2016 capture; listed as postdoc alumnus on the Apr 2016 lab site."),
        ST("Corentin Massot", "postdoc", [None, 2016], Q(T16, "Corentin Massot , Ph.D. Congitive Science, University of Glasgow & McGill University Current Ph.D. Students"),
           note="Current postdoc on the Jan 2016 capture."),
        ST("Elizabeth Ottens", "undergraduate", [2016, None], Q(T16, "Current Undergraduate Research Fellows Elizabeth Ottens , Electrical and Computer Engineering, CMU")),
        ST("Lingzhang Jiang", "undergraduate", [2016, None], Q(T16, "Lingzhang Jiang , Computer Science, CMU Dan Howarth")),
        ST("Dan Howarth", "undergraduate", [2016, None], Q(T16, "Dan Howarth , Computer Science, CMU Former Ph.D. Students")),
        ST("Zhihao Li", "masters", [2016, None], Q(TL16, "Zhihao Li M.S. Student (CSD)"), note="'Our Team' on the Apr 2016 lab site."),
        ST("Chaitanya Modak", "masters", [2016, None], Q(TL16, "Chaitanya Modak M.S. Student (ECE)"), note="'Our Team' on the Apr 2016 lab site."),
        ST("Allison Fisher", "undergraduate", [2016, None], Q(TL16, "Allison Fisher B.S. Student (CSD)"), note="'Our Team' on the Apr 2016 lab site."),
        ST("Bojian Han", "undergraduate", [2016, None], Q(TL16, "Bojian Han B.S. Student (CSD)"), note="'Our Team' on the Apr 2016 lab site."),
        ST("Chen Liu", "undergraduate", [2016, None], Q(TL16, "Chen Liu B.S. Student (CSD)"), note="'Our Team' on the Apr 2016 lab site."),
        ST("Jessica Lee", "undergraduate", [2016, None], Q(TL16, "Jessica Lee B.S. Student (CSD)"), note="'Our Team' on the Apr 2016 lab site."),
        ST("Gil Bartholomew", "undergraduate", None, Q(T26, "Gil Bartholomew , Music and Physics, Carnegie Mellon"), note=_U),
        ST("Zixin Sha", "undergraduate", None, Q(T26, "Zixin Sha , Computational Neuroscience, Carnegie Mellon, CMU."), note=_U),
        ST("Wentao Qiu", "other", None, Q(T26, "Wentao Qiu , YuanPi College, Computer Science, Peking University."), note=_vis("Peking University")),
        ST("Danial Wang", "undergraduate", None, Q(T26, "Danial Wang , Computer Science, CMU, Ph.D. program in Computer Science at Yale."), note=_U),
        ST("Nicholas McNeal", "other", None, Q(T26, "Nicholas McNeal Computer Science, Ohio State University."), note=_vis("Ohio State University")),
        ST("Hal Rockwell", "undergraduate", None, Q(T26, "Hal Rockwell , Computational Biology, CMU."), note=_U),
        ST("Deying Song", "other", None, Q(T26, "Deying Song , Yuanpei College, Mathematics, Peking Univeristy ."), note=_vis("Peking University") + " Later a CMU Neural Computation PhD student."),
        ST("Aniekan Umoren", "other", None, Q(T26, "Aniekan Umoren , BCS and EECS, MIT."), note=_vis("MIT")),
        ST("Chen Guo", "other", None, Q(T26, "Chen Guo , Computer Science, Tsinghua University"), note=_vis("Tsinghua University")),
        ST("Jennifer Huang", "undergraduate", None, Q(T26, "Jennifer Huang , Computer Science, CMU. Facebook"), note=_U),
        ST("Simin Li", "undergraduate", None, Q(T26, "Simin Li , Computer Science, CMU. Amazon"), note=_U),
        ST("Yuqi Zhang", "undergraduate", None, Q(T26, "Yuqi Zhang , Computer Science, CMU. Apple"), note=_U),
        ST("Ho-Yin Chau", "other", None, Q(T26, "Ho-Yin Chau , Physics, Mathematics, Computer Science, UC Berkeley"), note=_vis("UC Berkeley")),
        ST("Julie Xueyan Niu", "other", None, Q(T26, "Julie Xueyan Niu , Mathematics, Hong Kong University"), note=_vis("Hong Kong University")),
        ST("Zinui Wu", "undergraduate", None, Q(T26, "Zinui Wu , Mathematics, Statistics and Machine Learning, Carnegie Mellon University"), note=_U),
        ST("Yue Xu", "undergraduate", None, Q(T26, "Yue Xu , Computer Science, Carnegie Mellon University, CNS Ph.D. program at Caltech."), note=_U),
        ST("Siming Yan", "other", None, Q(T26, "Siming Yan , Computer Science, Peking University"), note=_vis("Peking University")),
        ST("Jielin Qiu", "other", None, Q(T26, "Jielin Qiu , EE Shanghai Jiaotung University"), note=_vis("Shanghai Jiao Tong University") + " Later a CMU CS PhD student."),
        ST("Bowen Xiao", "other", None, Q(T26, "Bowen Xiao , Computer Science, Peking University."), note=_vis("Peking University")),
        ST("Xuyang Fang", "other", None, Q(T26, "Xuyang Fang , Computer Science, Peking University, MS program in Computer Science, Carnegie mellon."), note=_vis("Peking University")),
        ST("Hao Wang", "other", None, Q(T26, "Hao Wang , Computer Science, Peking University."), note=_vis("Peking University")),
        ST("Xingyu Lin", "other", None, Q(T26, "Xingyu Lin , Computer Science, Peking University. Ph.D. Program in CS, CMU."), note=_vis("Peking University")),
        ST("Tiancheng Zhi", "other", None, Q(T26, "Tiancheng Zhi , Computer Science, Peking University. Ph.D. Program in CS, CMU."), note=_vis("Peking University")),
    ],
    lab_note=("Lee Laboratory for Biological and Machine Intelligence (CSD/CNBC); homepage roster (Aug 2026 capture) lists "
              "12 current graduate students, 7 current undergraduate fellows and long alumni lists; Jan 2016 homepage and "
              "Apr 2016 lab-site captures give the 2016 roster."),
    notes=("Sources: Wayback id_ captures of www.cnbc.cmu.edu/~tai/ (live fetch fails TLS verification) for Aug 2026 and "
           "Jan 2016, and leelab.cnbc.cmu.edu (Apr 2016). Anyone already a 'former' member on the Jan 2016 page (e.g. "
           "Mingmin Zhao, Shashank Singh, Ben Poole) or with a pre-2016 degree (Esha Uboweja M.S. 2015, PhDs 2002-2013, "
           "postdocs Smith/Yan/Yu) is out. Undergraduate fellows from other universities are recorded as role 'other' "
           "(visiting). Tianqin Li and Yimeng Zhang (CMU-CS-21-105, Thesis Committee: Tai Sing Lee (Chair)) are already held."),
)

# ---------------------------------------------------------------------------------------------- Rayid Ghani
DS = "https://datasciencepublicpolicy.org/team/"
DS22 = WB + "20220529050101id_/http://www.datasciencepublicpolicy.org/team/"
DS24 = WB + "20240224054108id_/http://www.datasciencepublicpolicy.org/team/"
_DSN = ("Not on the Nov 2019 capture (then still the University of Chicago 'Center for Data Science and Public Policy' "
        "team page); on the CMU-era page (contact [email removed]).")
D["Rayid Ghani"] = dict(
    students=[
        ST("Kasun Amarasinghe", "postdoc", [2021, None], Q(DS, "Our Team Kasun Amarasinghe Post-doc Researcher"),
           note="Spelled 'Kasun Amarsinghe' on the May 2022 and Feb 2024 captures. " + _DSN),
        ST("Hemank Lamba", "postdoc", None, Q(DS, "Hemank Lamba Post-doc"),
           note="Listed among alumni; absent from the Oct 2021 roster and present from the Jan 2023 roster on, i.e. a CMU-era postdoc. Also held as a PhD student of Jürgen Pfeffer."),
        ST("Alice Lai", "member", [2023, None], Q(DS, "Alice Lai Senior Data Scientist"), note="Research staff. " + _DSN),
        ST("Liliana Millán Núñez", "member", [2023, None], Q(DS, "Liliana Millán Núñez Senior Data Scientist"), note="Research staff. " + _DSN),
        ST("Peter Casey", "member", [2021, None], Q(DS22, "Peter Casey Program Director"), note="Staff (program director), current on the CMU-era roster (page revised 2021-10-27); alumni by 2023."),
        ST("Anne Driscoll", "member", [2021, None], Q(DS22, "Anne Driscoll Data Analyst"), note="Research staff, current on the CMU-era roster (page revised 2021-10-27); alumni by 2023."),
        ST("Carly Jones", "member", [2021, 2021], Q(DS22, "Carly Jones Research Assistant"), note="Research assistant on the CMU-era roster (page revised 2021-10-27); gone by 2023."),
        ST("Kit Rodolfa", "member", [None, None], Q(DS22, "Kit Rodolfa Senior Research Scientist Alumni"),
           note="Senior Research Scientist; on the Chicago-era roster and still current on the CMU-era roster (2021-10); alumni by 2023."),
    ],
    lab_note=("Data Science for Social Good Lab (moved with him from the University of Chicago to CMU in 2019); its team page "
              "lists research staff and postdocs, not students: 4 current members, CMU-era alumni from the 2021 and 2023 rosters."),
    notes=("Sources: datasciencepublicpolicy.org/team/ live and Wayback captures (Nov 2019 = Chicago-era, May 2022 and Feb 2024 = "
           "CMU-era). The long 'Alumni' list is the Chicago-era team carried over unchanged since 2019 and is excluded except "
           "where a member is first listed in the CMU era. No SCS thesis chaired by him (only committee memberships) and no "
           "KiltHub thesis naming him as advisor; homepage/Heinz profile list no students. PhD students Johnna Sundberg and "
           "Rachel Kim are already held."),
)

# ---------------------------------------------------------------------------------------------- Riad Wahby
D["Riad Wahby"] = dict(
    students=[
        ST("Prashanth M. Ramakrishna", "masters", [None, 2024], KH(25872175, "Prashanth M. Ramakrishna", "Riad S. Wahby"),
           note="KiltHub INI master's thesis 2024, Advisor(s): Riad S. Wahby, Jonathan Bootle."),
        ST("Faisal Binmahfoudh", "masters", [None, 2023], KH(24116022, "Faisal Binmahfoudh", "Riad Wahby"),
           note="KiltHub INI master's thesis 2023."),
    ],
    lab_note=("No lab page; CMU ECE Assistant Professor since September 2022 (CV); CSD profile lists 2 advisees (held) and "
              "KiltHub has 2 INI master's theses he advised."),
    notes=("Searched: wahby.org/wahby.net homepage and CV (no advising section), CSD profile, SCS thesis index (none), "
           "KiltHub (2 INI MS theses). Quang Dao and Kunming Jiang are already held."),
)

# ---------------------------------------------------------------------------------------------- Hui Zhang
D["Hui Zhang"] = dict(
    students=[
        ST("Junchen Jiang", "phd", [None, 2017],
           SE("http://reports-archive.adm.cs.cmu.edu/anon/2017/abstracts/17-119.html", "Junchen Jiang September 2017 Ph.D. Thesis",
              "Hui Zhang (Co-Chair)", long=True),
           note="CMU-CS-17-119 (Sept 2017), Thesis Committee: Hui Zhang (Co-Chair), Vyas Sekar (Co-Chair). Already held; thesis source added."),
    ],
    lab_note="No lab page (homepage lists only publications and talks; he is co-founder/CEO of Conviva); 1 known 2016+ PhD advisee.",
    notes=("Searched: cs.cmu.edu/~hzhang homepage, CSD profile (no Advisees section), SCS thesis index 2016-2026 (only "
           "CMU-CS-17-119 chaired/co-chaired by him), KiltHub (no CMU thesis). Nothing beyond the already-held Junchen Jiang."),
)

# ---------------------------------------------------------------------------------------------- Takeo Kanade
D["Takeo Kanade"] = dict(
    students=[],
    lab_note=("RI profile 'Students/Affiliates' lists only past PhD/master's students (the latest graduated by 2015) and "
              "two current affiliates (a Pitt collaborator and his administrative assistant); no 2016+ advisee found."),
    notes=("Searched: RI faculty page (live, 2017 Wayback; the 2016 old-RI 'Students' tab has no capture), cs.cmu.edu/~tk, "
           "CSD profile (no Advisees section), SCS thesis index 2016-2026 (no thesis with him as chair or member), KiltHub "
           "('Takeo Kanade'/'Kanade': latest thesis naming him is Varun Ramakrishna's 2015 'Pose Machines'). The held "
           "students are Varun Ramakrishna (thesis 2015) and Yair Movshovitz-Attias."),
)

# ---------------------------------------------------------------------------------------------- Mary Shaw
D["Mary Shaw"] = dict(
    students=[],
    lab_note="No current lab/student page; no 2016+ advisee found.",
    notes=("Searched: CSD profile (no Advisees section), S3D core-faculty profile (no students), homepage "
           "(www.cs.cmu.edu/~shaw redirects to spoke.compose.cs.cmu.edu/shaweb/, robots-disallowed; Wayback captures of it "
           "stop in 2013), SCS thesis index incl. ISR series 2016-2022 (no thesis with her as chair or member), KiltHub "
           "('Mary Shaw': no CMU thesis). Both already-held students graduated before the window (Orna Raz PhD 2004, "
           "Christopher Scaffidi PhD 2009)."),
)
