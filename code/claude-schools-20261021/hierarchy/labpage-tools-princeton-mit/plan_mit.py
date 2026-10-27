"""Reviewed lab-page plan for MIT (see lpauto.py for the keys). Pages were chosen by reading the discovery
dossier (dossier_mit.json), autom/peek listings and the pages themselves; notes say what was used and why."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lpev import M, MS, P as Pub, Pubs  # noqa: E402,F401

SCH = "mit"
P = {}
from lpauto import R, RS, js_members, sqs_members  # noqa: E402,F401


def lab(site, people=(), wb=None, pubs=(), notes="", **kw):
    d = dict(site=site, people=list(people), wb=list(people) if wb is None else list(wb),
             pubs=[Pubs(p) if isinstance(p, str) else p for p in pubs], notes=notes)
    d.update(kw)
    return d


NOPAGE = "No lab members page found on the PI's site(s) (EECS/CSAIL profile and personal pages checked)."
FIRST = "First faculty appointment (at MIT since {}), so undated alumni are MIT members."

P["Hal Abelson"] = lab("http://groups.csail.mit.edu/mac/users/hal/hal.html", [], pubs=["https://groups.csail.mit.edu/mac/users/hal/pubs.html"], notes=NOPAGE)
P["Fadel Adib"] = lab("https://www.mit.edu/~fadel/", ["https://www.mit.edu/~fadel/"], alumni_ok=True,
                      pubs=["https://www.mit.edu/~fadel/publications.html"], notes="Homepage group section (Signal Kinetics). " + FIRST.format(2016))
P["Pulkit Agrawal"] = lab("https://improbableai.com/", ["https://improbableai.com/members.html"], alumni_ok=True,
                          pubs=["https://improbableai.com/papers.html"], notes="Improbable AI Lab members page. " + FIRST.format(2019))
P["Mohammad Alizadeh"] = lab("https://people.csail.mit.edu/alizadeh/", ["https://people.csail.mit.edu/alizadeh/students.html"], alumni_ok=True,
                             pubs=["https://people.csail.mit.edu/alizadeh/papers.html"], notes="Students page. " + FIRST.format(2015))
P["Saman Amarasinghe"] = lab("https://mit-commit.github.io/commit-website/", ["https://mit-commit.github.io/commit-website/people.html"],
                             pubs=["https://mit-commit.github.io/commit-website/publications.html"], notes="COMMIT group site (people page, JS-rendered).")
P["Jacob Andreas"] = lab("https://lingo.csail.mit.edu/", ["https://lingo.csail.mit.edu/people.html"], alumni_ok=True,
                         notes="LINGO lab people page. " + FIRST.format(2019))
P["Hari Balakrishnan"] = lab("https://nms.csail.mit.edu/", ["https://nms.csail.mit.edu/people.html"], notes="Networks & Mobile Systems group people page.")
P["Regina Barzilay"] = lab("https://www.rbg.mit.edu/", ["https://www.rbg.mit.edu/people"], pubs=["https://www.rbg.mit.edu/publications"],
                           notes="Regina Barzilay Group people page.")
P["Sara Beery"] = lab("https://beerys.github.io/", ["https://beerys.github.io/"], alumni_ok=True, notes="Homepage group section. " + FIRST.format(2023))
P["Adam Belay"] = lab("https://people.csail.mit.edu/abelay/", [], notes=NOPAGE)
P["Robert Berwick"] = lab("https://berwick.mit.edu/", [], notes="berwick.mit.edu timed out; " + NOPAGE)
P["Guy Bresler"] = lab("https://www.mit.edu/~gbresler/", ["https://www.mit.edu/~gbresler/"], alumni_ok=True,
                       pubs=["https://www.mit.edu/~gbresler/publication/"], notes="Homepage students section. " + FIRST.format(2015))
P["Tamara Broderick"] = lab("https://tamarabroderick.com/", ["https://www.tamarabroderick.com/"], alumni_ok=True,
                            pubs=["https://tamarabroderick.com/papers.html"], notes="Homepage group section. " + FIRST.format(2015))
P["Michael Carbin"] = lab("https://people.csail.mit.edu/mcarbin/", [], notes=NOPAGE)
P["Anantha Chandrakasan"] = lab("https://chandrakasan.mit.edu/", ["https://chandrakasan.mit.edu/team/"],
                                pubs=["https://chandrakasan.mit.edu/publications/"], notes="Energy-Efficient Circuits and Systems group team page.")
P["Adam Chlipala"] = lab("https://adam.chlipala.net/", ["https://adam.chlipala.net/", "https://adam.chlipala.net/past.html"], alumni_ok=True,
                         pubs=["https://adam.chlipala.net/papers/"], notes="Homepage (current students) and past.html (former students). " + FIRST.format(2011))
P["Isaac Chuang"] = lab("https://feynman.mit.edu/ike/homepage/", [], notes=NOPAGE)
P["Henry Corrigan-Gibbs"] = lab("https://people.csail.mit.edu/henrycg/", ["https://people.csail.mit.edu/henrycg/"], alumni_ok=True,
                                notes="Homepage students section. " + FIRST.format(2020))
P["Constantinos Daskalakis"] = lab("http://people.csail.mit.edu/costis", ["https://people.csail.mit.edu/costis"],
                                   pubs=["http://people.csail.mit.edu/costis/academic.html"], notes="Homepage group section.")
P["Randall Davis"] = lab("http://people.csail.mit.edu/people/davis/", [], notes=NOPAGE)
P["Christina Delimitrou"] = lab("https://people.csail.mit.edu/delimitrou/", ["https://people.csail.mit.edu/delimitrou/Students.html"],
                                wb_from=2022, pubs=["https://people.csail.mit.edu/delimitrou/Publications.html"],
                                notes="Students page. She moved from Cornell in 2022 (SAIL group at Cornell): students placed at Cornell are left out.")
P["Erik Demaine"] = lab("https://erikdemaine.org/", ["https://erikdemaine.org/students/"], notes="Students page.")
P["Srini Devadas"] = lab("https://people.csail.mit.edu/devadas/", ["https://csg.csail.mit.edu/pubs/people.html"], notes="CSG group people page.")
P["Frederic Durand"] = lab("https://people.csail.mit.edu/fredo/", ["https://people.csail.mit.edu/fredo/student.html"], notes="Students page.")
P["William Freeman"] = lab("https://billf.mit.edu/", [], pubs=["https://billf.mit.edu/publications/all/"], notes=NOPAGE)
P["Marzyeh Ghassemi"] = lab("https://healthyml.org/", ["https://healthyml.org/people/"], wb_from=2021,
                            pubs=["https://healthyml.org/publication"], notes="Healthy ML people page. She moved from Toronto in 2021.")
P["Manya Ghobadi"] = lab("https://people.csail.mit.edu/ghobadi/", ["https://people.csail.mit.edu/ghobadi/"], alumni_ok=True,
                         notes="Homepage group section. " + FIRST.format(2018))
P["David Gifford"] = lab("https://gifford-lab.github.io/", ["https://gifford-lab.github.io/team/"], notes="Gifford Lab team page.")
P["Shafrira Goldwasser"] = lab(None, [], notes="No MIT profile or lab page found (EECS/CSAIL profile URLs 404).")
P["Polina Golland"] = lab("https://people.csail.mit.edu/polina/", ["https://people.csail.mit.edu/polina/people.html"], notes="Group people page.")
P["John Guttag"] = lab("http://nms.csail.mit.edu/~guttag/", [], notes="nms.csail.mit.edu/~guttag timed out; " + NOPAGE)
P["Dylan Hadfield-Menell"] = lab("https://algorithmicalignment.csail.mit.edu/", ["https://algorithmicalignment.csail.mit.edu/team/"], alumni_ok=True,
                                 notes="Algorithmic Alignment Group team page. " + FIRST.format(2021))
P["Song Han"] = lab("https://hanlab.mit.edu/", ["https://hanlab.mit.edu/team"], alumni_ok=True,
                    pubs=["https://hanlab.mit.edu/publications"], notes="HAN Lab team page. " + FIRST.format(2018))
P["Kaiming He"] = lab("https://people.csail.mit.edu/kaiming/", ["https://people.csail.mit.edu/kaiming/"], alumni_ok=True,
                      pubs=["https://people.csail.mit.edu/kaiming/publications.html"], notes="Homepage group section. " + FIRST.format(2024))
P["Sam Hopkins"] = lab("https://www.samuelbhopkins.com/", ["https://www.samuelbhopkins.com/"], alumni_ok=True,
                       pubs=["http://www.samuelbhopkins.com/pubs.html"], notes="Homepage group section. " + FIRST.format(2021))
P["Cheng Zhi (Anna) Huang"] = lab("https://czhuang.github.io/", [], notes=NOPAGE)
P["Daniel Huttenlocher"] = lab(None, [], notes="Dean of the Schwarzman College of Computing; no lab page found.")
P["Piotr Indyk"] = lab("https://people.csail.mit.edu/indyk/", ["https://people.csail.mit.edu/indyk/"], notes="Homepage students section.")
P["Phillip Isola"] = lab("https://web.mit.edu/phillipi/", ["https://web.mit.edu/phillipi/", "https://web.mit.edu/phillipi/www/alumni.html"],
                         alumni_ok=True, pubs=["http://web.mit.edu/phillipi/www/all_papers.html"], notes="Homepage group section and alumni page. " + FIRST.format(2018))
P["Tommi Jaakkola"] = lab("https://people.csail.mit.edu/tommi/", ["https://people.csail.mit.edu/tommi/people.html"],
                          pubs=["https://people.csail.mit.edu/tommi/papers.html"], notes="Group people page.")
P["Daniel Jackson"] = lab("https://sdg.csail.mit.edu/", ["https://sdg.csail.mit.edu/people", "https://sdg.csail.mit.edu/alumni/"],
                          pubs=["https://sdg.csail.mit.edu/publications/"], notes="Software Design Group people and alumni pages.")
P["Patrick Jaillet"] = lab("https://www.mit.edu/~jaillet/", [], pubs=["https://www.mit.edu/~jaillet/general/publications.html"], notes=NOPAGE)
P["Stefanie Jegelka"] = lab("https://people.csail.mit.edu/stefje/", ["https://people.csail.mit.edu/stefje/students.html"],
                            pubs=["https://people.csail.mit.edu/stefje/publications_year.html"], notes="Students page (she also holds a TUM chair since 2023).")
P["M. Frans Kaashoek"] = lab("https://pdos.csail.mit.edu/", ["https://pdos.csail.mit.edu/people/"], pubs=["https://pdos.csail.mit.edu/publications/"],
                             notes="PDOS group people page (shared with Robert Morris and Nickolai Zeldovich).")
P["Leslie Kaelbling"] = lab("https://lis.csail.mit.edu/", ["https://lis.csail.mit.edu/people/"], pubs=["https://lis.csail.mit.edu/publications/"],
                            notes="Learning and Intelligent Systems group people page (shared with Tomás Lozano-Pérez).")
P["David Karger"] = lab("https://people.csail.mit.edu/karger/", ["https://people.csail.mit.edu/karger/", "https://people.csail.mit.edu/karger/alumni.html"],
                        pubs=["https://people.csail.mit.edu/karger/papers.html"], notes="Homepage (current students) and alumni page.")
P["Dina Katabi"] = lab("https://people.csail.mit.edu/dina/", ["https://people.csail.mit.edu/dina/students.html"],
                       pubs=["https://people.csail.mit.edu/dina/publications.html"], notes="Students page (JS-rendered).")
P["Manolis Kellis"] = lab("https://compbio.mit.edu/", ["https://compbio.mit.edu/people.html"], pubs=["https://compbio.mit.edu/papers.html"],
                          notes="MIT Computational Biology Group people page.")
P["Yoon Kim"] = lab("https://people.csail.mit.edu/yoonkim/", ["https://people.csail.mit.edu/yoonkim/"], alumni_ok=True,
                    pubs=["https://people.csail.mit.edu/yoonkim/pubs.html"], notes="Homepage students section. " + FIRST.format(2021))
P["Mina Konakovic Lukovic"] = lab("https://adg.csail.mit.edu/", ["https://adg.csail.mit.edu/?page_id=11"], alumni_ok=True,
                                  notes="Algorithmic Design Group people page. " + FIRST.format(2022))
P["Tim Kraska"] = lab("https://dsg.csail.mit.edu/", ["https://dsg.csail.mit.edu/people/"], wb_from=2018,
                      notes="Data Systems Group people page (shared with Samuel Madden). He moved from Brown in 2018.")
P["Steven Leeb"] = lab("https://www.rle.mit.edu/leeb", ["https://www.rle.mit.edu/leeb"], notes="RLE group page.")
P["Charles Leiserson"] = lab("https://supertech.mit.edu/", ["https://supertech.mit.edu/supertech-people/"],
                             pubs=["https://supertech.mit.edu/publications/"], notes="Supertech group people page.")
P["Andrew Lo"] = lab("https://alo.mit.edu/", ["https://alo.mit.edu/students/"], pubs=["https://alo.mit.edu/publications/"], notes="Students page.")
P["Tomás Lozano-Pérez"] = lab("https://lis.csail.mit.edu/", ["https://people.csail.mit.edu/tlp/students.html"],
                              pubs=["https://people.csail.mit.edu/tlp/publications.html"], notes="Students page; LIS group page shared with Leslie Kaelbling.")
P["Nancy Lynch"] = lab("https://groups.csail.mit.edu/tds/", ["https://groups.csail.mit.edu/tds/people.html"],
                       pubs=["https://groups.csail.mit.edu/tds/reflist.html"], notes="Theory of Distributed Systems group people page.")
P["Samuel Madden"] = lab("https://db.csail.mit.edu/madden/", ["https://db.csail.mit.edu/madden"], pubs=["https://db.csail.mit.edu/madden/pubs.html"],
                         notes="Homepage students section; DSG people page shared with Tim Kraska.")
P["Aleksander Mądry"] = lab("https://people.csail.mit.edu/madry/", ["https://people.csail.mit.edu/madry/"], notes="Homepage group section (on leave at OpenAI).")
P["Thomas Magnanti"] = lab(None, [], notes=NOPAGE)
P["Wojciech Matusik"] = lab("https://cdfg.mit.edu/", ["https://people.csail.mit.edu/wojciech/"], pubs=["https://cdfg.mit.edu/publications/"],
                            notes="Homepage group section; Computational Design & Fabrication Group site.")
P["Muriel Médard"] = lab("https://www.rle.mit.edu/ncrc/", ["https://www.rle.mit.edu/ncrc/"], notes="Network Coding and Reliable Communications group page.")
P["Silvio Micali"] = lab("https://people.csail.mit.edu/silvio/", [], notes=NOPAGE)
P["Robert Miller"] = lab("https://up.csail.mit.edu/", ["https://up.csail.mit.edu/"], notes="User Interface Design group page.")
P["Ankur Moitra"] = lab("http://people.csail.mit.edu/moitra/", ["https://people.csail.mit.edu/moitra/group.html"], alumni_ok=True,
                        notes="Group page. " + FIRST.format(2013))
P["Robert Morris"] = lab("https://pdos.csail.mit.edu/~rtm/", [], pubs=["https://pdos.csail.mit.edu/publications/"],
                         notes="Homepage has no students list; PDOS people page is recorded under M. Frans Kaashoek.")
P["Stefanie Mueller"] = lab("https://hcie.csail.mit.edu/", ["https://hcie.csail.mit.edu/"], alumni_ok=True,
                            pubs=["https://hcie.csail.mit.edu/publications.html"], notes="HCI Engineering Group page. " + FIRST.format(2017))
P["Anand V Natarajan"] = lab(None, [], notes=NOPAGE)
P["Alan Oppenheim"] = lab("https://dsp-group.mit.edu/", ["https://dsp-group.mit.edu/alumni/"], notes="DSP Group alumni page.")
P["Asu Ozdaglar"] = lab("https://asu.mit.edu/", ["https://asu.mit.edu/research-group/"], notes="Research group page.")
P["Pablo Parrilo"] = lab("https://www.mit.edu/~parrilo/", ["https://www.mit.edu/~parrilo/group.html"], pubs=["https://www.mit.edu/~parrilo/pubs/index.html"],
                         notes="Group page.")
P["Jonathan Ragan-Kelley"] = lab("https://people.csail.mit.edu/jrk/", ["https://people.csail.mit.edu/jrk"], wb_from=2020,
                                 notes="Homepage group section. He was at Berkeley 2018-2020 before MIT.")
P["Martin Rinard"] = lab("http://people.csail.mit.edu/rinard/", ["https://people.csail.mit.edu/rinard/people"], notes="Group people page.")
P["Ronald Rivest"] = lab("https://people.csail.mit.edu/rivest/", ["https://people.csail.mit.edu/rivest/students.html"],
                         pubs=["https://people.csail.mit.edu/rivest/pubs.html"], notes="Students page.")
P["Ronitt Rubinfeld"] = lab("https://people.csail.mit.edu/ronitt/", ["https://people.csail.mit.edu/ronitt/"],
                            pubs=["https://people.csail.mit.edu/ronitt/papers/index-pubs.html"], notes="Homepage students section.")
P["Daniela Rus"] = lab("https://danielarus.csail.mit.edu/", ["https://danielarus.csail.mit.edu/index.php/people/"],
                       pubs=["https://danielarus.csail.mit.edu/about-daniela-2/publications-2/"], notes="Distributed Robotics Lab people page.")
P["Daniel Sanchez"] = lab("https://people.csail.mit.edu/sanchez/", ["https://people.csail.mit.edu/sanchez"], alumni_ok=True,
                          notes="Homepage group section. " + FIRST.format(2012))
P["Arvind Satyanarayan"] = lab("https://vis.csail.mit.edu/", ["https://vis.csail.mit.edu"], alumni_ok=True,
                               notes="MIT Visualization Group page. " + FIRST.format(2018))
P["Devavrat Shah"] = lab("https://devavrat.mit.edu/", ["https://devavrat.mit.edu/members/"], pubs=["https://devavrat.mit.edu/publication/"],
                         notes="Members page.")
P["Nir Shavit"] = lab("https://groups.csail.mit.edu/mag/", ["https://groups.csail.mit.edu/mag/"], notes="Multicore Algorithmics Group page.")
P["Julian Shun"] = lab("https://jshun.csail.mit.edu/", ["https://jshun.csail.mit.edu/group.shtml"], alumni_ok=True,
                       notes="Group page. " + FIRST.format(2017))
P["Armando Solar-Lezama"] = lab("https://groups.csail.mit.edu/cap/", ["https://groups.csail.mit.edu/cap/"], notes="Computer-Aided Programming group page.")
P["Justin Solomon"] = lab("https://groups.csail.mit.edu/gdpgroup/", ["https://groups.csail.mit.edu/gdpgroup/team.html"], alumni_ok=True,
                          notes="Geometric Data Processing group team page. " + FIRST.format(2016))
P["David Sontag"] = lab("https://people.csail.mit.edu/dsontag/", ["https://people.csail.mit.edu/dsontag/"], wb_from=2017,
                        notes="Homepage group section. He moved from NYU in 2017.")
P["Collin Stultz"] = lab("https://cb.mit.edu/", ["https://cb.mit.edu/people/"], pubs=["https://cb.mit.edu/publications/"], notes="Computational Biophysics group people page.")
P["Gerald Sussman"] = lab("https://groups.csail.mit.edu/mac/users/gjs/", [], notes=NOPAGE)
P["Vivienne Sze"] = lab("https://eems.mit.edu/", ["https://eems.mit.edu/people/"], alumni_ok=True,
                        pubs=["https://eems.mit.edu/publications/"], notes="EEMS group people page. " + FIRST.format(2013))
P["Peter Szolovits"] = lab("https://mit-medg.github.io/", ["https://mit-medg.github.io/people.html", "https://mit-medg.github.io/alumni.html"],
                           notes="Clinical Decision Making Group people and alumni pages.")
P["Bruce Tidor"] = lab(None, [], notes=NOPAGE)
P["Antonio Torralba"] = lab("https://groups.csail.mit.edu/vision/torralbalab/", ["https://groups.csail.mit.edu/vision/torralbalab/"],
                            notes="Torralba lab page.")
P["Caroline Uhler"] = lab("https://www.carolineuhler.com/", ["https://www.carolineuhler.com/current-team-members", "https://www.carolineuhler.com/alumni"],
                          pubs=["https://www.carolineuhler.com/publications"], alumni_ok=True,
                          notes="Current team members and alumni pages. " + FIRST.format(2015))
P["Vinod Vaikuntanathan"] = lab("https://people.csail.mit.edu/vinodv/", ["https://people.csail.mit.edu/vinodv/group.html"],
                                pubs=["https://people.csail.mit.edu/vinodv/pubs.html"], notes="Group page.")
P["Martin Wainwright"] = lab("https://wainwrigwork.github.io/", ["https://wainwrigwork.github.io/group.html"], wb_from=2022,
                             notes="Group page. He moved from Berkeley in 2022: Berkeley students are left out unless placed at MIT.")
P["Jacob White"] = lab("https://www.rle.mit.edu/cpg/", ["https://www.rle.mit.edu/cpg/people_students.htm"], notes="RLE Computational Prototyping Group students page.")
P["Ryan Williams"] = lab("https://people.csail.mit.edu/rrw/", ["https://people.csail.mit.edu/rrw/"], wb_from=2017,
                         notes="Homepage students section. He moved from Stanford in 2017.")
P["Virginia Vassilevska Williams"] = lab("https://people.csail.mit.edu/virgi/", ["https://people.csail.mit.edu/virgi/"], wb_from=2017,
                                         pubs=["https://people.csail.mit.edu/virgi/pubyear.html"], notes="Homepage students section. She moved from Stanford in 2017.")
P["Gregory Wornell"] = lab("https://sia.mit.edu/", ["https://sia.mit.edu/people/", "https://sia.mit.edu/people/alumni/"],
                           notes="Signals, Information and Algorithms Lab people and alumni pages (JS-rendered).")
P["Mengjia Yan"] = lab("https://people.csail.mit.edu/mengjia/", ["https://people.csail.mit.edu/mengjia/"], alumni_ok=True,
                       notes="Homepage group section. " + FIRST.format(2020))
P["Nickolai Zeldovich"] = lab("https://people.csail.mit.edu/nickolai/", ["https://people.csail.mit.edu/nickolai/"], notes="Homepage students section.")
P["Jas Brooks"] = lab("https://mit-pel.com/", ["https://mit-pel.com/team/"], alumni_ok=True, pubs=["https://mit-pel.com/publications/"],
                      notes="Lab team page. " + FIRST.format(2026))
P["Zana Bucinca"] = lab("https://zbucinca.github.io/", [], pubs=["https://zbucinca.github.io/publications/"], notes=NOPAGE + " (joined MIT 2026)")
P["Mohsen Ghaffari"] = lab("https://people.csail.mit.edu/ghaffari/", ["https://people.csail.mit.edu/ghaffari/"], wb_from=2022,
                           notes="Homepage group section. He moved from ETH Zurich in 2022: ETH students are left out unless placed at MIT.")
P["Mitchell Gordon"] = lab("https://mitchellg.github.io/", [], notes=NOPAGE + " (joined MIT 2025)")
P["Berthold Horn"] = lab("https://people.csail.mit.edu/bkph", [], pubs=["https://people.csail.mit.edu/bkph/publications"], notes=NOPAGE)
P["Omar Khattab"] = lab("https://omarkhattab.com/", ["https://omarkhattab.com/"], alumni_ok=True, notes="Homepage. " + FIRST.format(2026))
P["Vincent Sitzmann"] = lab("https://www.vincentsitzmann.com/", ["https://www.vincentsitzmann.com/"], alumni_ok=True,
                            notes="Homepage group section. " + FIRST.format(2022))
P["Michael Stonebraker"] = lab("http://db.csail.mit.edu/", [], notes=NOPAGE)
P["Christopher Terman"] = lab("https://people.csail.mit.edu/cjt/", [], notes=NOPAGE)
P["Victor Zue"] = lab("https://www.sls.csail.mit.edu/people/zue.shtml", [], notes=NOPAGE)
P["Ted Adelson"] = lab("http://persci.mit.edu/", [], notes="persci.mit.edu people page not usable; " + NOPAGE)
P["Bonnie Berger"] = lab("https://people.csail.mit.edu/bab/", ["https://people.csail.mit.edu/bab/members.html"], notes="Group members page.")
P["Tim Berners-Lee"] = lab("https://www.w3.org/People/Berners-Lee/", [], notes=NOPAGE)
P["Andreea Bobu"] = lab("https://clear.csail.mit.edu/", ["https://clear.csail.mit.edu/people.html"], alumni_ok=True,
                        pubs=["https://clear.csail.mit.edu/publications.html"], notes="CLEAR lab people page. " + FIRST.format(2024))
P["Michael Cafarella"] = lab("https://people.csail.mit.edu/michjc/", ["https://people.csail.mit.edu/michjc/"], wb_from=2020,
                             notes="Homepage students section. He moved from Michigan in 2020.")
P["David Clark"] = lab("https://groups.csail.mit.edu/ana/", ["https://groups.csail.mit.edu/ana/People/index.html"],
                       pubs=["https://groups.csail.mit.edu/ana/Publications/index.html"], notes="Advanced Network Architecture group people page (shared with Karen Sollins).")
P["Alan Edelman"] = lab("https://julia.mit.edu/", ["https://julia.mit.edu/people/"], pubs=["https://julia.mit.edu/publications/"], notes="Julia Lab people page.")
P["Jim Glass"] = lab("https://sls.csail.mit.edu/", ["https://sls.csail.mit.edu/people/"], pubs=["https://sls.csail.mit.edu/publications/"],
                     notes="Spoken Language Systems group people page.")
P["D. Fox Harrell"] = lab("https://virtuality.mit.edu/", ["https://virtuality.mit.edu/"], notes="Center for Advanced Virtuality page.")
P["Lalana Kagal"] = lab("https://dig.csail.mit.edu/", ["https://dig.csail.mit.edu/people.html"], pubs=["https://dig.csail.mit.edu/publications.html"],
                        notes="Decentralized Information Group people page.")
P["Boris Katz"] = lab("https://groups.csail.mit.edu/infolab/", ["https://groups.csail.mit.edu/infolab/people.html"],
                      pubs=["https://groups.csail.mit.edu/infolab/publications.html"], notes="InfoLab people page.")
P["Jonathan Kelner"] = lab("https://people.csail.mit.edu/kelner/", [], notes=NOPAGE)
P["John Leonard"] = lab("https://marinerobotics.mit.edu/", ["https://marinerobotics.mit.edu/people"], pubs=["https://marinerobotics.mit.edu/publications"],
                        notes="Marine Robotics Group people page.")
P["Rachit Nigam"] = lab("https://flame.csail.mit.edu/", ["https://flame.csail.mit.edu"], alumni_ok=True, notes="FLAME lab page. " + FIRST.format(2026))
P["Una-May O'Reilly"] = lab("https://alfagroup.csail.mit.edu/", ["https://alfagroup.csail.mit.edu/people"], pubs=["https://alfagroup.csail.mit.edu/publications"],
                            notes="ALFA group people page (shared with Erik Hemberg).")
P["Aude Oliva"] = lab("http://cvcl.mit.edu/", [], notes="cvcl.mit.edu people page not usable; " + NOPAGE)
P["Tomaso Poggio"] = lab("https://poggio-lab.mit.edu/", ["https://poggio-lab.mit.edu/people"], pubs=["https://poggio-lab.mit.edu/publications"],
                         notes="Poggio lab people page.")
P["Nicholas Roy"] = lab("https://robustrobotics.github.io/", ["https://robustrobotics.github.io/people.html"],
                        pubs=["https://robustrobotics.github.io/publications.html"], notes="Robust Robotics Group people page.")
P["Julie Shah"] = lab("https://interactive.mit.edu/", ["https://interactive.mit.edu/people"], pubs=["https://interactive.mit.edu/publications/"],
                      notes="Interactive Robotics Group people page.")
P["Peter Shor"] = lab("https://math.mit.edu/~shor/", [], pubs=["https://math.mit.edu/~shor/elecpubs.html"], notes=NOPAGE)
P["Howard Shrobe"] = lab("https://people.csail.mit.edu/hes/", [], notes=NOPAGE)
P["Michael Sipser"] = lab("http://www-math.mit.edu/~sipser/", [], notes=NOPAGE)
P["Russ Tedrake"] = lab("https://locomotion.csail.mit.edu/", ["https://locomotion.csail.mit.edu/people.html"], notes="Robot Locomotion Group people page.")
P["Daniel Weitzner"] = lab("https://internetpolicy.mit.edu/", [], notes="internetpolicy.mit.edu disallows our crawler in robots.txt; " + NOPAGE)
P["Brian Williams"] = lab("https://mers.csail.mit.edu/", ["https://mers.csail.mit.edu/people"], pubs=["https://mers.csail.mit.edu/publications"],
                          notes="MERS group people page.")
P["Joshua Tenenbaum"] = lab("https://cocosci.mit.edu/", ["https://cocosci.mit.edu/newpeoplepage2/"], notes="Computational Cognitive Science group people page.")
P["Erik Hemberg"] = lab("https://alfagroup.csail.mit.edu/", [], notes="ALFA group people page recorded under Una-May O'Reilly.")
P["Karen Sollins"] = lab("https://groups.csail.mit.edu/ana/", [], notes="ANA group people page recorded under David Clark.")
P["Neil Thompson"] = lab("https://futuretech.mit.edu/", ["https://futuretech.mit.edu/team"], alumni_ok=True, notes="FutureTech team page.")
P["Suvrit Sra"] = lab("https://optml.mit.edu/", ["https://optml.mit.edu/group.html"], notes="OPTML group page (he moved to TUM in 2024).")
P["Arvind"] = lab("https://csg.csail.mit.edu/", [], notes="Computation Structures Group (Arvind died in 2024); " + NOPAGE)
P["Jack Dennis"] = lab(None, [], notes=NOPAGE)
P["John Fisher"] = lab("http://groups.csail.mit.edu/vision/sli/", [], notes=NOPAGE)
P["Michael Goemans"] = lab("http://math.mit.edu/~goemans/", ["https://math.mit.edu/~goemans/students.html"],
                           pubs=["http://math.mit.edu/~goemans/publ.html"], notes="Students page.")
P["Ruth Rosenholtz"] = lab("http://persci.mit.edu/", [], notes=NOPAGE)
P["Ron Weiss"] = lab("http://weisslab.mit.edu/", [], notes=NOPAGE)
P["Roger Mark"] = lab("https://lcp.mit.edu/", ["https://lcp.mit.edu/people"], pubs=["https://lcp.mit.edu/publications"], notes="LCP people page.")
P["Li-Shiuan Peh"] = lab(None, [], notes="Moved to NUS in 2016; " + NOPAGE)
P["Patrick Winston"] = lab(None, [], notes="Died in 2019; " + NOPAGE)
P["Scott Aaronson"] = lab(None, [], notes="At UT Austin since 2016; " + NOPAGE)
P["Dana Moshkovitz"] = lab(None, [], notes="At UT Austin since 2017; " + NOPAGE)
P["Dirk Englund"] = lab("https://www.rle.mit.edu/qp/", ["https://www.rle.mit.edu/qp/"], notes="Quantum Photonics Lab page.")
P["Jing Kong"] = lab(None, [], notes=NOPAGE)
P["Yury Polyanskiy"] = lab("https://people.lids.mit.edu/yp/homepage/", ["https://people.lids.mit.edu/yp/homepage/groups.shtml"],
                           pubs=["https://people.lids.mit.edu/yp/homepage/papers.shtml"], notes="Group page.")
P["Sangeeta Bhatia"] = lab("https://www.lmrt.mit.edu/", ["https://www.lmrt.mit.edu/team"], pubs=["https://www.lmrt.mit.edu/publications"], notes="LMRT team page.")
P["YuFeng (Kevin) Chen"] = lab("https://smrl.mit.edu/", ["https://smrl.mit.edu/people/"], alumni_ok=True, pubs=["https://smrl.mit.edu/publications/"],
                               notes="Soft and Micro Robotics Lab people page. " + FIRST.format(2020))
P["William D. Oliver"] = lab("https://equs.mit.edu/", ["https://equs.mit.edu/graduate-students/", "https://equs.mit.edu/undergraduate-students/",
                                                       "https://equs.mit.edu/visiting-members/", "https://equs.mit.edu/alumni/"],
                             pubs=["https://equs.mit.edu/publications/"], notes="EQuS group member pages.")
P["Rajeev Ram"] = lab("https://www.rle.mit.edu/poe/", [], notes=NOPAGE)
P["Luca Daniel"] = lab("https://www.rle.mit.edu/cpg/", ["https://www.rle.mit.edu/cpg/people_students.htm"], notes="RLE Computational Prototyping Group students page.")
P["Munther Dahleh"] = lab("https://dahleh.mit.edu/", [], notes=NOPAGE)
P["Jeffrey Shapiro"] = lab("https://www.rle.mit.edu/oqe/", [], notes=NOPAGE)
P["Elfar Adalsteinsson"] = lab("https://www.rle.mit.edu/mri/", ["https://www.rle.mit.edu/mri/people/"], pubs=["https://mri.mit.edu/publications/"],
                               notes="MRI group people page.")
P["Thomas Heldt"] = lab(None, [], notes=NOPAGE)
P["Lizhong Zheng"] = lab("https://lizhongzheng.mit.edu/", [], pubs=["https://lizhongzheng.mit.edu/publications/"], notes=NOPAGE)
P["George Verghese"] = lab(None, [], notes=NOPAGE)
P["Vincent Chan"] = lab("https://www.rle.mit.edu/cnsg/", [], notes=NOPAGE)
P["Dennis Freeman"] = lab("https://www.rle.mit.edu/micromechanics/", [], notes=NOPAGE)
P["Alexandre Megretski"] = lab(None, [], notes=NOPAGE)
P["Priya Donti"] = lab("https://priyadonti.com/", ["https://priyadonti.com/group"], alumni_ok=True, pubs=["https://priyadonti.com/publications"],
                       notes="Group page. " + FIRST.format(2023))
P["Jae Lim"] = lab(None, [], notes=NOPAGE)
P["Thomas Heldt"] = lab(None, [], notes=NOPAGE)
P["Ron Weiss"] = lab("http://weisslab.mit.edu/", [], notes=NOPAGE)
P["Jing Kong"] = lab(None, [], notes=NOPAGE)
P["Elfar Adalsteinsson"]["notes"] += ""
P["Ted Adelson"]["notes"] += ""
P["Aude Oliva"]["notes"] += ""
P["Ruth Rosenholtz"]["notes"] += ""
P["Yael Kalai"] = lab(None, [], notes=NOPAGE + " (also at Microsoft Research)")
P["Hari Balakrishnan"].update(people=[], wb=["https://nms.csail.mit.edu/people.html"],
                              notes="nms.csail.mit.edu timed out live; the NMS people page is used via Wayback captures only.")
P["Erik Demaine"].update(people=[], wb=[], pubs=[Pubs("https://erikdemaine.org/papers/")],
                         notes="erikdemaine.org has no students page (students/ returns 404); papers page used.")
P["Daniela Rus"].update(people=[], wb=["https://danielarus.csail.mit.edu/index.php/people/"], pubs=[],
                        notes="danielarus.csail.mit.edu disallows our crawler in robots.txt (blocked); Wayback captures of the people page are used.")
P["Bonnie Berger"].update(people=[], wb=[], notes="Group members page returns 404; " + NOPAGE)
from lpauto import rx_members, table_members  # noqa: E402

# ---------------------------------------------------------------- corrections after review (MIT)
P["Neil Thompson"].update(drop=["Predicting AI's Future", "AIGEN Inaugural Convening"], drop_desc=r"(?i)^\W*affiliat",
                          span={"https://futuretech.mit.edu/team": ("Leadership Neil Thompson", None)})
P["Neil Thompson"]["notes"] += " Affiliate professors/researchers (other institutions) are left out."
P["William D. Oliver"].update(people=["https://equs.mit.edu/graduate-students/", "https://equs.mit.edu/undergraduate-students/",
                                      "https://equs.mit.edu/visiting-members/"],
                              rows=table_members(SCH, "https://equs.mit.edu/alumni/", note=None),
                              min_last_year=2016)
P["William D. Oliver"]["notes"] = ("EQuS group member pages (graduate students, undergraduates, visiting members) and the "
                                   "alumni table (Name, Position, Dates, Next position); alumni whose dates end before 2016 "
                                   "are left out.")
_TL = "https://groups.csail.mit.edu/vision/torralbalab/"
P["Antonio Torralba"].update(
    span={_TL: ("Lab Members Adrián", "Past Students and Postdocs")}, wb=[],
    rows=rx_members(SCH, _TL, r"(?P<name>[A-Z][^,()\.]{2,40}?|Dim P\. Papadopoulos) \((?P<role>Graduated|Postdoc|Research scientist|Grad\. Student|Visiting student)[^)0-9]*(?P<y1>(?:19|20)\d\d)?\)",
                    role_map={"Graduated": "phd", "Postdoc": "postdoc", "Research scientist": "other", "Grad. Student": "phd",
                              "Visiting student": "other"},
                    span=("Past Students and Postdocs", "Agata Lapedriza"), note="'Past Students and Postdocs' (newest first)"))
P["Antonio Torralba"]["notes"] = ("Lab page 'Lab Members' (current) and 'Past Students and Postdocs' (a newest-first list; "
                                  "entries from Andrew Owens/Aditya Khosla (graduated 2016) upward are used, older ones left "
                                  "out). The rest of the page is publications.")
_CD = "https://people.csail.mit.edu/delimitrou/Students.html"
P["Christina Delimitrou"].update(people=[], wb=[], rows=R(SCH, _CD, [
    ("Varun Gohil", "phd", None, "Students Varun Gohil (EECS, Ph.D.)"),
    ("Qihang Chen", "phd", None, "Qihang Chen (EECS, Ph.D.)"),
    ("Christos Zarkos", "phd", None, "Christos Zarkos (EECS, Ph.D.)"),
    ("Ansa Schmulbach", "phd", None, "Ansa Schmulbach (EECS, Ph.D., co-advised with Prof. Daniel Sanchez)"),
    ("Nevena Stojkovic", "undergraduate", None, "Nevena Stojkovic (EECS, BS)"),
    ("Nikita Lazarev", "phd", [None, 2025], "Nikita Lazarev (EECS, Ph.D., co-advised with Prof. Zhiru Zhang), February 2025"),
], note="Students page"))
P["Christina Delimitrou"]["notes"] = ("Students page: current EECS students and Nikita Lazarev (EECS Ph.D. 2025) are MIT; "
                                      "graduates listed with ECE/CS departments and the M.Eng./undergraduate graduates "
                                      "(2016-2022) are her Cornell students and are left out.")
P["Caroline Uhler"]["drop"] = ["TU Eindhoven", "PDT Partners", "HAP Capital"]
P["Tomás Lozano-Pérez"].update(people=[], wb=[], notes=("students.html lists surnames of (mostly pre-2016) students only; the "
                                                        "LIS group people page is recorded under Leslie Kaelbling."))
P["William D. Oliver"]["drop_undated_rows"] = True


def _drop(pi, *names_, note=None):
    P[pi].setdefault("drop", [])
    P[pi]["drop"] = list(P[pi]["drop"]) + list(names_)
    if note:
        P[pi]["notes"] += " " + note


_drop("Fadel Adib", "Ocean IoT", "CBS This Morning", "In-Vivo Networking", "Tech Xplore", "Huffington Post", "Bloomberg TV",
      "Link Budget Tool", "ONR Early Career Grant", "Battery-free Underwater Camera", "Underwater-to-air Communications",
      "Batteryless Micro-implants", "RFID Micro-sensing")
_drop("Sara Beery", "AI-Assisted Biodiversity Monitoring", "MegaDetector Model Codebase", "Caltech Camera Traps Dataset")
_drop("Guy Bresler", "David Gamarnik", "David Tse", "Bruce Hajek", note="Advisors/collaborators named on the homepage are left out.")
_drop("Adam Chlipala", "Advisory-Board Memberships", "SIGPLAN Climate Change")
_drop("Henry Corrigan-Gibbs", "Charles River Crypto Day", "Dan Boneh", "Bryan Ford", note="His own advisors are left out.")
_drop("Constantinos Daskalakis", "NPR Planet Money Episodes")
_drop("Srini Devadas", "Lee")
_drop("Frederic Durand", "Kate Saenko", "Georges Perec")
_drop("Manya Ghobadi", "High-Performance Cloud Infrastructure", "Hardware-Software Co-design", "On-Fiber Photonic Computing M. Yang",
      "WDM-Enabled Photonic Edge Computing", "NetFPGA-based Precise Traffic Generation", "General Co-Chair", "ACM HotNets",
      "ACM CoNEXT", "ACM HotMobile")
_drop("Polina Golland", "Georg Langs")
_drop("Kaiming He", "Faster R-CNN", "Mask R-CNN", "Rethinking ImageNet Pre-training Kaiming He", "Xiaolong Wang", "Tsung-Yi Lin",
      "Priya Goyal", "Saining Xie", "Shaoqing Ren", "Tiezheng Ge", "Guided Image Filtering Kaiming He", "PAMI Everingham Prize",
      note="Coauthors from his industry years named on the homepage are left out.")
_drop("Sam Hopkins", "Prasad Raghavendra", "Luca Trevisan", "David Steurer", note="His own advisors are left out.")
_drop("Phillip Isola", '"Robot-Use Agents"')
_drop("Stefanie Jegelka", "Nikos Karalias Ya-Wei Eileen Lin")
_drop("Manolis Kellis", "Non-Coding Exon Structural Analyses")
_drop("Yoon Kim", "Alexander Rush", "Roger Levy", "Log-Linear Attention", note="His advisor and collaborators are left out.")
_drop("Muriel Médard", "L Rapp", "YA Biyikoglu", "K Galligan", "GRAND-assisted Demodulation")
_drop("Stefanie Mueller", "Sprayable User Interfaces")
_drop("Jonathan Ragan-Kelley", "Pat Hanrahan", "Mark Horowitz", "Frédo Durand", note="His own advisors are left out.")
_drop("Daniel Sanchez", "Christos Kozyrakis", "Modeling Cache Performance Beyond LRU", note="His own advisor is left out.")
_drop("Arvind Satyanarayan", "Inria International Chair", "Semantic Regexes", "Tactile Vega-Lite")
_drop("Nir Shavit", "Multicore Algorithmics")
_drop("David Sontag", "D. Choo", "K. Kuang", "S. Arora", "T. Koo")
_drop("Collin Stultz", "RLRVI Risk Calculator")
_drop("Mengjia Yan", "Josep Torrellas", "ISCA Lightning Talk", "Tom's Hardware", "Louis D. Smullin", note="Her own advisor is left out.")
_drop("Nickolai Zeldovich", "Multi-Key Searchable Encryption", "Secure In-Band Wireless Pairing", "Northrop Grumman")
_drop("Mohsen Ghaffari", "Bernhard Haeupler")
P["Mohsen Ghaffari"]["min_last_year"] = 2023
P["Mohsen Ghaffari"]["notes"] += " Advisees whose stated dates end before 2023 (ETH Zurich years) are left out."
_drop("Omar Khattab", "Reasoning-Intensive Regression D Tchuindjo")
_drop("Andreea Bobu", "Rooftop BBQ", "Boda Borg")
_drop("Una-May O'Reilly", "Cyber Agents")
_drop("Tomaso Poggio", "Universita’ di Genova", "Lorenzo Rosasco")
_drop("Dirk Englund", "Nano Letters")
_drop("Sangeeta Bhatia", "Laura Charlesworth Administrative Coordinator")
P["Ronald Rivest"].update(people=[], wb=[], notes=("students.html lists his doctoral students without dates, all of whom "
                                                   "finished before 2016 (latest: Emily Shen); no members in the window."))
P["Tommi Jaakkola"]["years"] = {"Octavian Ganea": None}
P["Antonio Torralba"]["rows"] = [r for r in P["Antonio Torralba"]["rows"] if not r["name"].startswith("Past Students")] + R(
    SCH, "https://groups.csail.mit.edu/vision/torralbalab/", [
        ("Yichen Li", "phd", [None, 2026], "Past Students and Postdocs Yichen Li (Graduated 2026)")])


def _spec(pi, url, spec, note=None):
    for p in P[pi]["pubs"]:
        if p.get("pubs_page") == url:
            p["spec"] = spec
            if note:
                p["note"] = note
            return
    P[pi]["pubs"].append(Pubs(url, spec, note=note))


_spec("Manolis Kellis", "https://compbio.mit.edu/papers.html", {"item": "div.row.aln-middle", "title": "h4"})
_spec("Sangeeta Bhatia", "https://www.lmrt.mit.edu/publications", {"item": "div.summary-item", "title": "a.summary-title-link", "year": "time"})
_spec("William D. Oliver", "https://equs.mit.edu/publications/", {"item": "p", "title": "strong"})
_spec("Una-May O'Reilly", "https://alfagroup.csail.mit.edu/publications", {"item": "li", "title_rx": "\\((?:19|20)\\d\\d[a-z]?\\)\\.\\s*(.+?)\\.(?:\\s|$)"})
P["Boris Katz"]["pubs"] = [Pubs("https://groups.csail.mit.edu/infolab/publications.html", {"skip_rx": "(?i)\\b(news|thinks|learns to|database of|mit news|wired|times)\\b"})]
_spec("Sangeeta Bhatia", "https://www.lmrt.mit.edu/publications", {"item": "div.summary-item", "title": "a.summary-title-link"},
      note="Squarespace list; item dates are posting dates, so the year comes from the citation text")
P["William D. Oliver"]["wb"] = []
P["Kaiming He"]["wb"] = []
P["Kaiming He"]["notes"] += " Wayback captures mix in publications/coauthors and are not used."
_drop("Constantinos Daskalakis", "Kalai Prize", "ECCC Report", "Greek Stochastics Theta", "Sanjeev Arora",
      "Christos Papadimitriou", "Fotini Christia")
_drop("Tomaso Poggio", "Shimon Ullman", "Lucia Vaina")
_drop("Roger Mark", "PhysioNet Critical Care")
_drop("Alan Edelman", "Philip Julia Expert")
P["Andrew Lo"]["alumni_pages"] = ["https://alo.mit.edu/students/"]
P["Andrew Lo"]["drop_heads"] = r"Wharton"
P["Andrew Lo"]["notes"] += " The PhD list is all-time and undated (kept only when dated); Wharton students are left out."
P["Sangeeta Bhatia"]["alumni_pages"] = ["https://www.lmrt.mit.edu/team"]
P["Sangeeta Bhatia"]["notes"] += " The team page mixes current and past members without dates; only dated rows are kept."
P["Martin Rinard"]["drop_heads"] = r"MEng Students|USCB|UCSB"
P["Martin Rinard"]["notes"] += " MEng (pre-2016) and UCSB students are left out."
_drop("Constantinos Daskalakis", "Constantine P. Cavafy")
P["Suvrit Sra"]["drop_heads"] = r"advised on some projects|committee member|Master's Theses"
P["Gregory Wornell"]["drop_heads"] = r"Research Affiliates|Industrial Affiliate"
_drop("Gregory Wornell", "Dr.Jongha Ryu")
_drop("Wojciech Matusik", "B. Bickel", "S. Coros", "T. J. K. Buchner", "Professional Ed.")
_drop("Armando Solar-Lezama", "Multi-Language Transformation")
P["Andrew Lo"]["require_years"] = True
P["Andrew Lo"]["drop_heads"] = r"(?i)wharton"
P["Andrew Lo"]["notes"] += (" The students page lists PhD students of all eras without dates (and his Wharton students); "
                            "only rows with stated 2016+ years are kept.")
P["Sangeeta Bhatia"]["span"] = {"https://www.lmrt.mit.edu/team": ("Meet our team", "Alumni Postdoctoral researchers")}
P["Sangeeta Bhatia"]["wb"] = []
P["Sangeeta Bhatia"]["notes"] = ("LMRT team page, current team only (the page's undated 'Alumni' lists span her whole career "
                                 "and are left out).")
P["Martin Rinard"].update(people=[], wb=[], notes=("Group people page lists post-docs, research scientists, MEng students "
                                                   "and group members of all eras without dates; no row can be placed in "
                                                   "2016-2026 from it, so none is recorded."))
P["Asu Ozdaglar"].update(people=[], wb=[], notes=("Research group page lists current and former members without dates "
                                                  "(former members mostly before 2016); not used."))
P["Collin Stultz"]["drop_heads"] = r"(?i)alumni|medical student"
P["Collin Stultz"]["notes"] += " Undated alumni sections are left out."
P["D. Fox Harrell"]["drop_heads"] = r"(?i)advisory|stanford|art of teaching|moon disaster"
_drop("Elfar Adalsteinsson", "Arlene Wint", "Cindy Higgins", note="Administrative staff left out.")
_drop("Gregory Wornell", "Tricia O'Donnell", note="Administrative staff left out.")
