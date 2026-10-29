#!/bin/sh
# After run_dblp_recover.sh: retry EPFL and MIT papers that found no route before the proceedings-PDF rules existed, then Princeton.
cd "$(dirname "$0")/.."
while pgrep -f "run_dblp_recover.sh epfl" > /dev/null; do sleep 60; done
for s in epfl mit; do /usr/local/anaconda3/2024.02/bin/python -c "
import sqlite3; c=sqlite3.connect('hierarchy/$s/dblp-recover.sqlite'); c.execute(\"delete from tries where step='none'\"); c.commit()"; done
sh hierarchy/run_dblp_recover.sh epfl mit princeton
