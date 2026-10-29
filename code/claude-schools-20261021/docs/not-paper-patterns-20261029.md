# Not-paper patterns, measured on the 2026-10-29 build

Each pattern of `tools/pi_hierarchy.py` `not_a_paper` (R-PAP-18, R-PAP-19, R-PAP-22) and `doi_year_conflict` (R-PAP-23), applied to
every lab-paper row of the 2026-10-29 build (115,345 rows, the six packages the accuracy sample measured). A row is counted under
the first tag that matches, in the order the function tests them. Ten samples per tag (seeded random draw, seed 20261029). The
single-author abstract tag is shown before the build-time guard that keeps a row whose title the PI's DBLP page lists with co-authors.

| tag | princeton | cmu | epfl | mit | berkeley | stanford | all |
|---|---|---|---|---|---|---|---|
| `meeting_abstract:venue` | 28 | 27 | 36 | 166 | 68 | 236 | 561 |
| `meeting_abstract:doi` | 19 | 47 | 26 | 66 | 20 | 111 | 289 |
| `editorial` | 22 | 74 | 44 | 47 | 31 | 31 | 249 |
| `dissertation` | 1 | 0 | 0 | 5 | 0 | 231 | 237 |
| `software_record` | 17 | 68 | 46 | 25 | 25 | 50 | 231 |
| `meeting_abstract:journal` | 19 | 43 | 21 | 63 | 4 | 70 | 220 |
| `meeting_abstract:single_author` | 16 | 43 | 7 | 46 | 32 | 25 | 169 |
| `repository_supplement` | 5 | 36 | 19 | 16 | 4 | 7 | 87 |
| `machine_translation` | 2 | 10 | 9 | 7 | 11 | 5 | 44 |
| `workshop_proposal` | 2 | 14 | 5 | 17 | 2 | 1 | 41 |
| `erratum` | 1 | 10 | 4 | 2 | 5 | 17 | 39 |
| `dagstuhl_report` | 1 | 20 | 7 | 4 | 4 | 2 | 38 |
| `meeting_abstract:title` | 2 | 1 | 2 | 13 | 1 | 12 | 31 |
| `oberwolfach_report` | 2 | 3 | 6 | 8 | 7 | 2 | 28 |
| `award_announcement` | 3 | 1 | 0 | 10 | 0 | 2 | 16 |
| `tribute` | 0 | 3 | 0 | 5 | 0 | 0 | 8 |
| `highlights_column` | 1 | 0 | 0 | 1 | 0 | 0 | 2 |
| `meeting_abstract:keynote` | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| `doi_year_conflict` | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| **all** | 141 | 400 | 232 | 501 | 214 | 805 | 2293 |

## `meeting_abstract:venue` (561)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| stanford | Kawin Setsompop | Rapid implicit Spatio-Temporal Field Estimation and Correction for Diffusion MRI (D-FESTiV | Proceedings on CD-ROM - International Society | conference-paper | 10.58530/2025/0513 |
| stanford | Simona Onori | On-Board Diagnostics for Li-Ion Batteries Using Electrochemical Impedance Spectroscopy (EI | ECS Meeting Abstracts | conference-abstract | 10.1149/ma2024-01532802mtgabs |
| mit | Elfar Adalsteinsson | Change in T2* measurements of placenta during Braxton Hicks contractions | Proceedings on CD-ROM - International Society | conference-paper | 10.58530/2022/4018 |
| stanford | Mert Pilanci | Greedy Learning for Memory-Efficient Self-Supervised MRI Reconstruction | Proceedings on CD-ROM - International Society | conference-paper | 10.58530/2023/2921 |
| stanford | Kawin Setsompop | Optimization of Magnetic Resonance Fingerprinting with Subspace Reconstruction | Proceedings on CD-ROM - International Society | conference-paper | 10.58530/2023/0428 |
| berkeley | Michael Lustig | ResoNet: Physics Informed Deep Learning based Off-Resonance Correction Trained on Syntheti | Proceedings on CD-ROM - International Society | conference-paper | 10.58530/2022/0555 |
| mit | Dirk Englund | Controlling Quantum Transport with a Programmable Nanophotonic Processor | Bulletin of the American Physical Society | article |  |
| stanford | Kawin Setsompop | Estimating multicomponent 2D relaxation spectra with a ViSTa-MR fingerprinting acquisition | Proceedings on CD-ROM - International Society | conference-paper | 10.58530/2022/4389 |
| stanford | Jennifer A McNab | Can Tractography Predict Electrophysiological Connectivity? | Proceedings on CD-ROM - International Society | conference-paper | 10.58530/2025/1432 |
| epfl | Jean-Philippe Thiran | Advancing Brain Morphometry at 7T: A Pilot Study on Epilepsy Patients | Proceedings on CD-ROM - International Society | conference-paper | 10.58530/2025/4286 |

## `meeting_abstract:doi` (289)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| mit | Dara Entekhabi | Diurnal Vegetation Moisture Dynamics and Water Stress: Insights from GNSS Reflectometry-De |  | conference-abstract | 10.5194/egusphere-egu24-15823 |
| mit | Manolis Kellis | Abstract 6425: Functional roles of enhancers in immune microenvironment & immunotherapy re | Cancer Research | conference-abstract | 10.1158/1538-7445.am2023-6425 |
| epfl | Devis Tuia | Linking deep learning-based forest cover maps to treeline spatio-temporal patterns |  | conference-abstract | 10.5194/egusphere-egu24-9480 |
| stanford | James Zou | Abstract 10345: Video-Based Deep Learning Model for Automated Assessment of Ejection Fract | Circulation | conference-abstract | 10.1161/circ.144.suppl_1.10345 |
| mit | Vivek F. Farias | Abstract 6571: Plasma protein-protein interactome (PPI) maps derived from the protein coro | Cancer Research | conference-abstract | 10.1158/1538-7445.am2020-6571 |
| stanford | Anshul Kundaje | Deep Learning the Cis-Regulatory Code of Epigenomic Rewiring By Fusion Transcription Facto | Blood | conference-abstract | 10.1182/blood-2024-209601 |
| epfl | Dimitri Van De Ville | Abstract P357: Deep Learning Building on Prior Ischemic Core Segmentation Improves Predict | Stroke | conference-abstract | 10.1161/str.52.suppl_1.p357 |
| mit | Polina Golland | Abstract WP102: Risk Score Estimation For The Prognostication Of Post-stroke Functional In | Stroke | conference-abstract | 10.1161/str.53.suppl_1.wp102 |
| stanford | John M. Pauly | Abstract WP53: Improved Prediction of the Final Infarct From Acute Stroke Neuroimaging Usi | Stroke | conference-abstract | 10.1161/str.49.suppl_1.wp53 |
| cmu | John Michael Galeotti | Effect of Lung Ultrasound Didactics on Trainees' Interpretation of Lung Sonograms |  | conference-abstract | 10.1164/ajrccm-conference.2024.209.1_meetingabstracts.a1505 |

## `editorial` (249)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| berkeley | Jan M. Rabaey | Guest Editorial: Alternative Computing and Machine Learning for Internet of Things | IEEE Transactions on Very Large Scale Integra | editorial | 10.1109/tvlsi.2017.2742098 |
| cmu | Ding Zhao | Guest Editorial Special Issue on Artificial Intelligence for Autonomous Unmanned System Ap | IEEE Transactions on Automation Science and E | editorial | 10.1109/tase.2022.3208458 |
| princeton | Mona Singh | Preface | Journal of Computational Biology | article | 10.1177/15578666251412452 |
| cmu | Carlee Joe-Wong | Introduction to the Special Issue on Full-Stack Codesign for Robust and Secure AI-Enabled  | ACM Journal on Autonomous Transportation Syst | editorial | 10.1145/3665989 |
| mit | Eytan Modiano | Guest Editorial Age of Information | IEEE Journal on Selected Areas in Communicati | editorial | 10.1109/jsac.2021.3066816 |
| cmu | Carolyn P Rose | Editorial: Nine elements for robust collaborative learning analytics: A constructive colla | International Journal of Computer-Supported C | editorial | 10.1007/s11412-023-09389-x |
| cmu | Pulkit Grover | Guest Editorial for Special Issue on Coded Computing | IEEE Journal on Selected Areas in Information | editorial | 10.1109/jsait.2021.3108024 |
| epfl | Nikolas Geroliminis | Preface | Transportation Research Part C Emerging Techn | editorial | 10.1016/j.trc.2020.02.029 |
| epfl | Alcherio Martinoli | Guest editorial: Special issue on distributed robotics—from fundamentals to applications | Autonomous Robots | editorial | 10.1007/s10514-018-9803-9 |
| cmu | Abhinav Gupta | Editorial: Introduction to the Special Section on CVPR2019 Best Papers | IEEE Transactions on Pattern Analysis and Mac | editorial | 10.1109/tpami.2021.3080715 |

## `dissertation` (237)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| stanford | Sean Follmer | High-bandwidth electrostatic clutch arrays for high-resolution shape displays | Stanford Digital Repository | dissertation | 10.25740/dc344tb7744 |
| stanford | Dorsa Sadigh | Data-centric methods for training and adapting generalist robot policies | Stanford Digital Repository | dissertation | 10.25740/bc593xk6743 |
| stanford | Karen Liu | Learning for long-horizon humanoid autonomy | Stanford Digital Repository | dissertation | 10.25740/fr284bb0948 |
| stanford | David Lobell | Informing water and nutrient management for sustainable agriculture | Stanford Digital Repository | dissertation | 10.25740/np612sn4793 |
| stanford | Jiajun Wu | Toward generalizable and intelligent visual reasoning systems | Stanford Digital Repository | dissertation | 10.25740/yq194dx1901 |
| stanford | Jose H. Blanchet | On the first-passage times of branching random walks | Stanford Digital Repository | dissertation | 10.25740/vv508vp8750 |
| stanford | Vasilis Syrgkanis | Dynamic Local Average Treatment Effects | RePEc: Research Papers in Economics | preprint | 10.25740/zz954kz5769 |
| stanford | Andrea Montanari | High-dimensional asymptotics of empirical risk minimization beyond convexity, Gaussianity, | Stanford Digital Repository | dissertation | 10.25740/tj546hm6215 |
| stanford | Nicholas Bambos | Learning to control unknown multi-agent systems for guided distributed intelligence | Stanford Digital Repository | dissertation | 10.25740/dc159xb3475 |
| stanford | Marco Pavone | Deployment-time reliability of learned robot policies | Stanford Digital Repository | dissertation | 10.25740/cp016xz0883 |

## `software_record` (231)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| berkeley | Ian Holmes | Apollo 3 v1 | Zenodo (CERN European Organization for Nuclea | software | 10.5281/zenodo.20598247 |
| epfl | Alexander Mathis | amathislab/DeepDraw: Final project code for DeepDraw, Sandbrink, Mamidanna et al. eLife 20 | Zenodo (CERN European Organization for Nuclea | software | 10.5281/zenodo.23502908 |
| cmu | Victoria A. Webster-Wood | Repository for "Beyond cross-sectional area: Impacts of geometric scaling on the force res | Zenodo (CERN European Organization for Nuclea | software | 10.5281/zenodo.23249273 |
| epfl | Nate Foster | The Simulator's Blueprint: Automata Learning from System Event Logs | Zenodo (CERN European Organization for Nuclea | software | 10.5281/zenodo.19828944 |
| cmu | Jun-Yan Zhu | aaelmeli/PhysicsBasedFWI: UQFWI-VAE | Zenodo (CERN European Organization for Nuclea | software | 10.5281/zenodo.19411503 |
| cmu | Inseung Kang | Code and data for: Fall risk-aware adaptation explains suboptimal locomotor performance | Zenodo (CERN European Organization for Nuclea | software | 10.5281/zenodo.19547419 |
| mit | Ali Jadbabaie | Online Learning for Supervisory Switching Control (code) | Code Ocean | software | 10.24433/co.5030368.v1 |
| stanford | Kunle Olukotun | The Streaming Tensor Programs (STeP) Artifact | Figshare | software | 10.6084/m9.figshare.31095274 |
| epfl | Mathias Payer | Exploiting Android Apps with Counterfeit Art | Zenodo (CERN European Organization for Nuclea | software | 10.5281/zenodo.20076100 |
| stanford | Alex Aiken | Relight: Simple User-Level Checkpointing and Fast-Forward Replay for Distributed Task-Base | Zenodo (CERN European Organization for Nuclea | software | 10.5281/zenodo.21479557 |

## `meeting_abstract:journal` (220)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| stanford | Pamela Hinds | What Happened to My Office? The Role of Place Identity at Work | Academy of Management Proceedings | conference-abstract | 10.5465/ambpp.2016.11983abstract |
| mit | Henrik Schmidt | Robust neural network approach to source-range estimation in a simulated Arctic environmen | The Journal of the Acoustical Society of Amer | conference-abstract | 10.1121/1.5137274 |
| stanford | Andrea Goldsmith | F270. Regularized Linear Regression Guides Development of a Multilocus Genetic Profile Sco | Biological Psychiatry | conference-abstract | 10.1016/j.biopsych.2018.02.884 |
| mit | Henrik Schmidt | Real-time, model-aided ranging for small scale operations in the Beaufort Sea, an ice-cove | The Journal of the Acoustical Society of Amer | conference-abstract | 10.1121/10.0008285 |
| mit | Henrik Schmidt | The Virtual Ocean—A high-fidelity, physics-based testbed for distributed, autonomous under | The Journal of the Acoustical Society of Amer | conference-abstract | 10.1121/1.5014689 |
| mit | Henrik Schmidt | Estimation of the acoustic environment through machine learning techniques | The Journal of the Acoustical Society of Amer | conference-abstract | 10.1121/1.5067730 |
| stanford | Pamela Hinds | Fostering Equity and Inclusion in Distributed Work: New Directions in Hybrid & Remote Work | Academy of Management Proceedings | conference-abstract | 10.5465/amproc.2024.10524symposium |
| stanford | Jiajun Wu | MOTIVATING INFORMATION-SEEKING BEHAVIORS FOR NEW TECHNOLOGY ACROSS THE LIFE SPAN | Innovation in Aging | conference-abstract | 10.1093/geroni/igae098.2118 |
| princeton | Olga Troyanskaya | Proximal Tubular Epithelial Cell States in KPMP Protocol Kidney Biopsies Are Linked to Sho | Journal of the American Society of Nephrology | conference-abstract | 10.1681/asn.20223311s123c |
| mit | Neil Thompson | Sources of Innovation Revisited: Patterns in Firms’ Usage of Internal and External Search | Academy of Management Proceedings | conference-abstract | 10.5465/ambpp.2022.14221abstract |

## `meeting_abstract:single_author` (169)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| stanford | Jure Leskovec | Large-scale graph representation learning | IEEE International Conference on Big Data (Bi | conference-abstract | 10.1109/bigdata.2017.8257903 |
| princeton | Matthew Weinberg | Incentive Challenges in Designing Cryptocurrencies | ACM Conference on Economics and Computation ( | conference-abstract | 10.1145/3219166.3277551 |
| berkeley | Claire Tomlin | Safe Learning in Robotics |  | conference-abstract | 10.1145/3447548.3469648 |
| stanford | Chris Re | Is Data Management the Beating Heart of AI Systems? | ACM SIGMOD International Conference on Manage | conference-abstract | 10.1145/3514221.3523276 |
| stanford | Allison Okamura | Wearable haptic devices for ubiquitous communication |  | conference-abstract | 10.1117/12.2617849 |
| mit | Alan Edelman | A more open efficient future for AI development and data science with an introduction to J | IEEE International Conference on Big Data (Bi | conference-abstract | 10.1109/bigdata.2017.8257901 |
| mit | Pattie Maes | Benefiting from AI Without Losing Ourselves in the Process | ACM International Conference on Intelligent U | conference-abstract | 10.1145/3742414.3794764 |
| berkeley | David Wagner | Security and Machine Learning | ACM SIGSAC Conference on Computer and Communi | conference-abstract | 10.1145/3133956.3134108 |
| mit | Vivienne Sze | Efficient Computing for AI and Robotics | International Symposium on VLSI Design, Autom | conference-abstract | 10.1109/vlsi-dat49148.2020.9196291 |
| cmu | Leman Akoglu | Online Detection of Anomalous Heterogeneous Graphs with Streaming Edges | IEEE ... International Conference on Data Min | conference-abstract | 10.1109/icdmw.2017.133 |

## `repository_supplement` (87)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| epfl | Viktor Kuncak | Formal Autograding in a Classroom (Extended Version Artifact) |  | article | 10.5281/zenodo.17600207 |
| stanford | Barbara Elizabeth Engelhardt | Additional file 1 of Neighborhood nonnegative matrix factorization identifies patterns and | Figshare | article | 10.6084/m9.figshare.31311538 |
| cmu | Christian Kästner | Supplementary Materials for "Designing Abandabot: When Does Open Source Dependency Abandon |  | article | 10.5281/zenodo.16945363 |
| cmu | Laura Dabbish | Prosodic Synchrony Experiment set up PLoS One 2021 v1 |  | preprint | 10.17504/protocols.io.bqfamtie |
| stanford | Russ Altman | Additional file 2 of The Human Omnibus of Targetable Pockets | Figshare | article | 10.6084/m9.figshare.30947975 |
| epfl | Viktor Kuncak | Proactive Synthesis of Recursive Tree-to-String Functions from Examples (Artifact) | DROPS (Schloss Dagstuhl – Leibniz Center for  | article | 10.4230/darts.3.2.16 |
| mit | Ron Weiss | One-pot Optimization of Genetic Circuits using Poly-transfections v1 |  | preprint | 10.17504/protocols.io.k98cz9w |
| cmu | Richard Schuster Border | Additional file 1 of Leveraging tumor dynamics to discover mutations influencing progressi | Figshare | article | 10.6084/m9.figshare.33363981 |
| cmu | Bogdan Vasilescu | Data and code for paper "Scientific Open-Source Software Is Less Likely To Become Abandone |  | article | 10.5281/zenodo.15278784 |
| cmu | Dominik Moritz | Supplementary material for "Structured Visualization Design Knowledge for Grounding Genera |  | article | 10.5281/zenodo.19567051 |

## `machine_translation` (44)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| berkeley | Jitendra Malik | 物体再構成のためのカテゴリー特異的変形可能な3Dモデルの学習【Powered by NICT】 | IEEE Transactions on Pattern Analysis and Mac | article |  |
| berkeley | Vladimir Stojanovic | 45nm SOI CMOSによるリング共振器光DACに基づいた29.3A40Gb/s PAM‐4送信機【Powered by NICT】 | IEEE Conference Proceedings | conference-paper |  |
| mit | Anantha Chandrakasan | 14.4深部ニューラルネットワーク音響モデルと音声パワーゲーティングを用いたスケーラブル音声認識装置【Powered by NICT】 | IEEE Conference Proceedings | conference-paper |  |
| berkeley | Krste Asanović | 28nm FD‐SOIプロセッサSoCにおけるサブマイクロ秒適応電圧スケーリング【Powered by NICT】 | IEEE Conference Proceedings | conference-paper |  |
| stanford | Amin Arbabian | 1.55での12.5Gbit/s pJ/b/mを達成する三次元印刷した26DBIレンズアンテナを用いた17.8コンパクト130GHz完全包装したポイントツーポイント無線システム【P | IEEE Conference Proceedings | conference-paper |  |
| epfl | Andreas Peter Burg | 高速データ伝送のためのスライディングブロックViterbi検出器の設計考察【Powered by NICT】 | IEEE Conference Proceedings | conference-paper |  |
| stanford | Chris Re | 非同期性は運動量を生む,深い学習への応用【Powered by NICT】 | IEEE Conference Proceedings | conference-paper |  |
| berkeley | Claire Tomlin | スマートメータデータを用いた住宅負荷需要応答へのBayes法の適用【Powered by NICT】 | IEEE Conference Proceedings | conference-paper |  |
| epfl | Yusuf Leblebici | 損失ワイヤラインデータリンクのためのマルチtone/single側波帯シリアルリンクトランシーバのアーキテクチャモデリング【Powered by NICT】 | IEEE Conference Proceedings | conference-paper |  |
| cmu | José M. F. Moura | 制御目的によって制約されたサイバー物理攻撃【Powered by NICT】 | IEEE Conference Proceedings | conference-paper |  |

## `workshop_proposal` (41)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| princeton | Nick Feamster | Workshop on Tracking Quality of Experience in the Internet | ACM SIGCOMM Computer Communication Review | article | 10.1145/3041027.3041035 |
| mit | David Clark | Workshop on Internet Economics (WIE2018) Final Report | ACM SIGCOMM Computer Communication Review | article | 10.1145/3336937.3336941 |
| cmu | Hoda Heidari | Workshop on Developing Standards and Documentation For LLM Use as Simulated Research Parti | Extended Abstracts of the CHI Conference on H | conference-paper | 10.1145/3772363.3778756 |
| mit | David Clark | Workshop on Internet Economics (WIE-KISMET 2019) report | ACM Special Interest Group on Data Communicat | article |  |
| epfl | Pierre Dillenbourg | Workshop on Robots for Learning | ACM/IEEE International Conference on Human-Ro | conference-paper | 10.1145/3029798.3029801 |
| mit | David Clark | Workshop on Tracking Quality of Experience in the Internet | ACM SIGCOMM Computer Communication Review | article | 10.1145/3041027.3041035 |
| mit | Hiroshi Ishii | Living Bits and Radical Aminos: A Workshop on Bio-Digital Interfaces for Human-Computer In | Extended Abstracts of the CHI Conference on H | conference-paper | 10.1145/3544549.3573813 |
| cmu | Ken Koedinger | Advancing the Science of Teaching with Tutoring Data: A Collaborative Workshop with the Na | ACM Conference on Learning @ Scale (L@S) | conference-paper | 10.1145/3698205.3733961 |
| epfl | Daniel Kressner | 7th Workshop on Matrix Equations and Tensor Techniques | Numerical Linear Algebra with Applications | article | 10.1002/nla.2223 |
| mit | David Clark | Workshop on Internet Economics (WIE 2019) report | ACM SIGCOMM Computer Communication Review | article | 10.1145/3402413.3402421 |

## `erratum` (39)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| mit | Daniela Rus | Publisher Correction: Closed-form continuous-time neural networks | Nat. Mac. Intell. | article | 10.1038/s42256-022-00597-y |
| stanford | James Zou | Author Correction: Prostate cancer therapy personalization via multi-modal deep learning o | npj Digit. Medicine | article | 10.1038/s41746-023-00769-z |
| stanford | James Zou | Author Correction: Advances, challenges and opportunities in creating data for trustworthy | Nat. Mac. Intell. | article | 10.1038/s42256-022-00548-7 |
| stanford | Sanmi Koyejo | Publisher Correction: Increasing the presence of BIPOC researchers in computational scienc | Nat. Comput. Sci. | article | 10.1038/s43588-024-00710-8 |
| cmu | Eduard Hovy | Erratum: Measuring and Improving Consistency in Pretrained Language Models | Trans. Assoc. Comput. Linguistics | article | 10.1162/tacl_x_00455 |
| stanford | Mert Pilanci | Correction to: Sketching the Krylov subspace: faster computation of the entire ridge regul | J. Supercomput. | article | 10.1007/s11227-023-05476-w |
| stanford | Christos Kozyrakis | Corrigendum to "The IX Operating System: Combining Low Latency, High Throughput and Effici | ACM Trans. Comput. Syst. | article | 10.1145/3154292 |
| berkeley | Stuart J. Russell | Correction: AI content detection in the emerging information ecosystem: new obligations fo | Ethics Inf. Technol. | article | 10.1007/s10676-024-09808-z |
| stanford | Jacob Fox | Erratum: On Regularity Lemmas and their Algorithmic Applications | Comb. Probab. Comput. | article | 10.1017/s0963548318000111 |
| stanford | Fei-Fei Li | Author Correction: Advances, challenges and opportunities in creating data for trustworthy | Nat. Mac. Intell. | article | 10.1038/s42256-022-00548-7 |

## `dagstuhl_report` (38)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| cmu | Carolyn P Rose | BOTse: Bots in Software Engineering (Dagstuhl Seminar 19471) | DROPS (Schloss Dagstuhl – Leibniz Center for  | article | 10.4230/dagrep.9.11.84 |
| stanford | Diyi Yang | Natural Language Processing for Mental Health (Dagstuhl Seminar 25361) | TUbilio (Technical University of Darmstadt) | article | 10.4230/dagrep.15.8.62 |
| epfl | Haitham Al Hassanieh | Novel Scenarios for the Wireless Internet of Things (Dagstuhl Seminar 23222) | Dagstuhl Reports | article | 10.4230/dagrep.13.5.182 |
| epfl | Nisheeth Vishnoi | Evolution and Computing (Dagstuhl Seminar 16011) | Repository@Nottingham (University of Nottingh | article | 10.4230/dagrep.6.1.1 |
| cmu | Benjamin Moseley | Learned Predictions for Data Structures and Running Time (Dagstuhl Seminar 25181) | DROPS (Schloss Dagstuhl – Leibniz Center for  | article | 10.4230/dagrep.15.4.112 |
| cmu | Maria Balcan | Foundations of Unsupervised Learning (Dagstuhl Seminar 16382) | DROPS (Schloss Dagstuhl – Leibniz Center for  | article | 10.4230/dagrep.6.9.94 |
| cmu | Eunsuk Kang | Specification Engineering: Foundations for the Future of Software Development (Dagstuhl Se | DROPS (Schloss Dagstuhl – Leibniz Center for  | article | 10.4230/dagrep.15.9.160 |
| princeton | Kyle Jamieson | Novel Scenarios for the Wireless Internet of Things (Dagstuhl Seminar 23222) | Dagstuhl Reports | article | 10.4230/dagrep.13.5.182 |
| epfl | Mathias Payer | Secure Compilation (Dagstuhl Seminar 21481) | Dagstuhl Reports | article | 10.4230/dagrep.11.10.173 |
| mit | Ronitt Rubinfeld | From Big Data Theory to Big Data Practice (Dagstuhl Seminar 23071) | Dagstuhl Reports | article | 10.4230/dagrep.13.2.33 |

## `meeting_abstract:title` (31)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| mit | Hugh Herr | Abstract P25: A Caprine Model of a Novel Amputation Paradigm for Bi-directional Neural Con | Plastic & Reconstructive Surgery Global Open | conference-abstract | 10.1097/01.gox.0000516682.22242.0c |
| stanford | Peter Bailis | Abstract 16231: Machine Learning of Remodeled Ventricular Action Potentials and Long-Term  | Circulation | conference-abstract |  |
| stanford | Parag Mallick | Abstract A23: Characterization of diverging molecular and phenotypic responses under chang | Cancer Research | conference-abstract | 10.1158/1538-7445.tme16-a23 |
| stanford | Matei Zaharia | Abstract 16231: Machine Learning of Remodeled Ventricular Action Potentials and Long-Term  | Circulation | conference-abstract |  |
| cmu | Marcel Bruchez | Abstract B02: Complex molecular-scale dynamics of HER2 receptor transport in live SKBR3 br | Molecular Cancer Research | conference-abstract | 10.1158/1557-3125.advbc15-b02 |
| stanford | James Zou | Abstract 16339: Machine Learning Prediction of Left Ventricular Chamber Size and Ejection  | Circulation | conference-abstract |  |
| mit | Manolis Kellis | Abstract B25: Exosomal transcriptomic signatures tracks and predicts response to checkpoin | Cancer Immunology Research | conference-abstract | 10.1158/2326-6074.tumimm17-b25 |
| mit | Manolis Kellis | Abstract B034: Overcoming resistance to immunotherapy by targeting CD38 in human tumor exp | Cancer Research | conference-abstract | 10.1158/1538-7445.genfunc25-b034 |
| mit | Regina Barzilay | Abstract SP080: Hidden clues in the mammogram: How AI can improve early breast cancer dete | Cancer Research | conference-abstract | 10.1158/1538-7445.sabcs20-sp80 |
| stanford | Anshul Kundaje | Abstract 4349: Predicting gene expression from plasma cell-free DNA using both the fragmen | Molecular and Cellular Biology / Genetics | conference-abstract | 10.1158/1538-7445.sabcs18-4349 |

## `oberwolfach_report` (28)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| mit | Caroline Uhler | Algebraic Structures in Statistical Methodology | Oberwolfach Reports | article | 10.4171/owr/2022/55 |
| berkeley | Lin Lin | Mathematical Methods in Quantum Chemistry | Oberwolfach Reports | article | 10.4171/owr/2018/13 |
| cmu | Dejan Slepčev | Variational Methods for Evolution | Oberwolfach Reports | article | 10.4171/owr/2023/57 |
| stanford | Mary Wootters | New Mathematical Directions in Coding Theory | Oberwolfach Reports | article | 10.4171/owr/2025/41 |
| epfl | Ola Svensson | Combinatorial Optimization | Oberwolfach Reports | article | 10.4171/owr/2021/53 |
| epfl | Fabio Nobile | Uncertainty Quantification | Oberwolfach Reports | article | 10.4171/owr/2025/21 |
| cmu | Aaditya Ramdas | Game-theoretic Statistical Inference: Optional Sampling, Universal Inference, and Multiple | Oberwolfach Reports | article | 10.4171/owr/2024/24 |
| mit | Philippe Rigollet | Statistical and Computational Aspects of Learning with Complex Structure | Oberwolfach Reports | article | 10.4171/owr/2019/22 |
| berkeley | Peter Bartlett | Mathematical Foundations of Machine Learning | Oberwolfach Reports | article | 10.4171/owr/2021/15 |
| mit | Youssef Marzouk | Data Assimilation: From Mathematical and Statistical Foundations to Applications | Oberwolfach Reports | article | 10.4171/owr/2025/10 |

## `award_announcement` (16)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| mit | Bonnie Berger | 2017 ISCB Accomplishment by a Senior Scientist Award given to Pavel Pevzner | PLoS Computational Biology | article | 10.1371/journal.pcbi.1005561 |
| princeton | Margaret Martonosi | 2018 ACM SIGMOBILE Rockstar Award | GetMobile Mobile Computing and Communications | article | 10.1145/3276145.3276151 |
| stanford | Gordon Wetzstein | VGTC Virtual Reality Technical Achievement Award | IEEE Conference on Virtual Reality and 3D Use | conference-abstract | 10.1109/vr58804.2024.00017 |
| mit | Bonnie Berger | 2017 ISCB Accomplishment by a Senior Scientist Award: Pavel Pevzner | F1000Research | article | 10.12688/f1000research.11588.1 |
| princeton | Margaret Martonosi | 2016 Maurice Wilkes Award Given to Timothy Sherwood | IEEE Micro | article | 10.1109/mm.2017.24 |
| mit | Stefanie Mueller | SIGCHI Outstanding Dissertation Award | Extended Abstracts of the CHI Conference on H | conference-paper | 10.1145/3170427.3185063 |
| mit | Nancy Lynch | 2019 Principles of Distributed Computing Doctoral Dissertation Award | ACM Symposium on Principles of Distributed Co | conference-abstract | 10.1145/3293611.3341565 |
| mit | Bonnie Berger | 2017 ISCB Innovator Award: Aviv Regev | F1000Research | article | 10.12688/f1000research.11585.1 |
| cmu | Dominik Moritz | 2024 VGTC Visualization Significant New Researcher Award | IEEE Transactions on Visualization and Comput | article | 10.1109/tvcg.2024.3473335 |
| mit | Bonnie Berger | 2017 Outstanding Contributions to ISCB Award: Fran Lewitter | F1000Research | article | 10.12688/f1000research.11587.1 |

## `tribute` (8)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| mit | Patrick Winston | Marvin L. Minsky (1927–2016) | Nature | article | 10.1038/530282a |
| mit | Erik Demaine | Tribute to Godfried Toussaint. | Canadian Conference on Computational Geometry | conference-paper |  |
| mit | Alan Edelman | Tribute to Nick Higham | Foundations of Computational Mathematics | article | 10.1007/s10208-024-09680-9 |
| mit | Vincent Chan | In Memory of Charles Kao Kuen | Journal of Optical Communications and Network | article | 10.1364/jocn.10.000ed1 |
| cmu | Ignacio E. Grossmann | A tribute to professor Roger Sargent: Intellectual leader of process systems engineering | AIChE Journal | article | 10.1002/aic.15425 |
| mit | Joel Emer | Derek Chiou | IEEE Micro | article | 10.1109/mm.2025.3544666 |
| cmu | Ignacio E. Grossmann | A tribute to Roger Sargent | AIChE Journal | article | 10.1002/aic.15423 |
| cmu | James C. Hoe | Derek Chiou | IEEE Micro | article | 10.1109/mm.2025.3544666 |

## `highlights_column` (2)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| princeton | Ileana M. Cristea | Principles of Systems Biology, No. 31 | Cell Systems | article | 10.1016/j.cels.2018.08.005 |
| mit | Bonnie Berger | Principles of Systems Biology, No. 31 | Cell Systems | article | 10.1016/j.cels.2018.08.005 |

## `meeting_abstract:keynote` (2)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| stanford | Tim Roughgarden | Why prices need algorithms (invited talk) | ACM Symposium on Theory of Computing (STOC) | conference-abstract | 10.1145/3055399.3079077 |
| stanford | Subhasish Mitra | ASP-DAC 2017 keynote speech I: In memory of Edward J. McCluskey: The next wave of pioneeri | Asia and South Pacific Design Automation Conf | conference-abstract | 10.1109/aspdac.2017.7858250 |

## `doi_year_conflict` (1)

| school | PI | title | venue | type | DOI |
|---|---|---|---|---|---|
| stanford | Chris Manning | A Framework for Fostering Easier Access to Enriched Textual Information | DROPS (Schloss Dagstuhl – Leibniz Center for  | article | 10.4230/oasics.slate.2023.2 |
