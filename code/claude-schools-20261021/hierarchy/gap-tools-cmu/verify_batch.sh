#!/bin/sh
set -a; . /tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/openalex.env; set +a
cd /n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-cmu
PY="/usr/local/anaconda3/2024.02/bin/python -I"
v() { echo "######## $1 $2"; $PY verify_oa.py "$1" "$2" "$3" --show 6; }
v A5069656894 https://borderlab.org/publications Border
v A5134514127 https://borderlab.org/publications Border
v A5028325980 https://labs.bio.cmu.edu/bruchez-lab/publications/ Bruchez
v A5028841180 https://web.archive.org/web/20250116030510id_/https://compeau.cbd.cmu.edu:443/wp-content/uploads/2024/05/Compeau_CV.pdf Compeau
v A5048633127 https://engineering.cmu.edu/_files/documents/directory/gomes-cv.pdf Gomes
v A5023957810 https://engineering.cmu.edu/_files/documents/directory/gomes-cv.pdf Gomes
v A5049293538 https://labs.bio.cmu.edu/hinman/publications/ Hinman
v A5005587345 https://ichnow.ski/ Ichnowski
v A5075857263 https://steven.cs.illinois.edu/ Xia
v A5015501574 https://yunwilliamyu.net/content/static/curriculum-vitae.pdf Yu
v A5055884793 https://randiwilliams.com/files/RWilliams_CV.pdf Williams
v A5113677164 https://www.cs.cmu.edu/~sef/ Fahlman
