"""Harvest DataSpace OAI-PMH sets (ListRecords, metadataPrefix=dim) for the Princeton few-students PIs. Resumable: pages
already stored (here, in the main store, or in the sister gap store) are not fetched again.
usage: FSCAP_LOCAL=<scratch sqlite> harvest_princeton.py SET [SET ...]"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fsev  # noqa: E402

for st in sys.argv[1:]:
    n = 0
    for url, r, t in fsev.oai_pages({"verb": "ListRecords", "metadataPrefix": "dim", "set": st}):
        n += len(re.findall(r"<record>", t))
    print("DONE", st, n, flush=True)
print("ALLDONE", flush=True)
