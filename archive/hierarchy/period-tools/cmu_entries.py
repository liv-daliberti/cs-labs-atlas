# CMU appointment-period entries, exec'd by cmu_build.py (E, old, oid, period, nochange, SCH, TODAY in scope).
# ruff: noqa
DEAN = 'https://www.dean.scs.cmu.edu/new-faculty/%d.html'
SCSDIR = 'https://web.archive.org/web/20260210063230id_/https://www.cs.cmu.edu/directory/api/v1/all.json'

# ---------------------------------------------------------------- SCS / Dietrich targets without override periods
period('Alessandro Acquisti', '2003', None, TODAY, 'year', [
    E(SCH + '48-alessandro-acquisti', 'Assistant Professor of Information Technology and Public Policy Carnegie Mellon University, Heinz College, United States 2003 - 2009', 'faculty_start_statement', 'CMU Scholars (Elements) academic positions'),
    E(SCH + '48-alessandro-acquisti', 'Trustees Chair in Information Technology and Public Policy Carnegie Mellon University, Heinz College, Pittsburgh, United States 1 Jan 2020 - present', 'faculty_profile', 'current position (asof)'),
], 'Start: CMU Scholars lists his Heinz College assistant professorship from 2003 (year only). Ongoing: Trustees Chair 2020-present on the live profile. Home appointment is Heinz College; the S3D/Societal Computing listings are affiliated.')

period('Alan Black', '1999', '2022-06', None, 'month', [
    E('https://en.wikipedia.org/wiki/Alan_W._Black', 'he took a research faculty position at Carnegie Mellon in 1999. In 2008 he became a regular faculty member with tenure at CMU', 'faculty_start_statement', 'Wikipedia'),
    E('http://www.cs.cmu.edu/~awb/', 'In June 2022, I retired as a full professor from CMU to move to Anchorage, Alaska', 'emeritus_transfer', 'own CMU homepage, headed "Retired Professor"'),
], 'Start: research faculty position at CMU in 1999 (year only; tenured faculty from 2008). End: retired as a full professor in June 2022 (his own homepage); later "Retired Professor" years are not appointment years, so the rejected 2023/2024/2026 papers stay outside. Fills the 2018 gap between the 2017 and 2019 LTI listings.',
    departure='Retired from CMU (full professor, LTI) in June 2022; now "Retired Professor".')

nochange('Avrim Blum', 'Rejected 2022 and 2025 papers postdate his move to TTIC in 2017; listings cover 2016-2021 (the 2018-2021 MLD affiliated/adjunct listings already describe him at TTIC). Nothing to add.',
    departure='Left the CMU CSD faculty in 2017 to become Chief Academic Officer of the Toyota Technological Institute at Chicago.',
    dep_ev=[E('https://ttic.edu/faculty/blum', 'He then served on the faculty in the Computer Science Department at Carnegie Mellon University from 1992 to 2017. In 2017 he joined the Toyota Technological Institute at Chicago as Chief Academic Officer.', 'departure_announcement', 'TTIC faculty page')])

nochange('Brett Browning', 'Owner-named. Rejected 2017 and 2018 papers postdate his departure: by 2017 he was VP of Robotics at Argo AI, described by CMU as a former RI/NREC senior systems scientist who had since been at Uber ATC. No source dates the exact exit from CMU (Uber ATC hired NREC staff in 2015), so the only covered year (2016, from an April 2016 RI listing) may itself be stale; no period is proposed.',
    departure='Left CMU (RI/NREC Senior Systems Scientist) for Uber ATC, then Argo AI (VP Robotics by 2017); exact exit date not found.',
    dep_ev=[E('https://web.archive.org/web/20250326003803id_/https://www.cmu.edu/cmtoday/business_robotics/a-billion-dollar-idea-cmu-veterans-head-automotive-ai-startup/index.html', 'Brett Browning, vice president of robotics, is a former senior systems scientist at the Robotics Institute and NREC and formerly of Uber ATC.', 'departure_announcement', 'CMU Today 2017 story on Argo AI (Wayback)')])

nochange('Carlos Busso', 'Rejected 2024 papers predate (or fall in the unresolvable start year of) his CMU appointment: his LTI profile gives UT Dallas Full Professor 2020-2024, SCS lists him among 2024 hires, and he is absent from the LTI faculty listing of 2025-01-05 (present 2025-09-04). Listings already cover 2025-2026.',
    dep_ev=[E('https://lti.cmu.edu/people/faculty/busso-carlos.html', 'Associate Professor (2015-2020), and Full Professor (2020-2024) in the Department of Electrical and Computer Engineering', 'faculty_profile', 'prior UT Dallas appointment through 2024'),
            E(DEAN % 2024, 'Carlos Busso Professor Language Technologies Institute', 'appointment_announcement', 'SCS Recent Faculty Hires / 2024 (year only)')])

nochange('Vincent Conitzer', 'Rejected 2018 and 2021 papers predate his 2022 move from Duke; the site period cmu_faculty_period_0 (2022-) and listings 2022-2026 are right.',
    dep_ev=[E(DEAN % 2022, 'Vince Conitzer Professor Computer Science Department/Machine Learning Department', 'appointment_announcement', 'SCS Recent Faculty Hires / 2022')])

nochange('Stelian Coros', 'Rejected 2018 papers postdate his move to ETH Zurich (his CMU role is now adjunct); RI listings cover 2016-2017.',
    departure='Moved to ETH Zurich (Assistant Professor, Computational Robotics Lab); CMU role now adjunct. Year of move not stated on the captured page (RI lists him as Assistant Professor in 2017).',
    dep_ev=[E('https://www.cs.cmu.edu/~scoros/index.html', 'I am an Assistant Professor in the Department of Computer Science at ETH Zurich , where I lead the Computational Robotics Lab (CRL) . I am also an Adjunct Professor in the Robotics Institute at Carnegie Mellon University .', 'departure_announcement', 'own CMU homepage')])

period('Dannie Durand', '2000-09', None, TODAY, 'month', [
    E('https://www.cmu.edu/cmnews/020308/020308_ddurand.html', 'as an associate professor of biological sciences and computer science in September 2000', 'faculty_start_statement', 'Carnegie Mellon News, March 2002'),
    E('https://www.cmu.edu/bio/people/faculty/index.html', 'Dannie Durand Associate Professor', 'dept_listing:Biological Sciences', 'live Biological Sciences faculty listing (asof)'),
], 'Start: joined CMU as associate professor of biological sciences and computer science in September 2000 (home department Biological Sciences; the CBD listing is an affiliated appointment). Ongoing on the live Biological Sciences listing.')

period('Maxine Eskenazi', '2015-04-25', '2022-12-31', None, 'day', [
    E('https://web.archive.org/web/20150425214534id_/http://www.lti.cs.cmu.edu:80/directory/all/154/1', 'Maxine Eskenazi Principal Systems Scientist', 'faculty_start_lower_bound', 'earliest LTI faculty directory capture examined'),
    E('https://www.cs.cmu.edu/~max/', 'Carnegie Mellon University, retiring on December 31, 2022', 'emeritus_transfer', 'own CMU homepage'),
], 'Start is a lower bound: listed as LTI Principal Systems Scientist (her PI-basis role, CMU special faculty) on 2015-04-25; she was at the LTI long before (no dated start statement in HTML; the CV is a PDF). End: retiring on 2022-12-31 per her homepage, so rejected 2023/2024 papers stay outside; fills the 2018 gap.',
    departure='Retired from CMU on 2022-12-31 (homepage).')

period('Gabe Gomes', '2022-01', None, TODAY, 'month', [
    E('https://www.cmu.edu/chemistry/news-events/2021/0827_introducing_new_faculty.html', 'In January 2022, Gabriel Gomes will join Carnegie Mellon University as assistant professor in a joint appointment with the Department of Chemistry and Department of Chemical Engineering.', 'appointment_announcement', 'CMU Chemistry news, Aug. 27, 2021'),
    E(SCH + '11274-gabriel-gomes', 'Gabriel Gomes Assistant Professor Chemistry', 'faculty_profile', 'live CMU Scholars profile (asof)'),
], 'Start: joint Chemistry/Chemical Engineering assistant professorship from January 2022 (announced Aug. 2021); MLD listing is an affiliated appointment. Ongoing.')

nochange('Albert Gu', 'Rejected 2016 and 2023 papers predate his appointment: MLD still listed him as "Incoming Assistant Professor" on 2023-09-24 (he is in the SCS 2023 hiring cohort); listings cover 2024-2026.',
    dep_ev=[E('https://web.archive.org/web/20230924205715id_/https://www.ml.cmu.edu/people/core-faculty.html', 'Albert Gu Incoming Assistant Professor, Machine Learning, School of Computer Science', 'dept_listing:MLD', 'not yet in post in Sept. 2023')])

period('Maggie Henderson', '2024-09-16', None, TODAY, 'day', [
    E('https://web.archive.org/web/20240916050532id_/https://www.cmu.edu/dietrich/psychology/directory/core-training-faculty/henderson-maggie.html', 'Maggie Henderson Assistant Professor of Psychology and Neuroscience Institute, Assistant Professor of Machine Learning (Affiliated)', 'faculty_start_lower_bound', 'earliest Wayback capture of her Psychology profile'),
    E('https://www.cmu.edu/dietrich/psychology/news/2023/summer-oct-postdoc-news.html', 'Maggie Henderson has a new preprint out on bioRxiv', 'pre_appointment_role', 'Psychology postdoc news, 2023: still a postdoc'),
    E('https://www.cmu.edu/ni/people/faculty/maggie-henderson', 'Maggie Henderson Assistant Professor of Psychology and Neuroscience Institute, Assistant Professor of Machine Learning (Affiliated)', 'faculty_profile', 'live Neuroscience Institute profile (asof)'),
], 'Owner-named. Start is a lower bound: the earliest capture of her Psychology faculty profile (2024-09-16). Her CV (PDF, not quotable here) gives Assistant Professor 2024-present after a 2021-2024 postdoc in the Neuroscience Institute (Wehbe/Tarr), and the 2023 Psychology postdoc news confirms the postdoc role; postdoc years do not count, so 2021-2023 papers stay outside and 2024 papers before Sept. 16 stay unresolved. Home: Psychology + Neuroscience Institute; MLD is an affiliated title.')

period('Marijn Heule', '2019-08', None, TODAY, 'month', [
    E(DEAN % 2019, 'Marijn Heule Associate Professor Computer Science Department', 'appointment_announcement', 'SCS Recent Faculty Hires / 2019'),
    E('https://www.cs.cmu.edu/~mheule/', 'Fall 2019: 15-816 Advanced Topics in Logic: Automated Reasoning and Satisfiability', 'faculty_profile', 'teaching record on his CMU homepage'),
    E('https://www.cmu.edu/news/stories/archives/2020/october/scientists-solve-geometry-problem.html', 'an associate professor of computer science who joined CSD last August', 'faculty_start_statement', 'CMU News, Oct. 2020'),
    E(SCSDIR, '"n":"Marijn Heule","aff":"Faculty","titl":["Associate Professor"]', 'dept_listing:CSD', 'SCS directory 2026-02 (asof)'),
], 'New period replacing the year-only site period cmu_faculty_period_21 (start 2019), so that 2019 papers after he arrived resolve. He joined CSD in August (CMU News, read with the 2019 SCS hiring page and his Fall 2019 course; he was at UT Austin until 2019). Ongoing. Rejected 2016-2018 papers are pre-appointment (UT Austin).')

period('Hanan Hibshi', '2021-08', None, TODAY, 'month', [
    E(SCH + '7977-hanan-hibshi', 'Assistant Teaching Professor Carnegie Mellon University, Information Networking Institute, Pittsburgh, United States Aug 2021 - present', 'faculty_start_statement', 'CMU Scholars academic positions'),
], 'Start: INI Assistant Teaching Professor from Aug 2021 (her census role). Ongoing. Rejected 2016 and 2020 papers predate the appointment (CMU PhD student until 2018). Note: her covered 2017-2019 and 2021-2022 years come from Societal Computing student/alumni rosters, not faculty listings.')

nochange('Zhihao Jia', 'Rejected 2021 papers predate (or at most marginally overlap) his appointment: he is in the SCS 2021 hiring cohort but absent from the CSD faculty listing of 2021-10-16, and his first CMU course was Spring 2022; listings cover 2022-2026.',
    dep_ev=[E(DEAN % 2021, 'Zhihao Jia Assistant Professor Computer Science Department', 'appointment_announcement', 'SCS Recent Faculty Hires / 2021 (year only)'),
            E('https://www.cs.cmu.edu/~zhihaoj2/', '15-849 Machine Learning Systems : spring 2022', 'faculty_profile', 'earliest course on his teaching list')])

nochange('Jason Li', 'Rejected 2017-2022 papers are from his CMU PhD (ACO) and pre-faculty years; he joined CSD as assistant professor with the 2023 cohort and listings cover 2023-2026.',
    dep_ev=[E(DEAN % 2023, 'Jason Li Assistant Professor Computer Science Department More Info Education B.S. Computer Science and Mathematics Ph.D. Algorithms and Combinatorial Optimization (ACO), Carnegie Mellon University', 'appointment_announcement', 'SCS Recent Faculty Hires / 2023')])

nochange('Lei Li', 'Rejected 2016-2021 papers predate his 2023 LTI appointment (SCS 2023 cohort); listings cover 2023-2026.',
    dep_ev=[E(DEAN % 2023, 'Lei Li Assistant Professor Language Technologies Institute', 'appointment_announcement', 'SCS Recent Faculty Hires / 2023')])

nochange('Zachary Chase Lipton', 'Rejected 2016-2017 papers predate his January 2018 start; listings cover 2018-2026.',
    dep_ev=[E('https://web.archive.org/web/20180102153844id_/http://ml.cmu.edu:80/people/affiliated-faculty.html', 'Zachary Lipton Assistant Professor (starting January 2018)', 'dept_listing:MLD')])

nochange('David R. Mortensen', 'Site period cmu_faculty_period_45 (2018-, from his CV: Systems Scientist 2018-2023) stands. The 2016 papers predate any faculty role; in 2017 the LTI listed him as "Research Scientist" on its research-staff/postdoc page, not a faculty appointment. The 2018 papers stay in the year-only start year: no HTML source gives the month (CV is a PDF).',
    dep_ev=[E('https://web.archive.org/web/20170523210241id_/http://www.lti.cs.cmu.edu:80/directory/all/154/2729', 'David Mortensen Research Scientist', 'pre_appointment_role', 'LTI directory 154/2729 lists postdocs, visiting scholars and research staff')])

nochange('Richard Peng', 'Rejected 2016, 2017 and 2019 papers predate his 2023 CSD appointment (SCS 2023 cohort); listings cover 2023-2026.',
    dep_ev=[E(DEAN % 2023, 'Richard Peng Associate Professor Computer Science Department', 'appointment_announcement', 'SCS Recent Faculty Hires / 2023')])

period('Aaditya Ramdas', '2018', '2026', None, 'year', [
    E(DEAN % 2018, 'Aaditya Ramdas Assistant Professor Department of Statistics, Courtesy Appointment in the Machine Learning Department', 'appointment_announcement', 'SCS Recent Faculty Hires / 2018 (year only)'),
    E('https://web.stanford.edu/~aramdas/', 'He was a postdoc at UC Berkeley (2015–2018)', 'pre_appointment_role', 'Stanford homepage'),
    E('https://web.archive.org/web/20260710204043id_/https://www.cmu.edu/dietrich/statistics-datascience/people/faculty/aaditya-ramdas.html', 'Aaditya Ramdas Associate Professor', 'faculty_profile', 'last CMU profile capture, July 2026'),
    E('https://web.archive.org/web/20260509140923id_/https://www.stat.cmu.edu/~aramdas/', 'I am moving permanently to Stanford in Fall 2026.', 'departure_announcement', 'CMU homepage, May 2026'),
    E('https://web.stanford.edu/~aramdas/', 'Before that, he was a tenured faculty member at Carnegie Mellon University, in the Machine Learning Department and the Department of Statistics and Data Science.', 'departure_announcement', 'Stanford homepage'),
], 'Start: 2018 (postdoc at Berkeley 2015-2018; SCS 2018 hiring page), year only, so the 2018 papers stay unresolved; the 2017 paper is pre-appointment. End: moved permanently to Stanford in Fall 2026 (CMU profile still active 2026-07-10), year precision. Home: Statistics & Data Science with MLD.',
    departure='Moved permanently to Stanford (Associate Professor, Statistics) in Fall 2026.')

period('Cosma Shalizi', '2006', None, TODAY, 'year', [
    E(SCH + '976-cosma-shalizi', 'Assistant Professor Carnegie Mellon University, Pittsburgh, Pennsylvania, United States 2006 - 2012', 'faculty_start_statement', 'CMU Scholars academic positions'),
    E(SCH + '976-cosma-shalizi', 'Visiting Assistant Professor Carnegie Mellon University, Pittsburgh, Pennsylvania, United States 2005 - 2006', 'pre_appointment_role', 'visiting year not counted'),
    E(SCH + '976-cosma-shalizi', 'Associate Professor with Tenure Carnegie Mellon University, Pittsburgh, Pennsylvania, United States 2014 - present', 'faculty_profile', 'current (asof)'),
], 'Start: Statistics assistant professor from 2006 (the 2005-2006 visiting year does not count). Ongoing as Associate Professor with Tenure, which covers the rejected 2024-2026 papers. Home: Statistics & Data Science.')

nochange('Hong Shen', 'Rejected 2016-2018 papers predate her CMU appointment: PhD at UIUC, first CMU listing as HCII Systems Scientist in March 2019; listings cover 2019-2026.',
    dep_ev=[E('https://web.archive.org/web/20190326020843id_/https://hcii.cmu.edu/people/special-faculty-and-postdocs', 'Hong Shen Systems Scientist', 'dept_listing:HCII', 'earliest listing'),
            E('https://www.andrew.cmu.edu/user/hongs/', 'I received my PhD from the University of Illinois at Urbana-Champaign', 'pre_appointment_role')])

period('Elaine Shi', '2020', None, TODAY, 'year', [
    E('https://cylab.cmu.edu/news/2020/08/12-shi-distinguished-alumni.html', 'a CyLab alum and professor at Cornell University who will join the faculty at CMU this Fall', 'appointment_announcement', 'CyLab news, Aug. 12, 2020'),
    E('https://en.wikipedia.org/wiki/Elaine_Shi', 'before coming back to Carnegie Mellon University as a faculty in Fall 2020', 'faculty_start_statement', 'Wikipedia'),
    E('https://elaineshi.com/', 'I am a Professor with a joint appointment in CSD and ECE at Carnegie Mellon University', 'faculty_profile', 'live homepage (asof)'),
], 'Start: joined CMU (CSD/ECE) in Fall 2020 from Cornell; year precision (2020 is listed anyway). Ongoing: she is still a CMU professor, so the rejected 2025-2026 papers are inside; the 2018 papers are pre-appointment (Cornell).')

nochange('Siddhartha Srinivasa', 'Rejected 2018-2023 papers postdate his fall 2017 move to the University of Washington; the 2017 RI listing shows him only as adjunct.',
    departure='Left the CMU Robotics Institute for the University of Washington (Boeing Endowed Professor) in fall 2017.',
    dep_ev=[E('https://news.cs.washington.edu/2017/01/17/senior-faculty-hires-sidd-srinivasa-and-michael-taylor-set-to-advance-uws-leadership-in-robotics-and-computer-engineering-research', 'Sidd Srinivasa will join UW as the Boeing Endowed Professor in Computer Science & Engineering from his alma mater, The Robotics Institute at Carnegie Mellon University', 'departure_announcement', 'UW CSE news, Jan. 17, 2017 (arrival "this fall")')])

nochange('Wennie Tabib', 'Rejected 2016 and 2018 papers are from her CMU PhD years; she became an RI System Scientist with the 2021 SCS cohort (her 2020-2021 coverage comes from RI postdoctoral-fellow listings).',
    dep_ev=[E(DEAN % 2021, 'Wennie Tabib System Scientist Robotics Institute More Info Education Ph.D. Carnegie Mellon University', 'appointment_announcement', 'SCS Recent Faculty Hires / 2021')])

nochange('Ameet Talwalkar', 'Rejected 2016-2017 papers predate his January 2018 start (UCLA before); listings cover 2018-2026.',
    dep_ev=[E('https://www.ml.cmu.edu/news/news-archive/2016-2020/2017/november/ameet-talwalkar-joins-the-machine-learning-department.html', 'We are very excited to welcome Ameet Talwalkar as an Assistant Professor in the Machine Learning Department starting in January 2018.', 'appointment_announcement', 'MLD news, Nov. 2017')])

period('Michael Tarr', '2009', None, TODAY, 'year', [
    E('https://www.cmu.edu/news/stories/archives/2013/september/sept12_michaeltarr.html', 'Tarr joined Carnegie Mellon in 2009 to co-direct the CNBC', 'faculty_start_statement', 'CMU News, Sept. 2013 (named Psychology department head)'),
    E(SCSDIR, '"n":"Michael Tarr","aff":"Faculty","titl":["Professor"]', 'dept_listing:RI', 'SCS directory 2026-02 (asof): Robotics Institute and Psychology'),
], 'New period: the site period cmu_faculty_period_50 (start 2024) is wrong - its evidence is Maggie Henderson\'s CV, not Tarr\'s. Tarr joined CMU (Psychology/CNBC) in 2009 and remains a professor (Psychology; MLD/RI courtesy). Covers the rejected 2016-2021 papers.')

nochange('Yuanzhi Li', 'Rejected 2018 paper predates his fall 2019 start; rejected 2025-2026 papers postdate his departure: MLD listed him through 2024-09-01 and dropped him by 2024-11-01; he is absent from the SCS directory in 2025-2026. Listings cover 2019-2024.',
    departure='Left the MLD faculty in autumn 2024 (in the core-faculty listing 2024-09-01, gone 2024-11-01); destination not confirmed.',
    dep_ev=[E('https://ml.cmu.edu/news/2019/machine-learning-department-welcomes-new-faculty-members', 'Yuanzhi Li Assistant Professor', 'appointment_announcement', 'MLD news, Aug. 28, 2019'),
            E('https://web.archive.org/web/20240901034728id_/https://www.ml.cmu.edu/people/core-faculty.html', 'Yuanzhi Li Assistant Professor, Machine Learn', 'dept_listing:MLD', 'last listing found')])

nochange('Alex Smola', 'Rejected 2018 and 2021 papers postdate his July 2016 move to Amazon Web Services (he gives his CMU professorship as 2013-2017).',
    departure='Moved to Amazon Web Services in July 2016; CMU professorship ended by 2017.',
    dep_ev=[E('https://ki-campus.org/node/61', 'From 2013-2017 I was professor at Carnegie Mellon University. I co-founded Marianas Labs in early 2015. In July 2016 I moved to Amazon Web Services', 'departure_announcement', 'own bio')])

nochange('Stephen Fienberg', 'Owner-named. He died on 2016-12-14; rejected 2017-2018 papers are posthumous. Listing covers 2016.',
    departure='Died 2016-12-14 in Pittsburgh (University Professor of Statistics and Social Science; at CMU since 1980).',
    dep_ev=[E('https://www.cmu.edu/dietrich/news/news-stories/2016/december/stephen-fienberg-obituary.html', 'University Professor of Statistics and Social Science at Carnegie Mellon University, died Wednesday, Dec. 14 in Pittsburgh. He was 74.', 'obituary', 'Dietrich College news, Dec. 2016'),
            E('https://www.cmu.edu/dietrich/news/news-stories/2016/december/stephen-fienberg-obituary.html', 'Statistics Department in 1980', 'faculty_start_statement')])

# ---------------------------------------------------------------- engineering
nochange('Diana Marculescu', 'Rejected 2020-2023 papers postdate her move to UT Austin (chair from 2019-12-01); the override period 2016-2019 stands.',
    departure='Left CMU ECE to chair UT Austin ECE from 2019-12-01.',
    dep_ev=[E('https://www.ece.utexas.edu/news/diana-marculescu-named-new-chair-electrical-and-computer-engineering', 'She will assume her position on Dec. 1, 2019, succeeding the department’s current chair, Ahmed Tewfik. Marculescu will join UT after serving on the faculty at Carnegie Mellon for nearly two decades.', 'departure_announcement', 'UT Austin ECE news, Aug. 26, 2019')])

nochange('Bruno Sinopoli', 'Rejected 2019-2023 papers postdate his move to Washington University in St. Louis (chair of ESE effective 2019-01-01); the override period 2016-2018 stands.',
    departure='Left CMU ECE to chair Electrical & Systems Engineering at Washington University in St. Louis, effective 2019-01-01.',
    dep_ev=[E('https://source.washu.edu/2018/09/sinopoli-named-chair-of-preston-m-green-department-of-electrical-systems-engineering/', 'effective Jan. 1. Sinopoli comes to Washington University from Carnegie Mellon University', 'departure_announcement', 'WashU Source, Sept. 2018')])

nochange('Xin Li', 'Rejected 2018 and 2020 papers postdate his 2017 move to Duke / Duke Kunshan; the override period 2016-2017 stands.',
    departure='Moved to Duke University ECE (and Duke Kunshan) in 2017; CMU listing shows him as adjunct by 2018.',
    dep_ev=[E('https://scholars.duke.edu/person/Xin.Li/academic-experience', 'Professor in the Department of Electrical and Computer Engineering · 2017 - Present', 'departure_announcement', 'Duke Scholars')])

period('Patrick Tague', '2016', None, TODAY, 'year', [
    old('Patrick Tague', 0, 'dept_listing:ECE'),
    old('Patrick Tague', 1, 'dept_listing:ECE'),
    old('Patrick Tague', 2, 'dept_listing:ECE', 'ECE now lists him as courtesy because his home moved to INI, not because he left'),
    E('https://www.cmu.edu/ini/news/2025/faculty-spotlight-patrick-tague.html', 'Tague has been with Carnegie Mellon University (CMU) for 16 years and has taught INI courses from CMU in Silicon Valley (CMU-SV) for many years. In 2020, he officially joined the INI faculty full-time.', 'faculty_start_statement', 'INI faculty spotlight, 2025'),
    E('https://www.cmu.edu/ini/about/team/tague.html', 'Patrick Tague Associate Teaching Professor, Information Networking Institute', 'faculty_profile', 'live INI profile (asof)'),
], 'Corrects the end of the override period: the 2019 end was read from ECE moving him to courtesy status, but he moved his primary appointment to the INI full-time in 2020 and is still an INI Associate Teaching Professor. Start kept at the 2016 listing (lower bound; the INI says he has been with CMU about 16 years, i.e. since about 2009, and his PhD is 2009). Covers the rejected 2020-2026 papers.',
    existing=oid('Patrick Tague'))

period('John Paul Shen', '2015-09', None, TODAY, 'month', [
    E(SCH + '2444-john-shen', 'Professor Carnegie Mellon University, Electrical and Computer Engineering, Pittsburgh, United States 1 Sep 2015 - present', 'faculty_start_statement', 'CMU Scholars academic positions (Nokia Fellow until Aug 2015)'),
    old('John Paul Shen', 0, 'dept_listing:ECE'),
    old('John Paul Shen', 1, 'dept_listing:ECE'),
], 'Corrects the start: his current ECE professorship began 2015-09-01 (after Nokia, to Aug 2015; an earlier CMU tenure 1981-2000 is not relevant). Covers the rejected 2017 papers. Ongoing (Distinguished Service Professor).',
    existing=oid('John Paul Shen'))

period('Tze Meng Low', '2017-09', None, TODAY, 'month', [
    E(SCH + '3065-tze-meng-low', 'Assistant Research Professor Carnegie Mellon University, Pittsburgh, United States 1 Sep 2017 - present', 'faculty_start_statement', 'CMU Scholars academic positions'),
    E(SCH + '3065-tze-meng-low', 'System Scientist (Special Faculty) Carnegie Mellon University, Pittsburgh, United States 1 Jan 2015 - 1 Aug 2017', 'pre_appointment_role', 'special-faculty role before the research professorship'),
    old('Tze Meng Low', 0, 'dept_listing:ECE'),
    old('Tze Meng Low', 1, 'dept_listing:ECE'),
], 'Refines the start to 2017-09-01 (Assistant Research Professor; his census role is a research professor). He was a System Scientist (special faculty) from 2015-01 to 2017-08; that non-professorial role is not counted, so the rejected 2016 papers stay outside (if the owner counts special faculty, the start would be 2015-01). Ongoing.',
    existing=oid('Tze Meng Low'))

nochange('Jeyanandh Paramesh', 'Rejected 2019-2024 papers fall after his regular CMU appointment: ECE listed him as Associate Professor on 2018-07-17, not on 2019-08-24, and as Adjunct Professor by 2019-09-19; he now holds a courtesy appointment at Oregon State. The exit date inside that window is not documented, so the override end (2018) is kept rather than extended.',
    departure='Left the regular CMU ECE faculty between 2018-07-17 and 2019-08-24 (adjunct from 2019); now courtesy appointment at Oregon State EECS.',
    dep_ev=[E('https://web.archive.org/web/20180717153248id_/https://www.ece.cmu.edu/directory/faculty.html', 'Jeyanandh Paramesh Associate Professor', 'dept_listing:ECE', 'last regular listing'),
            E('https://web.archive.org/web/20190919150329id_/https://www.ece.cmu.edu/directory/adjunct-faculty.html', 'Jeyanandh Paramesh Adjunct Professor', 'dept_listing:ECE'),
            E('https://engineering.oregonstate.edu/people/jeyanandh-paramesh', 'Jeyanandh Paramesh Title Courtesy Appointment', 'faculty_profile')])

period('Richard M. Stern', '1977', None, TODAY, 'year', [
    E('https://engineering.cmu.edu/directory/bios/stern-richard.html', 'He has been on the faculty of Carnegie Mellon University since 1977', 'faculty_start_statement', 'College of Engineering bio'),
    old('Richard M. Stern', 0, 'dept_listing:ECE'),
    old('Richard M. Stern', 1, 'dept_listing:ECE'),
], 'Corrects the start: on the CMU faculty since 1977 (ECE, with CSD/LTI appointments). Covers the rejected 2016-2017 papers. Ongoing.',
    existing=oid('Richard M. Stern'))

nochange('Bob Iannucci', 'Rejected 2023 and 2026 papers postdate his regular appointment: ECE listed him as Distinguished Service Professor through 2021 and as Courtesy Professor in 2022. Override period 2016-2021 stands.',
    departure='Regular ECE (CMU Silicon Valley) appointment ended after 2021; listed only as courtesy professor from 2022.',
    dep_ev=[E('https://web.archive.org/web/20220307194911id_/https://www.ece.cmu.edu/directory/courtesy-faculty.html', 'Bob Iannucci Courtesy Professor', 'dept_listing:ECE')])

nochange('Marija Ilić', 'Rejected 2017-2026 papers postdate her move to emerita status (ECE lists her as Professor Emeritus by Oct. 2017; she is at MIT). Override period 2016 stands.',
    departure='Professor Emerita of ECE by 2017 (emeritus years are not appointment years).',
    dep_ev=[E('https://web.archive.org/web/20171022221311id_/http://www.ece.cmu.edu:80/directory/department/faculty/index.html', 'Ilic , Marija Professor Emeritus – ECE', 'emeritus_transfer')])

period('Ding Zhao', '2018-08', None, TODAY, 'month', [
    E(SCH + '7850-ding-zhao', 'Assistant Professor Carnegie Mellon University, Pittsburgh, Pennsylvania, United States Aug 2018 - present', 'faculty_start_statement', 'CMU Scholars academic positions'),
    E(SCH + '7850-ding-zhao', 'Research Scientist University of Michigan–Ann Arbor, Ann Arbor, Michigan, United States May 2017 - Aug 2018', 'pre_appointment_role'),
    old('Ding Zhao', 0, 'dept_listing:MechE'),
    old('Ding Zhao', 1, 'dept_listing:MechE'),
], 'Corrects the start to Aug 2018 (MechE assistant professor; Michigan research scientist until Aug 2018), so 2018 papers from Aug on resolve; earlier 2018 papers are pre-appointment. Ongoing.',
    existing=oid('Ding Zhao'))

nochange('Steven H. Collins', 'Rejected 2018-2021 papers postdate his 2017 move to Stanford. Override period 2016-2017 stands.',
    departure='Left CMU (MechE/RI) for Stanford Mechanical Engineering in 2017.',
    dep_ev=[E('https://neuroscience.stanford.edu/people/steven-hartley-collins', 'He was a professor of Mechanical Engineering and Robotics at Carnegie Mellon University for seven years. In 2017, he joined the faculty of Mechanical Engineering at Stanford University.', 'departure_announcement', 'Stanford profile')])

nochange('Metin Sitti', 'Rejected 2019-2022 papers postdate his regular CMU appointment: MechE lists him only as "Special Faculty" by April 2019 (he directed the MPI for Intelligent Systems from 2014). Override period 2016-2018 stands.',
    departure='Regular CMU professorship ended by 2019 (MechE "Special Faculty" from 2019); Director at MPI-IS Stuttgart from 2014.',
    dep_ev=[E('https://web.archive.org/web/20190413031434id_/http://www.meche.engineering.cmu.edu:80/directory/index.html', 'Metin Sitti Special Faculty', 'dept_listing:MechE')])

nochange('Hae Young Noh', 'Rejected 2020-2023 papers postdate her move to Stanford (CMU bio: Adjunct Professor at CMU, Associate Professor at Stanford). Override period 2016-2019 stands.',
    departure='Moved to Stanford CEE (Associate Professor) after 2019; CMU role now adjunct.',
    dep_ev=[E('https://engineering.cmu.edu/directory/bios/noh-hae-young.html', 'Adjunct Professor, Civil and Environmental Engineering, Carnegie Mellon University Associate Professor, Civil and Environmental Engineering, Stanford', 'departure_announcement', 'CMU Engineering bio')])

nochange('Nikolaos V. Sahinidis', 'Rejected 2021-2025 papers postdate his 2020 move to Georgia Tech (ChemE lists him as adjunct by 2023). Override period 2016-2020 stands.',
    departure='Moved to Georgia Tech (Gary C. Butler Family Chair, ISyE/ChBE) in 2020; CMU role adjunct.',
    dep_ev=[E('https://www.isye.gatech.edu/users/nikolaos-sahinidis', 'Nick Sahinidis is the Gary C. Butler Family Chair Professor in the H. Milton Stewart School of Industrial and Systems Engineering', 'departure_announcement', 'Georgia Tech ISyE profile'),
            E('https://web.archive.org/web/20230408072929id_/https://www.cheme.engineering.cmu.edu/directory/index.html', 'Nikolaos Sahinidis Adjunct Faculty', 'dept_listing:ChemE')])

nochange('Zachary W. Ulissi', 'Rejected 2024-2025 papers postdate his regular appointment: he joined Meta FAIR in 2023 (on leave from CMU that year) and is an adjunct professor from 2024. Override period 2017-2023 stands (2023 was a leave year at Meta; see report).',
    departure='Joined Meta FAIR in 2023 while on leave from CMU; adjunct professor of chemical engineering from 2024.',
    dep_ev=[E('https://bidmap.berkeley.edu/seminars/may-8-2025-zachary-w-ulissi', 'Prior to 2023, he was an assistant and then associate professor at CMU, and in 2023, he was on leave from his position. He joined CMU in 2017', 'departure_announcement', 'Berkeley seminar bio, May 2025'),
            E('https://bidmap.berkeley.edu/seminars/may-8-2025-zachary-w-ulissi', 'In 2024, Ulissi serves as an adjunct professor of chemical engineering at Carnegie Mellon University (CMU).', 'departure_announcement')])

nochange('B. Erik Ydstie', 'Rejected 2021-2025 papers postdate his move to emeritus (ChemE lists him as Emeritus Professor in April 2021). Override period 2016-2020 stands.',
    departure='Emeritus Professor of Chemical Engineering by April 2021.',
    dep_ev=[E('https://web.archive.org/web/20210404132135id_/https://www.cheme.engineering.cmu.edu/directory/index.html', 'B. Erik Ydstie Emeritus Professor', 'emeritus_transfer')])

# ---------------------------------------------------------------- Tepper / Heinz
period('Alan Scheller-Wolf', '1996', None, TODAY, 'year', [
    E('https://www.cmu.edu/piper/news/archives/2017/august/august-10/personal-mention.html', 'Scheller-Wolf, a member of the Tepper School since 1996', 'faculty_start_statement', 'The Piper, Aug. 2017'),
    old('Alan Scheller-Wolf', 0, 'dated_profile:Tepper'),
    old('Alan Scheller-Wolf', 1, 'dept_listing:Tepper'),
], 'Corrects the start: Tepper faculty since 1996. Covers the rejected 2016-2018 papers. Ongoing (Richard M. Cyert Professor).',
    existing=oid('Alan Scheller-Wolf'))

period('Gérard Cornuéjols', '2002', '2022', None, 'year', [
    E('https://en.wikipedia.org/wiki/G%C3%A9rard_Cornu%C3%A9jols', 'In 2002, he received the title of University Professor at Carnegie Mellon University.', 'faculty_start_lower_bound', 'Wikipedia'),
    E('https://www.cmu.edu/homepage/computing/2009/fall/awarded-dantzig-prize.shtml', 'Gérard Cornuéjols — IBM University Professor of Operations Research at Carnegie Mellon University', 'faculty_profile', 'CMU homepage story, fall 2009'),
    old('Gérard Cornuéjols', 0, 'dept_listing:Mathematical Sciences'),
    old('Gérard Cornuéjols', 1, 'dept_listing:Mathematical Sciences'),
    E('https://web.archive.org/web/20221226002605id_/https://www.cmu.edu/math/people/faculty/index.html', 'Gérard P. Cornuéjols IBM University Professor of Operations Research, Emeritus', 'emeritus_transfer', 'emeritus by Dec. 2022'),
], 'Owner-named. Start is a lower bound: University Professor at CMU from 2002 (on the Tepper faculty since about 1978, PhD Cornell 1978, but no dated start statement captured). End: last active listing 2022-03-07, Emeritus by 2022-12-26, so the appointment ended in 2022 (year precision; the exact emeritus date was not found). Covers the rejected 2016-2018 papers; 2023-2026 papers are emeritus years and stay outside.',
    existing=oid('Gérard Cornuéjols'), departure='Became IBM University Professor of Operations Research, Emeritus in 2022 (active in March 2022, emeritus by Dec. 2022).')

period('Willem-Jan van Hoeve', '2007', None, TODAY, 'year', [
    E(SCH + '5011-willemjan-van-hoeve', 'Assistant Professor of Operations Research Carnegie Mellon University, Tepper School of Business, Pittsburgh, United States 1 Jan 2007 - 1 Jan 2013', 'faculty_start_statement', 'CMU Scholars academic positions (dates given as 1 Jan, i.e. year only)'),
    E(SCH + '5011-willemjan-van-hoeve', 'Carnegie Bosch Professor of Operations Research Carnegie Mellon University, Tepper School of Business, Pittsburgh, United States 1 Jan 2019 - present', 'faculty_profile', 'current (asof)'),
    old('Willem-Jan van Hoeve', 0, 'faculty_profile'),
    old('Willem-Jan van Hoeve', 1, 'dept_listing:Tepper'),
], 'Corrects the start: the override start 2016-01 was the start of his Carnegie Bosch chair; he has been a Tepper faculty member since 2007 (assistant professor 2007-2013, after a Cornell postdoc 2005-2007). Covers the rejected 2016 papers. Ongoing.',
    existing=oid('Willem-Jan van Hoeve'))

period('John Hooker', '1984', '2022-04', None, 'month', [
    E('https://web.archive.org/web/20160616220521id_/http://web.tepper.cmu.edu:80/jnh/contact.htm', 'He joined the Tepper School of Business at CMU in 1984', 'faculty_start_statement', 'own biography, May 2016'),
    E('https://www.cmu.edu/news/stories/archives/2022/april/hebert-hooker-and-kraut-named-university-professors', 'is a professor of operations research and the T. Jerome Holleran Professor of Business Ethics and Social Responsibility at Carnegie Mellon', 'faculty_profile', 'CMU News, Apr. 11, 2022 (named University Professor)'),
    E('https://web.archive.org/web/20220408024837id_/https://www.cmu.edu/tepper/faculty-and-research/faculty-by-area/profiles/hooker-john.html', 'John Hooker T. Jerome Holleran Professor of Business Ethics and Social Responsibility; Professor of Operations Research', 'faculty_profile', 'Tepper profile, Apr. 2022'),
    E('https://web.archive.org/web/20230531190523id_/https://johnhooker.tepper.cmu.edu/', 'University Professor of Operations Research and T. Jerome Holleran Professor of Business Ethics and Social Responsibility, Emeritus', 'emeritus_transfer', 'own homepage, May 2023'),
    old('John Hooker', 0, 'dated_profile:Tepper'),
    old('John Hooker', 1, 'faculty_profile', 'live Tepper page: Emeritus'),
], 'Owner-named. Start: joined Tepper in 1984. End: last evidence of active status is April 2022 (named University Professor, CMU News 2022-04-11); he is Emeritus by 2023-05-31. The end is set at the last affirmative evidence (2022-04) and is a lower bound on the true retirement date, which lies between 2022-04-11 and 2023-05-31; papers in that window stay outside. Covers the rejected 2016-2018 and 2020-2021 papers; 2023-2026 are emeritus years.',
    existing=oid('John Hooker'), departure='Emeritus (University Professor of Operations Research and Holleran Professor, Emeritus) by 2023-05-31; active as of 2022-04-11.')

nochange('Ali Shourideh', 'Override start 2016-07 is confirmed (assistant professor at Tepper from 1 Jul 2016; Wharton until 30 Jun 2016). The rejected 2016 papers predate it.',
    dep_ev=[E(SCH + '5383-ali-shourideh', 'Assistant Professor of Economics Carnegie Mellon University, Tepper School of Business, Pittsburgh, United States 1 Jul 2016 - Jul 2020', 'faculty_start_statement'),
            E(SCH + '5383-ali-shourideh', 'Assistant Professor of Finance University of Pennsylvania, Wharton School of Business, Philadelphia, United States 1 Jul 2011 - 30 Jun 2016', 'pre_appointment_role')])

period('Rema Padman', '1995', None, TODAY, 'year', [
    E('https://www.andrew.cmu.edu/user/rk2x/home/rema.html', 'I am Associate Professor of Operations and InformationManagement at the Heinz School of Public Policy and Management at Carnegie Mellon University', 'faculty_start_lower_bound', 'personal page stamped "last updated 8/2/95"'),
    E('https://www.andrew.cmu.edu/user/rk2x/home/rema.html', 'last updated 8/2/95', 'faculty_start_lower_bound', 'date stamp of the page above'),
    old('Rema Padman', 0, 'dated_profile:Heinz'),
    old('Rema Padman', 1, 'dept_listing:Heinz'),
], 'Owner-named. Start is a lower bound: an Associate Professor at the Heinz School on a page last updated 1995-08-02 (she came to Pittsburgh in 1989; no dated hire statement captured). Covers the rejected 2016-2018 papers. Ongoing (Trustees Professor).',
    existing=oid('Rema Padman'))

period('Jeremy C. Weiss', '2016', '2022-07', None, 'month', [
    old('Jeremy C. Weiss', 0, 'dept_listing:MLD'),
    old('Jeremy C. Weiss', 1, 'dept_listing:MLD'),
    E('https://web.archive.org/web/20220707051717id_/https://www.heinz.cmu.edu/faculty-research/profiles/weiss-jeremy/', 'Jeremy Weiss Assistant Professor of Health Informatics', 'dated_profile:Heinz', 'last capture of his Heinz profile; removed by 2023-01-30'),
    E('https://mainweb.awsprod.nlm.nih.gov/research/researchstaff/WeissJeremy.html', 'Tenure Track Investigator, Computational Health Research Branch', 'departure_announcement', 'now at NIH/NLM'),
], 'Refines the end from year 2022 to the last affirmative evidence (Heinz profile 2022-07-07; profile gone by 2023-01-30; he is now an NLM tenure-track investigator), so 2022 papers through July resolve. The end is a lower bound on the true departure date. Start kept at the 2016 MLD listing.',
    existing=oid('Jeremy C. Weiss'), departure='Left Heinz College between 2022-07-07 and 2023-01-30; now Tenure Track Investigator at the National Library of Medicine.')

period('Pedro Ferreira', '2011', None, TODAY, 'year', [
    E(SCH + '3852-pedro-ferreira', 'Assistant Research Professor Carnegie Mellon University, Heinz College & Engineering and Public Policy, Pittsburgh, United States 2011 - 2013', 'faculty_start_statement', 'CMU Scholars academic positions'),
    E(SCH + '3852-pedro-ferreira', 'Visiting Assistant Professor Carnegie Mellon University, Engineering and Public Policy and Heinz College, Pittsburgh, United States 2010 - 2011', 'pre_appointment_role', 'visiting year not counted'),
    E(SCH + '3852-pedro-ferreira', 'Full Professor Carnegie Mellon University, Heinz College & Engineering and Public Policy, Pittsburgh, United States 2023 - present', 'faculty_profile', 'current (asof)'),
    old('Pedro Ferreira', 0, 'dated_profile:Heinz'),
    old('Pedro Ferreira', 1, 'dept_listing:Heinz'),
], 'Owner-named. Corrects the start: Assistant Research Professor at Heinz/EPP from 2011 (visiting 2010-2011 not counted), assistant professor 2013. Covers the rejected 2016-2018 papers. Ongoing.',
    existing=oid('Pedro Ferreira'))

period('Michael D. Smith', '2000', None, TODAY, 'year', [
    E('https://ece.umd.edu/news/story/alumnus-michael-d-smith-promoted-to-full-professor-at-carnegie-mellon', 'Prof. Smith has served as a faculty member at Carnegie Mellon University since 2000.', 'faculty_start_statement', 'UMD ECE alumni news'),
    E(SCH + '3296-michael-smith', 'Michael Smith Professor of Information Technology and Public Policy Heinz College of Information Systems and Public Policy', 'faculty_profile', 'live CMU Scholars profile (asof)'),
    old('Michael D. Smith', 0, 'dated_profile:Heinz'),
    old('Michael D. Smith', 1, 'dept_listing:Heinz'),
], 'Owner-named. Corrects the start: CMU faculty member since 2000 (assistant professor, promoted 2006). Covers the rejected 2016-2019 papers. Ongoing.',
    existing=oid('Michael D. Smith'))

# ---------------------------------------------------------------- Dietrich / MCS / CFA / EPP
period('Simon DeDeo', '2017-01', None, TODAY, 'month', [
    E('https://www.cmu.edu/dietrich/news/news-stories/2017/january/simon-dedeo.html', 'an expert in social complexity and a mathematician, has joined Carnegie Mellon University', 'appointment_announcement', 'Dietrich College news, Jan. 18, 2017'),
    E(SCH + '7415-simon-dedeo', 'Simon DeDeo Professor Social and Decision Sciences', 'faculty_profile', 'live CMU Scholars profile (asof)'),
    old('Simon DeDeo', 0, 'dept_listing:Social & Decision Sciences'),
], 'Owner-named. Corrects the start from 2026 to January 2017: the Dietrich College announcement of 2017-01-18 says he has joined SDS (assistant professor, from Indiana University/SFI). Covers the rejected 2017-2025 papers; 2016 papers predate the appointment. Ongoing.',
    existing=oid('Simon DeDeo'))

nochange('David Danks', 'Rejected 2022 papers postdate his move to UC San Diego (accepted Jan. 2021, starting 2021); override period 2016-2021 stands.',
    departure='Left CMU (Philosophy head) for UC San Diego (Philosophy and Halıcıoğlu Data Science Institute) in 2021.',
    dep_ev=[E('https://leiterreports.com/2021/01/29/danks-harrell-from-carnegie-mellon-to-uc-san-diego/', 'Danks will be half in Philosophy and half in the Halıcıoğlu Data Science Institute', 'departure_announcement', 'Leiter Reports, Jan. 29, 2021: accepted a tenured offer from UC San Diego')])

period('Marsha Lovett', '2012', None, TODAY, 'year', [
    E('https://www.cmu.edu/leadership/the-provost/campus-comms/2022/2022-07-01.html', 'Since 2012, she has served as the director of the Eberly Center for Teaching Excellence and Educational Innovation and a teaching professor in the Department of Psychology.', 'faculty_start_statement', 'Provost announcement, July 1, 2022'),
    old('Marsha Lovett', 0, 'dept_listing:Psychology'),
    old('Marsha Lovett', 1, 'dept_listing:Psychology'),
], 'Owner-named. Corrects the start: teaching professor in Psychology since 2012 (lower bound for the teaching-track appointment, which is her census role; she was at CMU earlier). Covers the rejected 2016-2021 papers. Ongoing (Vice Provost, Professor of Psychology (Teaching)).',
    existing=oid('Marsha Lovett'))

nochange('Daniel Yurovsky', 'Rejected 2023-2026 papers postdate his departure: Psychology listed him on 2022-05-16 but not on 2022-09-01; he now leads the Communication and Learning Lab at the University of Chicago. Override period 2020-2022 stands (he joined in Aug 2019).',
    departure='Left CMU Psychology between 2022-05-16 and 2022-09-01 (dropped from the core faculty listing); now PI of the UChicago Communication and Learning Lab.',
    dep_ev=[E('https://web.archive.org/web/20220516212830id_/https://www.cmu.edu/dietrich/psychology/directory/core-training-faculty/index.html', 'Daniel Yurovsky Assistant Professor of Psychology', 'dept_listing:Psychology', 'last listing'),
            E('https://callab.uchicago.edu/members.html', 'Dan Yurovsky Principal Investigator', 'faculty_profile', 'University of Chicago lab page')])

period('Wesley Pegden', '2013', None, TODAY, 'year', [
    E(SCH + '3853-wesley-pegden', 'Assistant Professor Carnegie Mellon University, Department of Mathematical Sciences, Pittsburgh, United States 2013 - 2017', 'faculty_start_statement', 'CMU Scholars academic positions'),
    old('Wesley Pegden', 0, 'dept_listing:Mathematical Sciences'),
    old('Wesley Pegden', 1, 'dept_listing:Mathematical Sciences'),
], 'Owner-named. Corrects the start: assistant professor in Mathematical Sciences from 2013 (after a Courant postdoc 2010-2013). Covers the rejected 2016-2018 papers. Ongoing.',
    existing=oid('Wesley Pegden'))

period('Dejan Slepčev', '2006', None, TODAY, 'year', [
    E(SCH + '4587-dejan-slepčev', 'Assistant Professor Carnegie Mellon University, Department of Mathematical Sciences, Pittsburgh, United States 2006 - 2011', 'faculty_start_statement', 'CMU Scholars academic positions'),
    old('Dejan Slepčev', 0, 'dept_listing:Mathematical Sciences'),
    old('Dejan Slepčev', 1, 'dept_listing:Mathematical Sciences'),
], 'Owner-named. Corrects the start: assistant professor in Mathematical Sciences from 2006 (UCLA 2004-2006). Covers the rejected 2016-2018 papers. Ongoing.',
    existing=oid('Dejan Slepčev'))

period('Robert L. Pego', '2010', '2022', None, 'year', [
    E('https://web.archive.org/web/20100309095452id_/http://www.math.cmu.edu:80/~bobpego/', 'Robert Pego Professor Department of Mathematical Sciences Carnegie Mellon University', 'faculty_start_lower_bound', 'own homepage, Wayback 2010-03-09'),
    old('Robert L. Pego', 0, 'dept_listing:Mathematical Sciences'),
    old('Robert L. Pego', 1, 'dept_listing:Mathematical Sciences'),
    E('https://web.archive.org/web/20221226002605id_/https://www.cmu.edu/math/people/faculty/index.html', 'Robert Pego Professor Emeritus', 'emeritus_transfer', 'emeritus by Dec. 2022'),
], 'Owner-named. Start is a lower bound (Professor of Mathematical Sciences on his homepage captured 2010-03-09; no dated hire statement captured). End: Professor on the 2022-03-07 listing, Professor Emeritus by 2022-12-26, so the appointment ended in 2022 (year precision). Covers the rejected 2016-2018 papers; 2023-2025 are emeritus years.',
    existing=oid('Robert L. Pego'), departure='Became Professor Emeritus of Mathematical Sciences in 2022 (active March 2022, emeritus by Dec. 2022).')

period('Hayden Schaeffer', '2015', '2023', None, 'year', [
    E('https://sites.google.com/view/haydenschaeffer/cv', 'Assistant Professor , Mathematical Sciences, Carnegie Mellon University, 2015-2019', 'faculty_start_statement', 'own CV page'),
    E('https://sites.google.com/view/haydenschaeffer/cv', 'Associate Professor with Tenure , Mathematical Sciences, Carnegie Mellon University, 2022-2023', 'faculty_profile'),
    E('https://sites.google.com/view/haydenschaeffer/cv', 'Professor , Department of Mathematics, UCLA, since 2023', 'departure_announcement'),
    old('Hayden Schaeffer', 0, 'dept_listing:Mathematical Sciences'),
    old('Hayden Schaeffer', 1, 'dept_listing:Mathematical Sciences'),
], 'Owner-named. Corrects the start: CMU assistant professor from 2015 (Caltech von Karman instructor 2014-2015). End 2023 as before (moved to UCLA in 2023; year only). Covers the rejected 2016-2018 papers.',
    existing=oid('Hayden Schaeffer'), departure='Moved to UCLA (Professor of Mathematics) in 2023.')

period('Douglas Sicker', '2016', '2020-07', None, 'month', [
    old('Douglas Sicker', 0, 'dept_listing:S3D'),
    old('Douglas Sicker', 1, 'dept_listing:S3D'),
    E('https://ucdengineeringnews.com/2020/07/22/sicker/', 'He comes to CU Denver from Carnegie Mellon University (CMU) where he was the Thomas Lord Endowed Chair Professor in Computer Science and Engineering.', 'departure_announcement', 'CU Denver CEDC news, July 22, 2020'),
], 'Corrects the end: the override ended at the 2019 listing, but he held his CMU chair professorship until he moved to CU Denver, announced as having joined on 2020-07-22; the end is set to 2020-07 (month of the move; no CMU listing between Dec. 2019 and the move was captured). Covers the rejected 2020 papers through July; 2021 papers stay outside. Start kept at the 2016 listing (lower bound; head of EPP before).',
    existing=oid('Douglas Sicker'), departure='Left CMU for CU Denver (Senior Associate Dean for Computing) in July 2020.')

period('Daniel Cardoso Llach', '2016-03-24', None, TODAY, 'day', [
    E('https://web.archive.org/web/20160324214919id_/http://soa.cmu.edu/daniel-cardoso-llach', 'Daniel Cardoso Llach Assistant Professor', 'faculty_start_lower_bound', 'School of Architecture profile, Wayback 2016-03-24'),
    old('Daniel Cardoso Llach', 0, 'dept_listing:Architecture'),
    old('Daniel Cardoso Llach', 1, 'dept_listing:Architecture'),
], 'Owner-named. Start is a lower bound: assistant professor in the School of Architecture on the earliest captured profile (2016-03-24; he joined after his 2012 MIT PhD, exact year not found). Covers the rejected 2017-2023 papers; 2016 papers before March 24 stay unresolved. Ongoing.',
    existing=oid('Daniel Cardoso Llach'))

period('Peter Scupelli', '2013-09-19', None, TODAY, 'day', [
    E('https://web.archive.org/web/20130919092106id_/http://design.cmu.edu:80/people/faculty/peter-scupelli', 'Peter Scupelli is an Assistant Professor in the School of Design.', 'faculty_start_lower_bound', 'School of Design profile, Wayback 2013-09-19 (earliest capture)'),
    E(SCH + '3878-peter-scupelli', 'Associate Professor Carnegie Mellon University, School of Design, Pittsburgh, United States 1 Jul 2020 - present', 'faculty_profile', 'current (asof)'),
    old('Peter Scupelli', 0, 'dept_listing:Design'),
    old('Peter Scupelli', 1, 'dept_listing:Design'),
], 'Owner-named. Start is a lower bound: assistant professor in the School of Design on the earliest captured profile (2013-09-19). Covers the rejected 2016-2023 papers. Ongoing.',
    existing=oid('Peter Scupelli'))

period('Molly Wright Steenson', '2015', '2023-06', None, 'month', [
    E('https://www.girlwonder.com/bio-and-cv', 'At Carnegie Mellon University, where she was on faculty from 2015–2025', 'faculty_start_statement', 'own bio'),
    E('https://asimn.org/press-release/american-swedish-institute-announces-new-president-and-ceo/', 'Dr. Steenson will join ASI in July 2023', 'departure_announcement', 'American Swedish Institute press release, Mar. 21, 2023'),
    old('Molly Wright Steenson', 0, 'dept_listing:Design', 'on leave while ASI president'),
    old('Molly Wright Steenson', 1, 'dept_listing:Design', 'on leave while ASI president'),
], 'Owner-named. Start: on the CMU faculty from 2015 (her bio). End: she became President and CEO of the American Swedish Institute in July 2023; the Design listings of 2024-2025 show her only "(On Leave)" and her bio gives her CMU faculty years as 2015-2025. Leave years while employed full-time elsewhere are treated like adjunct roles after moving and are not counted, so the period ends 2023-06 (this shortens the override, which ran 2024-open). Covers the rejected 2016-2022 papers.',
    existing=oid('Molly Wright Steenson'), departure='Left active CMU service in July 2023 to lead the American Swedish Institute (on leave 2023-2025; CMU faculty status ended 2025 per her bio).')

nochange('Koushil Sreenath', 'Rejected 2020 and 2026 papers postdate his move to UC Berkeley (CMU assistant professor 2013-2017). Override period 2016-2018 stands (its 2018 end rests on an April 2018 ECE courtesy/RI listing).',
    departure='Left CMU for UC Berkeley Mechanical Engineering after 2017.',
    dep_ev=[E('https://hybrid-robotics.berkeley.edu/koushil', 'an Assistant Professor at Carnegie Mellon University from 2013 to 2017', 'departure_announcement', 'Berkeley lab page')])

nochange('Yong-Lae Park', 'Rejected 2018-2026 papers postdate his 2016 move to Seoul National University. Override period 2016-2017 stands (its 2017 year rests on a MechE courtesy listing).',
    departure='Moved to Seoul National University (Mechanical Engineering) in 2016.',
    dep_ev=[E('https://www.ieee-ras.org/ras_member/yonglae-park/', 'Prof. Park is an Associate Professor in the Department of Mechanical Engineering at Seoul National University (2016~present).', 'departure_announcement', 'IEEE RAS member bio')])
