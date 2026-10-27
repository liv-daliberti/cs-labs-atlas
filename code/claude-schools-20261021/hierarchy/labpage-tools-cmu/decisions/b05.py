from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Justin Chan
JC = "https://semanticsignals.com/cadre.html"
D["Justin Chan"] = dict(
    lab_site="https://semanticsignals.com/",
    people_page=JC,
    people_pages=[JC],
    members=[
        M("Mengning Li", "postdoc", None, JC, q="Mengning Li Postdoc"),
        M("Siqi Zhang", "phd", None, JC, q="Siqi Zhang Ph.D. Student co-advised with Mayank Goel"),
        M("Jiangyifei Zhu", "phd", None, JC, q="Jiangyifei Zhu Ph.D. Student co-advised with Swarun Kumar"),
        M("Freddy Liu", "phd", None, JC, q="Freddy Liu Ph.D. Student co-advised with Swarun Kumar"),
        M("Seungjoo Lee", "phd", None, JC, q="Seungjoo Lee Ph.D. Student co-advised with Mayank Goel"),
        M("Dongrak Choi", "visitor", None, JC, q="Dongrak Choi Visiting Ph.D. Student from Seoul National University"),
        M("Leah Zhang", "undergraduate", None, JC, q="Leah Zhang Undergraduate"),
        M("Ashee Bansaal", "undergraduate", None, JC, q="Ashee Bansaal Undergraduate"),
        M("Anika Sharma", "undergraduate", None, JC, q="Anika Sharma Undergraduate"),
        M("Alexandra Yin", "undergraduate", None, JC, q="Alexandra Yin Undergraduate"),
        M("Xiyuxing Zhang", "visitor", None, JC, q="Xiyuxing Zhang Visiting Ph.D. from Tsinghua",
          note="alumni network"),
        M("Kuang Yuan", "phd", None, JC, q="Kuang Yuan Affiliated Ph.D. Student advised by Swarun Kumar",
          note="alumni network; affiliated student, primary advisor Swarun Kumar; now Meta"),
        M("Saksham Bhutani", "masters", None, JC, q="Saksham Bhutani Masters", note="alumni; then Columbia PhD"),
        M("Zhikai Qin", "visitor", None, JC, q="Zhikai Qin Visiting Undergraduate from Tsinghua",
          note="alumni; visiting undergraduate"),
        M("Duc Vu", "undergraduate", None, JC, q="Duc Vu Undergraduate", note="alumni; then Georgia Tech PhD"),
        M("Tao Qiang", "undergraduate", None, JC, q="Tao Qiang Undergraduate", note="alumni; then CMU PhD"),
        M("Caroline Zhao", "undergraduate", None, JC, q="Caroline Zhao Undergraduate, NSF REU",
          note="alumni; NSF REU"),
        M("Akshay Anand", "undergraduate", None, JC, q="Akshay Anand Undergraduate, NSF REU",
          note="alumni; NSF REU"),
        M("Clara Palacios", "undergraduate", None, JC, q="Clara Palacios Undergraduate"),
    ],
    pubs=[PUB("https://semanticsignals.com/pubs.html", mode="css:div.pub_text", title_css="a.ptitle")],
    notes=("S3D profile -> cs.cmu.edu/~justinc3 -> Semantic Signals Lab (semanticsignals.com; nav built by JS, "
           "people page is cadre.html). No Wayback captures of cadre.html (lab founded ~2024), so live page only. "
           "Pubs list includes the PI's UW-era papers. 'Kevin Xu' co-authors two 2025 papers with the PI but is "
           "not on the people page (not recorded)."),
    blocked=[],
)

# ---------------------------------------------------------------- Yuejie Chi
YC = "https://yuejiechi.github.io/group.html"
YC20 = WB + "20200929032037id_/https://users.ece.cmu.edu/~yuejiec/group.html"
YC23 = WB + "20230212123846id_/https://users.ece.cmu.edu/~yuejiec/group.html"
YC18 = WB + "20180222215520id_/http://users.ece.cmu.edu:80/~yuejiec/group.html"
D["Yuejie Chi"] = dict(
    lab_site="https://yuejiechi.github.io/",
    people_page=YC,
    people_pages=[YC, YC18, YC20, YC23],
    members=[
        M("He Wang", "phd", [2022, None], YC, q="He Wang Ph.D. Candidate (2022-current, CMU ECE"),
        M("Tong Yang", "phd", [2023, None], YC, q="Tong Yang Ph.D. Candidate (2023-current, CMU ECE"),
        M("Timofey Efimov", "phd", [2023, None], YC, q="Timofey Efimov Ph.D. Candidate (2023-current, CMU ECE"),
        M("Zixin Wen", "phd", [2021, 2026], YC, q="Zixin Wen , CMU Ph.D. 2026"),
        M("Lingjing Kong", "phd", [2021, 2026], YC, q="Lingjing Kong , CMU Ph.D. 2026"),
        M("Xingyu Xu", "phd", [None, 2026], YC, q="Xingyu Xu , Ph.D. 2026"),
        M("Harry Dong", "phd", [2021, 2026], YC, q="Harry Dong , CMU Ph.D. 2026"),
        M("Jiin Woo", "phd", [2021, 2026], YC, q="Jiin Woo , CMU Ph.D. 2026"),
        M("Pedro Valdeira", "phd", [2020, 2025], YC, q="Pedro Valdeira , CMU Ph.D. 2025",
          note="CMU-Portugal program, co-advised with J. Xavier and C. Soares"),
        M("Shicong Cen", "phd", [2019, 2024], YC, q="Shicong Cen , CMU Ph.D. 2024"),
        M("Laixi Shi", "phd", [2018, 2023], YC, q="Laixi Shi , CMU Ph.D. 2023"),
        M("Boyue Li", "phd", [2018, 2023], YC, q="Boyue Li , CMU Ph.D. 2023"),
        M("Vince Monardo", "phd", [2016, 2022], YC, q="Vince Monardo , CMU Ph.D. 2022",
          note="followed the PI from OSU (Fall 2016 start)"),
        M("Tian Tong", "phd", [2015, 2022], YC, q="Tian Tong , CMU Ph.D. 2022"),
        M("Harlin Lee", "phd", [2017, 2021], YC, q="Harlin Lee , CMU Ph.D. 2021"),
        M("Sudeep Salgia", "postdoc", [2023, 2025], YC, q="Sudeep Salgia Postdoctoral Researcher (2023-2025)"),
        M("Zhize Li", "staff", [2022, 2023], YC, q="Zhize Li Research Scientist (2022-2023)",
          note="research scientist, listed under postdoc alumni"),
        M("Maxime Ferreira Da Costa", "postdoc", [2018, 2020], YC,
          q="Maxime Ferreira Da Costa Post-doctoral researcher (2018-2020)"),
        M("Diogo Cardoso", "phd", [2019, None], YC20,
          q="Diogo Cardoso Ph.D. Student (Fall 2019-current, co-advised with J. Xavier through CMU-Portugal program)",
          note="2019-12 capture only; not on 2023 or live page"),
        M("Yuanxin Li", "postdoc", [2018, 2018], YC20,
          q="Yuanxin Li Ph.D., 2013 - 2018 Post-doctoral researcher (Fall 2018)",
          note="OSU PhD 2018, then postdoc Fall 2018; in the 2018/10 CMU group-retreat photo caption"),
    ],
    pubs=[PUB("https://yuejiechi.github.io/publications.html", mode="auto")],
    notes=("users.ece.cmu.edu/~yuejiec now redirects to yuejiechi.github.io (PI moved to Yale July 2025; at CMU "
           "from 2018). Members from the live Group page plus 2018-02, 2019-12 (2020 cdx) and 2023-02 captures of "
           "the old CMU group page. Skipped as Yale-era: Yuepeng Yang (postdoc 2025-), Ivan Lee (Yale SDS). "
           "Skipped as OSU-era: Haoyu Fu, Jiaqing Huang, Liming Wang, Azer Shikhaliev, Xusheng Wang and other OSU "
           "M.S./visitors; Myung Cho (postdoc 2017-2018) not placed at CMU by the source. 'Xiaohan' appears in a "
           "2019 photo caption without a surname (not recorded). Page says undergrad/master/visiting students are "
           "not listed."),
    blocked=[],
)

# ---------------------------------------------------------------- Steven Michael Chase
SC_ = "http://www.cnbc.cmu.edu:80/~schase/people.php"
SC16 = WB + "20160129170305id_/" + SC_
SC17 = WB + "20170515135237id_/" + SC_
SC18 = WB + "20180114010005id_/" + SC_
SC20 = WB + "20200123031754id_/" + SC_
D["Steven Michael Chase"] = dict(
    lab_site=WB + "20210421035958id_/http://www.cnbc.cmu.edu/~schase/",
    people_page=SC20,
    people_pages=[SC16, SC17, SC18, SC20],
    members=[
        M("Matthew Golub", "postdoc", None, SC16, near="Post-Docs", note="later listed as alumnus (Stanford)"),
        M("Yin Zhang", "phd", None, SC16, near="PhD Students", note="alumnus PhD (Google) by 2020"),
        M("Xiao Zhou", "phd", [None, 2020], SC20, near="PhD Students",
          note="homepage news 3/23/2020: thesis defended"),
        M("Lindsay Bahureksa", "phd", None, SC20, near="PhD Students"),
        M("Jay Hennig", "phd", None, SC20, near="PhD Students"),
        M("Brian Jeon", "phd", None, SC20, near="PhD Students", note="listed as Masters student in 2016-01"),
        M("Carmen Fisac", "phd", None, SC20, near="PhD Students"),
        M("Katrina Nguyen", "phd", None, SC20, near="PhD Students"),
        M("Tze Hui Koh", "phd", None, SC20, near="PhD Students"),
        M("Darby Losey", "phd", None, SC20, near="PhD Students"),
        M("Adam Smoulder", "phd", None, SC20, near="PhD Students"),
        M("Sadhana Ravikumar", "masters", None, SC17, near="Masters Students", note="alumna MS (Penn) by 2018"),
        M("Abhinav Sharma", "staff", None, SC18, q="Researchers Abhinav Sharma",
          note="Masters student in 2017-05, researcher in 2018-01; alumnus MS by 2020"),
        M("Rob Rasmussen", "member", None, SC16, near="Affiliated Members",
          note="affiliated member; alumni list 2020 gives MD, PhD"),
        M("Faisal Baqai", "member", None, SC18, near="Affiliated Members",
          note="affiliated member; alumni list 2020 gives MS (CMU Program in Neural Computation)"),
        M("Emily Oby", "member", None, SC18, near="Affiliated Members", note="affiliated member, PhD"),
        M("Mary Cundiff", "member", None, SC20, near="Affiliated Members", note="affiliated member"),
    ],
    pubs=[PUB(WB + "20210302070638id_/http://www.cnbc.cmu.edu/~schase/publications.php", mode="css:i",
              title_css="b", note="last capture 2021-03; list ends 2019; years from year headings")],
    notes=("BME profile links the lab site www.cnbc.cmu.edu/~schase/ (live host fails TLS; no newer lab site found "
           "via RI profile, BME profile or web search). People page people.php read in 2016-01, 2017-05, 2018-01 "
           "and 2020-01 captures (last capture 2020). Skipped: Prof. Agustin Gutierrez Galvez (visiting faculty, "
           "affiliated); 7 undated alumni already listed as alumni in the 2016-01 capture (Sagi Perel, Pete Lund, "
           "Srivignesh Rajendran, Sonia Todorova, Yao Zhao, Madhumitha Raghu, Hrishikesh Rao)."),
    blocked=[],
)

# ---------------------------------------------------------------- Howie Choset
HC_LAB = "https://www.ri.cmu.edu/robotics-groups/biorobotics/"
HC_PROF = "https://www.ri.cmu.edu/ri-faculty/howie-choset/"
HC_P18 = WB + "20180715011144id_/https://www.ri.cmu.edu/ri-faculty/howie-choset/"
HC20 = WB + "20200519191925id_/https://www.ri.cmu.edu/robotics-groups/biorobotics/"
HC23 = WB + "20230327135000id_/https://www.ri.cmu.edu/robotics-groups/biorobotics/"
D["Howie Choset"] = dict(
    lab_site="http://biorobotics.ri.cmu.edu/",
    people_page=HC_LAB,
    people_pages=[HC_LAB, HC_PROF, HC_P18, HC20, HC23],
    members=[
        M("Capprin James Bass", "phd", None, HC_PROF, near="current phd students"),
        M("Anoop Bhat", "phd", None, HC_PROF, near="current phd students"),
        M("Chao Cao", "phd", None, HC_PROF, near="current phd students"),
        M("Shricharana Shastry Puthige", "phd", None, HC_PROF, near="current phd students"),
        M("Albert Xu", "phd", None, HC_PROF, near="current phd students"),
        M("Nicolas Mateo Zevallos-Roberts", "masters", None, HC_PROF, near="current masters students"),
        M("Tony Dear", "phd", None, HC_PROF, near="past phd students", note="seen current on a 2018/2020/2023 capture"),
        M("Benjamin (Ben) Freed", "phd", None, HC_PROF, near="past phd students", note="seen current on a 2018/2020/2023 capture"),
        M("Ramkumar Natarajan", "phd", None, HC_PROF, near="past phd students", note="seen current on a 2018/2020/2023 capture"),
        M("Ananya Rao", "phd", None, HC_PROF, near="past phd students", note="seen current on a 2018/2020/2023 capture"),
        M("FNU Abhimanyu", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Raunaq Mahesh Bhirangi", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Blake Buchanan", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Edward Chen", "masters", None, HC_PROF, near="past masters students", note="Ed Chen on the lab member lists"),
        M("Shuoqi (Socky) Chen", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Daqian Cheng", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Howard Coffin", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Ruijie Fu", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Ruohai Ge", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Raghavv Goel", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Naman Gupta", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Evan Harber", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Jiaheng Hu", "masters", None, HC_PROF, near="past masters students", note="listed as Jeff Hu among past members in 2023-03"),
        M("Hans Kumar", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Matthew Martone", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Sara Misra", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Akshaya Kesarimangalam Srinivasan", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Tina Tian", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Daniel Vedova", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Thomas Wei", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Tejas Zodage", "masters", None, HC_PROF, near="past masters students", note="seen current on a 2018/2020/2023 capture"),
        M("Jaskaran Grover", "member", None, HC_P18, near="Current RI Students", note="RI student, level not stated"),
        M("Simon Kalouche", "member", [None, 2016], HC_P18, near="Past RI Students", note="listed with year 2016"),
        M("Arun Srivatsan Rangaprasad", "member", [None, 2018], HC_P18, near="Past RI Students", note="listed with year 2018"),
        M("Hadi Salman", "member", [None, 2018], HC_P18, near="Past RI Students", note="listed with year 2018"),
        M("Ralph Boirum", "staff", None, HC_LAB, near="current staff"),
        M("Liyao Chang", "staff", None, HC_LAB, near="current staff"),
        M("Je Choi", "staff", None, HC_LAB, near="current staff"),
        M("Jinwoo Choi", "staff", None, HC_LAB, near="current staff"),
        M("Yann Duband", "staff", None, HC_LAB, near="current staff"),
        M("Eric Foote", "staff", None, HC_LAB, near="current staff"),
        M("Yizhu Gu", "staff", None, HC_LAB, near="current staff"),
        M("Yuxin Guo", "staff", None, HC_LAB, near="current staff"),
        M("Erik Kahn", "staff", None, HC_LAB, near="current staff"),
        M("Youssef Khaky", "staff", None, HC_LAB, near="current staff"),
        M("Lu Li", "staff", None, HC_LAB, near="current staff"),
        M("Allen Liu", "staff", None, HC_LAB, near="current staff"),
        M("Yash Manian", "staff", None, HC_LAB, near="current staff"),
        M("Junil Min", "staff", None, HC_LAB, near="current staff"),
        M("Robin Murphy", "staff", None, HC_LAB, near="current staff"),
        M("Madankumar Sathenahally Nagaraju", "staff", None, HC_LAB, near="current staff"),
        M("Owen Simon", "staff", None, HC_LAB, near="current staff"),
        M("Vivaan Singh", "staff", None, HC_LAB, near="current staff"),
        M("Dean Zadok", "staff", None, HC_LAB, near="current staff"),
        M("Haoran Zheng", "staff", None, HC_LAB, near="current staff"),
        M("Brett Zubiate", "staff", None, HC_LAB, near="current staff"),
        M("Hyeonji Ahn", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Omar Aldhaher", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Krish Bafna", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Ananya Bal", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Ailisi Bao", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Kaushik Chavali", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Kulvir Chavda", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("William Chen", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Cho Ling Chu", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Dhruv Dange", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Aaron Ding", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Aragya Goyal", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Arnav Kharbanda", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Joshua Kim", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("David Neiman", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Daniya Nussipbek", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Chinmay Ramamurthy", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Mithun Roy", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Kaylie Shelton", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Prasanna Kettavarapalyam Sriganesh", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Prakrit Tyagi", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Roland Zhang", "member", None, HC_LAB, near="current student", note="student member, level not stated"),
        M("Khush Agrawal", "member", None, HC_LAB, near="past members"),
        M("Annanya", "member", None, HC_LAB, near="past members"),
        M("Arkadeep Chaudhury", "member", None, HC_LAB, near="past members"),
        M("Dingkun Guo", "member", None, HC_LAB, near="past members"),
        M("Joshua Spisak", "member", None, HC_LAB, near="past members"),
        M("Xinyu Wang", "member", None, HC_LAB, near="past members"),
        M("Greg Armstrong", "staff", None, HC23, near="staff Members"),
        M("Tyler Bobik", "staff", None, HC23, near="staff Members"),
        M("Ryan Darnley", "staff", None, HC23, near="staff Members"),
        M("Thomas Detlefsen", "staff", None, HC23, near="staff Members"),
        M("Geordan Gutow", "staff", None, HC23, near="staff Members"),
        M("David Kohanbash", "staff", None, HC23, near="staff Members"),
        M("James Maier", "staff", None, HC23, near="staff Members"),
        M("Andrew Orekhov", "staff", None, HC23, near="staff Members"),
        M("Rishabh Pahuja", "staff", None, HC23, near="staff Members"),
        M("Beau Pollard", "staff", None, HC23, near="staff Members"),
        M("Tejas Rane", "staff", None, HC23, near="staff Members"),
        M("Zhongqiang Ren", "staff", None, HC23, near="staff Members"),
        M("Nathaniel Shoemaker-Trejo", "staff", None, HC23, near="staff Members"),
        M("Shambhavi Singh", "staff", None, HC23, near="staff Members"),
        M("Changsheng Su", "staff", None, HC23, near="staff Members"),
        M("Parvathiswara Bhaskar Vundurthy", "staff", None, HC23, near="staff Members"),
        M("Rohan Walia", "staff", None, HC23, near="staff Members"),
        M("Tanner Aikens", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Namya Bagree", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Ryan Bao", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Yilin Cai", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Jasmine Cheng", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Brian Chien", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Paul Dreyer", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Chi Gao", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Daniel Gomez", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Michelle Heo", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Mithril Hugunin", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Adam Johnson", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Douglas Johnson", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Ajinkya Kamat", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Xinyue Lai", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Samuel Lapides", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Aria Lorenz", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Grayson Moyer", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Nicholas Murolo", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Ajinkya Mukund Nande", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Chase Noren", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Vaidehi Patil", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Lee Poirier", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Yash Prakash", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Fujun Ruan", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Arushi Singh", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Kevin Song", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Himanshu Thakur", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("John Yordy", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Rohan Zeng", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Brian Zhang", "member", None, HC23, near="student Members", note="student member, level not stated"),
        M("Bassam Bikdash", "member", None, HC23, near="past Members", note="past member on the RI lab page (RI site in this form since 2017)"),
        M("Estevan Chairez", "member", None, HC23, near="past Members", note="past member on the RI lab page (RI site in this form since 2017)"),
        M("Sanil Pande", "member", None, HC23, near="past Members", note="past member on the RI lab page (RI site in this form since 2017)"),
        M("Harsh Sharma", "member", None, HC23, near="past Members", note="seen as student member in 2020-05"),
        M("Yunfei Shi", "member", None, HC23, near="past Members", note="seen as student member in 2020-05"),
        M("Wendy Summer", "member", None, HC23, near="past Members", note="seen as student member in 2020-05"),
        M("Stefan Zhu", "member", None, HC23, near="past Members", note="seen as student member in 2020-05"),
        M("H. Benjamin Brown", "staff", None, HC20, near="staff Members"),
        M("Matthew Dworman", "staff", None, HC20, near="staff Members"),
        M("Zhaoyuan Gu", "staff", None, HC20, near="staff Members"),
        M("Charles Hart", "staff", None, HC20, near="staff Members"),
        M("Shengjie Hu", "staff", None, HC20, near="staff Members"),
        M("Rohan James", "staff", None, HC20, near="staff Members"),
        M("Nicholas Paiva", "staff", None, HC20, near="staff Members"),
        M("Sumangala Patki", "staff", None, HC20, near="staff Members"),
        M("James R. Picard", "staff", None, HC20, near="staff Members"),
        M("Vinit Sarode", "staff", None, HC20, near="staff Members"),
        M("Michael Schwerin", "staff", None, HC20, near="staff Members"),
        M("Nayana Suvarna", "staff", None, HC20, near="staff Members"),
        M("Andrew Wilson", "staff", None, HC20, near="staff Members"),
        M("Yigit Yakupoglu", "staff", None, HC20, near="staff Members"),
        M("Abha Agrawal", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Alex Baikovitz", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Anika Banga", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Annie Chen", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Sarah Costrell", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Xinze Deng", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Joseph Gnehm", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Quint Hester", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("William Paivine III", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Adrian Kager", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Justin Kerr", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Maya Liu", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Zachary Masciopinto", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Justin Mitchell", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Victoria Ortega", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Roshan Pradhan", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Kalee Rozylowicz", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Muhammad Suhail Saleem", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Harvey Shi", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Kenneth Sladick", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Cole Sorkness", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Jocelyn Su", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Michael Tatum", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Tianyu Wang", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("James Wong", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Shuo Yang", "member", None, HC20, near="student Members", note="student member, level not stated"),
        M("Daphne Zhou", "member", None, HC20, near="student Members", note="student member, level not stated"),
    ],
    pubs=[PUB("http://biorobotics.ri.cmu.edu/papers/index.php", mode="css:p", title_css="i")],
    notes=("Biorobotics Lab site (biorobotics.ri.cmu.edu, also cs.cmu.edu/~choset) has no people page "
           "(people/index.php 404). Members from the RI lab page robotics-groups/biorobotics (live + 2020-05 and "
           "2023-03 captures; staff/student/past lists, co-head Matthew Travers is faculty and not recorded) and the "
           "PI's RI faculty profile (live Students/Affiliates tab + 2018-07 capture with dated past RI students). "
           "Student members on the lab page include many MechE/ECE/CSD project students whose level is not stated "
           "(role member). Skipped: pre-2016 past students on the profile (Abcouwer 2014, Abraham 2004, Conner 2007, "
           "Degani 2010, Deo 2014, Ford 2014, Fox 2009, Morales 2006, Morse 2011, Ponte 2014, Rollinson 2014, "
           "Skaff 2007, Tesch 2013, Wagner 2015, Greenfield); undated past masters not seen current in any capture "
           "(Yu Chen, Xiang (Shawn) Fei, Gabriel Olin, Haowen Shi - all already held); 'Annanya' (single name in "
           "live past members). Jeff Hu (2023 past members) recorded once as Jiaheng Hu. Profile affiliates overlap "
           "the lab page staff/student lists and are recorded from there."),
    blocked=[],
)

# ---------------------------------------------------------------- Tianqi Chen
TC_CSD = "https://csd.cmu.edu/people/faculty/tianqi-chen"
TC_CAT = "https://catalyst.cs.cmu.edu/"
D["Tianqi Chen"] = dict(
    lab_site="https://catalyst.cs.cmu.edu/",
    people_page=TC_CAT,
    people_pages=[TC_CAT, TC_CSD, WB + "20210117150140id_/https://catalyst.cs.cmu.edu/"],
    members=[
        M("Bohan Hou", "phd", None, TC_CSD, near="Advisees"),
        M("Hongyi Jin", "phd", None, TC_CSD, near="Advisees"),
        M("Ruihang Lai", "phd", None, TC_CSD, near="Advisees"),
        M("Yixin Dong", "phd", None, TC_CAT, near="PhD Students",
          note="Catalyst shared page; recorded because already held under this PI"),
        M("Byungsoo Jeon", "phd", [None, 2024], TC_CAT, q="Byungsoo Jeon Ph.D., 2024.",
          note="Catalyst alumni; already held under this PI"),
        M("Pratik Fegade", "phd", [None, 2023], TC_CAT, q="Pratik Fegade Ph.D., 2023.",
          note="Catalyst alumni; already held under this PI"),
        M("Charlie Ruan", "masters", None, TC_CAT, near="Masters Students",
          note="Catalyst shared page; already held under this PI (Charlie F. Ruan)"),
    ],
    pubs=[PUB("https://catalyst.cs.cmu.edu/publications.html", mode="auto",
              note="shared Catalyst group list (Tianqi Chen, Zhihao Jia, Beidi Chen, Gibbons, Mowry, ...)")],
    notes=("tqchen.com links 'Group' to the CMU Catalyst group (catalyst.cs.cmu.edu), a joint ML-systems group of "
           "12 faculty (B. Chen, T. Chen, Dettmers, Ganger, Gibbons, Hsu, Jia, Mowry, Skarlatos, Talwalkar, Vinayak, "
           "Xing) whose People section (1 postdoc, 24 PhD, 7 visiting, 24 masters, 8 undergrads, 28 alumni live; "
           "2021-01 capture lists only Fegade, Jaasaari, Jeon) does not say who advises whom; held data shows many "
           "of them belong to Zhihao Jia, Gibbons, Ganger, Xing, Sherry etc. Per the shared-center rule only people "
           "attributable to this PI are recorded: the three CSD-profile advisees, plus Catalyst entries already held "
           "under this PI. Orchestrator may want a separate decision on the unattributed Catalyst masters/undergrads "
           "(e.g. MLC-LLM contributors). Catalyst publications page added (shared list). No personal students or "
           "publications page on tqchen.com."),
    blocked=[],
)

# ---------------------------------------------------------------- Nicolas Christin
NC = "https://www.andrew.cmu.edu/user/nicolasc/"
NC17 = WB + "20170101223846id_/http://www.andrew.cmu.edu/user/nicolasc/"
NC20 = WB + "20200110085546id_/http://www.andrew.cmu.edu/user/nicolasc/"
D["Nicolas Christin"] = dict(
    lab_site=NC,
    people_page=NC,
    people_pages=[NC, NC17, NC20],
    members=[
        M("Taro Tsuchiya", "phd", None, NC, q="six incredible Ph.D. students: Taro Tsuchiya ( SCS , Societal Computing )"),
        M("Alexandra Nisenoff", "phd", None, NC, q="Alexandra Nisenoff ( SCS , Societal Computing , co-advised with Lorrie Cranor )"),
        M("Jenny Tang", "phd", None, NC, q="Jenny Tang ( SCS , Societal Computing , co-advised with Lujo Bauer )"),
        M("Hobin Kim", "phd", None, NC, q="Hobin Kim ( SCS , Societal Computing , co-advised with Lujo Bauer )"),
        M("Carolina Carreira", "phd", None, NC, q="Carolina Carreira ( SCS and CMU|Portugal program"),
        M("Diana Fernandes", "phd", None, NC, q="Diana Fernandes ( EPP and CMU|Portugal program"),
        M("Enze “Alex” Liu", "postdoc", None, NC, q="one postdoc, Enze “Alex” Liu"),
        M("Arjun Brar", "staff", None, NC, q="Arjun Brar (former research programmer, now at Meta"),
        M("Kyle Soska", "phd", [None, 2021], NC, q="Kyle Soska (Ph.D., ECE , 2021)"),
        M("Zachary Weinberg", "phd", [None, 2018], NC, q="Zachary Weinberg (Ph.D., ECE , 2018)",
          note="then teaching postdoc in CMU CS"),
        M("Mahmood Sharif", "phd", [None, 2019], NC, q="Mahmood Sharif (Ph.D., ECE , 2019, co-advised with Lujo Bauer )"),
        M("János Szurdi", "phd", [None, 2020], NC, q="János Szurdi (Ph.D., ECE , 2020)"),
        M("Kyle Crichton", "phd", [None, 2023], NC, q="Kyle Crichton (Ph.D., EPP , 2023, co-advised with Lorrie Cranor )"),
        M("Daisuke Kawai", "phd", [None, 2024], NC, q="Daisuke Kawai (Ph.D., EPP , 2024)"),
        M("Alejandro Cuevas", "phd", [None, 2025], NC, q="Alejandro Cuevas (Ph.D., Societal Computing , SCS , 2025)"),
        M("Jin-Dong (Mark) Dong", "phd", [None, 2025], NC, q="Jin-Dong (Mark) Dong (Ph.D., ECE , 2025)"),
        M("Timothy Vidas", "phd", [None, 2016], NC, q="Timothy Vidas (Ph.D., ECE , 2016)"),
        M("Luís Brandão", "phd", [None, 2016], NC, q="Luís Brandão (Ph.D., ECE / U. Lisbon , 2016; co-advised with Alysson Bessani )"),
        M("Aurelia Augusta", "phd", None, NC20, q="Aurelia Augusta ( EPP , co-advised with Lorrie Cranor )",
          note="PhD student in 2020 capture; later listed as M.Sc. Societal Computing 2021 on live page"),
        M("Nicolas Szwajcok", "masters", [None, 2026], NC, q="Nicolas Szwajcok (M. Sc., EPFL , 2026)", note="EPFL master's, supervised"),
        M("Léo Alvarez", "masters", [None, 2023], NC, q="Léo Alvarez (M. Sc., EPFL , 2023)"),
        M("William Luca", "masters", [None, 2022], NC, q="William Luca (M. Sc., INI , 2022)"),
        M("Xin Huang", "masters", [None, 2019], NC, q="Xin Huang (M. Sc., INI, 2019)"),
        M("Behtash Banihashemi", "masters", [None, 2019], NC, q="Behtash Banihashemi (M.Sc, EPP , 2019)"),
        M("Eugene Lemuel Garcia", "masters", [None, 2017], NC, q="Eugene Lemuel Garcia (M. Sc., INI, 2017)"),
    ],
    pubs=[PUB(NC + "papers/", mode="block", note="entries are plain-text citations; title sits between authors and venue")],
    notes=("No separate lab site: the group is described on the PI homepage (Research group section) with current "
           "students, dated PhD alumni and dated master's alumni; read live plus Wayback 2017 and 2020 captures "
           "(2017: Weinberg, Soska, Szurdi, Sharif; 2020 adds Crichton, Augusta, Cuevas, Dong). Undated postdocs "
           "(Alain Forget, Benjamin Johnson, Steve Matsumoto) and undated visitors (Xiao Hui Tai, Diogo Barradas, "
           "Dominic Deuber) not recorded; pre-2016 alumni skipped. Publications page (papers/) parsed by block mode; "
           "tool titles show as link labels because titles are plain text in the citation. Also papers-topic page "
           "exists (same papers by topic)."),
    blocked=[],
)

# ---------------------------------------------------------------- Edmund Clarke
EC = "http://www.cs.cmu.edu/~emc/students.html"
D["Edmund Clarke"] = dict(
    lab_site="http://www.cs.cmu.edu/~emc/",
    people_page=EC,
    people_pages=[EC],
    members=[
        M("Soon Ho Kong", "phd", None, EC, near="Current Graduate Students"),
        M("Qinsi Wang", "phd", None, EC, near="Current Graduate Students"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~emc/publications.html", mode="auto")],
    notes=("PI died 2020. Live emc/students.html lists Current Graduate Students (Soon Ho Kong, Qinsi Wang), "
           "dated PhD alumni (latest Komuravelli 2015, so pre-window, skipped) and postdocs with dates ending 2015 "
           "(skipped, 2014-2015 and earlier). Wayback of students.html (2016-2020 captures) could not be read: "
           "archive.org CDX refused (wayback-backoff) at the time of this pass. Selected-publications page has only "
           "9 classic entries (one in window: Model Checking 2nd ed. 2018)."),
    blocked=[],
)

# ---------------------------------------------------------------- William W Cohen
WC = "http://www.cs.cmu.edu/~wcohen/"
WCG = "https://wwcohen.github.io/"
D["William W Cohen"] = dict(
    lab_site=WCG,
    people_page=WC,
    people_pages=[WC, WCG],
    members=[
        M("Daniel Spokoyny", "phd", None, WC, q="Students and other colleagues Daniel Spokoyny, LTI PhD student"),
        M("Katie Rivard Mazaitis", "staff", None, WC, q="Long-term colleagues Katie Rivard Mazaitis , research programmer/analyst"),
        M("Jay Yoon Lee", "phd", None, WCG, q="Students and other colleagues Former students/colleagues: Daniel Spokoyny, LTI PhD student, co-supervised with Taylor Berg-Kirkpatrick. Katie Rivard Mazaitis , research programmer/analyst Jay Yoon Lee",
          note="CSD PhD student co-advised with Jaime Carbonell (github.io copy of the page)"),
        M("Wen Haw Chong", "visitor", [2015, 2016], WC, q="Wen Haw Chong (PhD student at Singapore Management University, visted CMU in 2015-2016)"),
    ],
    pubs=[PUB(WCG + "pubs-s.html", mode="auto"), PUB(WCG + "pubs.html", mode="auto")],
    notes=("Lab site is the PI homepage (cs.cmu.edu/~wcohen, mirrored at wwcohen.github.io); no separate people page, "
           "the 'Students and other colleagues' section lists current students, research staff and a long list of "
           "undated former students/colleagues. Undated alumni were skipped (they cannot be shown to be in 2016-2026 "
           "from this page); undated master's students (Ezra Winston, Lanxio Xu, Yuxing Zhang, Jakob Bauer, Kavya "
           "Srinet, Bhawna Juneja) and visitor Qiao Jin are also undated. Wayback captures were not read because "
           "archive.org was in shared back-off during this pass. Publications: recent (pubs-s.html) and complete "
           "(pubs.html) lists added."),
    blocked=[],
)

# ---------------------------------------------------------------- Phillip Compeau
D["Phillip Compeau"] = dict(
    lab_site=None,
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes=("Teaching Professor / Assistant Dean for Innovation in Computing Education (CBD). compeau.cbd.cmu.edu does "
           "not resolve (ConnectionError) and the CBD profile (cmu.edu/cbd/people/compeau.html) lists only highlighted "
           "publications (textbooks, teaching papers) and online-education projects, no students or group. "
           "A web search found no lab roster. Wayback of compeau.cbd.cmu.edu could not be read (archive.org shared "
           "back-off), so any older group listing there is unchecked. No publications page added."),
    blocked=[],
)

# ---------------------------------------------------------------- Vincent Conitzer
VCF = "http://www.cs.cmu.edu/~focal/people.html"
VCH = "https://www.cs.cmu.edu/~conitzer/"
D["Vincent Conitzer"] = dict(
    lab_site="http://www.cs.cmu.edu/~focal/",
    people_page=VCF,
    people_pages=[VCF, VCH],
    members=[
        M("Caspar Oesterheld", "phd", None, VCF, q="Caspar Oesterheld Assistant Director, PhD student in Computer Science"),
        M("Vojta Kovarik", "postdoc", None, VCF, q="Vojta Kovarik Postdoctoral researcher in Computer Science"),
        M("Ivan Geffner", "postdoc", None, VCF, q="Ivan Geffner Postdoctoral researcher in Computer Science"),
        M("Chris van Merwijk", "phd", None, VCF, q="Chris van Merwijk PhD student in Computer Science"),
        M("Emanuel Tewolde", "phd", None, VCF, q="Emanuel Tewolde PhD student in Computer Science"),
        M("Ratip Emin Berker", "phd", None, VCF, q="Ratip Emin Berker PhD student in Computer Science"),
        M("Jiayuan Liu", "phd", None, VCF, q="Jiayuan Liu PhD student in Computer Science"),
        M("Emery Cooper", "staff", None, VCF, q="Emery Cooper Research Associate"),
        M("Alexander Heckett", "undergraduate", None, VCF, q="Alexander Heckett Undergraduate researcher"),
        M("Gabriele Farina", "staff", None, VCF, q="Gabriele Farina Research scientist in Computer Science (alum; now on the faculty at MIT)",
          note="research scientist at CMU in the Sandholm group; listed as FOCAL alum"),
        M("Hanrui Zhang", "phd", [None, 2023], VCF,
          q="Hanrui Zhang PhD student in Computer Science (alum; now on the faculty at the Chinese University of Hong Kong)",
          note="homepage: CS PhD 2023, SCS Distinguished Dissertation honorable mention 2023"),
        M("Akash Kundu", "visitor", [2026, 2026], VCH, q="Akash Kundu (Cooperative AI Research Fellow, 2026)"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~focal/publications.html", mode="auto")],
    notes=("Lab site is FOCAL (cs.cmu.edu/~focal); PI homepage cs.cmu.edu/~conitzer has the RESEARCH GROUP list. The PI "
           "moved from Duke to CMU in 2022, so Duke-era alumni (Yuan Deng, Rupert Freeman, Yu Cheng, Catherine Moon, "
           "Michael Albert, Kolb, Li, older) are not recorded; only people the sources place at CMU. Haoming Li "
           "(M.S. 2020) and Kenzie Doyle (post-bac 2016-2020) are probably Duke-era and were skipped. Mingyu Guo (undated sabbatical visitor) skipped. PI homepage "
           "publications are plain text and parse poorly, so only the FOCAL publications page was added."),
    blocked=[],
)

# ---------------------------------------------------------------- Stelian Coros
D["Stelian Coros"] = dict(
    lab_site=None,
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes=("CMU RI faculty 2015-2019, now ETH Zurich (Computational Robotics Lab, crl.ethz.ch). Searched: RI faculty "
           "index (only a Wayback copy), RI WordPress search (news posts only, no people page), "
           "ri.cmu.edu/ri-people/stelian-coros (404), cs.cmu.edu/~scoros/index.html (one-paragraph ETH page, no "
           "students), crl.ri.cmu.edu (does not resolve), web search (no roster). The CMU-era lab site could not be "
           "read from Wayback because archive.org was in shared back-off. No people or publications page usable."),
    blocked=[],
)

# ---------------------------------------------------------------- Tom Costello
TC = "https://www.thcostello.com/"
D["Tom Costello"] = dict(
    lab_site=TC,
    people_page=TC,
    people_pages=[TC],
    members=[
        M("Kenneth Diao", "phd", None, TC, q="The lab is Thomas Costello (director) and Ph.D. students Kenneth Diao"),
        M("Duncan Wood", "phd", None, TC, q="Ph.D. students Kenneth Diao, Duncan Wood"),
        M("Ali Levontin", "phd", None, TC, q="Ph.D. students Kenneth Diao, Duncan Wood, and Ali Levontin"),
    ],
    pubs=[PUB(TC + "research.html", mode="auto")],
    notes=("Viewpoints Lab section of thcostello.com lists the director and three SDS PhD students; no separate "
           "people page. PI joined CMU (SDS, affiliated HCII) after an MIT Sloan postdoc 2022-24, so the lab is "
           "recent and Wayback was not needed. CMU SDS faculty page has no group list. Complete publications page "
           "added (auto mode reads titles after the author list)."),
    blocked=[],
)
