# SJTU paper hold review, 2026-11-15

Four automatic `anchored_uncorroborated` holds said the paper was absent from the PI’s DBLP person record. Each is present there. The DBLP DOI equals the stored OpenAlex DOI, and the OpenAlex authorship names the PI at Shanghai Jiao Tong University. We remove only these four holds; the native identity, school, appointment and paper-type gates still decide admission.

Source replay: `hierarchy/sjtu/raw/dblp-dump-persons-school.json.gz` SHA-256 `5caa6ded64ee5cef6d915d3c2fbbefac2fd833a9102464b1500252a00b1c4284`; `hierarchy/sjtu/raw/pi-works.sqlite` work blobs are hashed below.

| PI | DBLP key | DOI | OpenAlex work | stored blob SHA-256 |
|---|---|---|---|---|
| 化存卿 | `conf/acsac/WangZGHH25` | `10.1109/acsac67867.2025.00050` | `W7131251348` | `7954674725d8c8e8a812bd3606738b16cc28f69d4d47fd07a2d596f2787df33e` |
| 李国强 | `journals/isci/HuFJXLCZYZ22` | `10.1016/j.ins.2022.05.045` | `W4280645289` | `fb61a24bf000cea8959abd8fa456f66b65bb29274079b213acd494bac88e5006` |
| 马利庄 | `journals/cvgip/JiangS0MTW20` | `10.1016/j.gmod.2020.101077` | `W3033649516` | `833fbe8dfe30e3790326a3dff71c313f97c44d21c4a0c77894aaaf6864b12218` |
| 涂仕奎 | `conf/ictai/YangT19` | `10.1109/ictai.2019.00087` | `W3006033959` | `df8a9db58e48d75e02ebdfa6be4ba6df0cb703b25b4090db8944ecdf14c3b42e` |

The four removed decision IDs: `sjtu-20261109-ol1-W3006033959-d355`, `sjtu-20261109-ol1-W3033649516-2111`, `sjtu-20261109-ol1-W4280645289-9248`, `sjtu-20261109-ol1-W7131251348-0fe8`.
