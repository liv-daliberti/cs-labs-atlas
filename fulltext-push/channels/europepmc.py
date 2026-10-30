"""Channel europepmc: lab_channels.step_europepmc, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['europepmc']). What it does: Europe PMC's REST search (25 DOIs per query, one
query per 10 s as its robots.txt asks; cached in the CMU stage's raw/europepmc.jsonl) for the lab papers' DOIs: a
hit with a PMCID -> its files in NLM's PMC open-data dataset on S3 (PDF before JATS XML), through ../../claude-
cmu-20261017/tools/europepmc_lookup.py search / files."""
from channels import _legacy

NAME = 'europepmc'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
