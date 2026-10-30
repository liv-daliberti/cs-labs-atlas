"""Channel homepages: lab_channels.step_homepages, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['homepages']). What it does: (berkeley) Author- and lab-hosted PDFs: each PI's
own website (EECS directory 'website') and the websites of the units they lead (claude-berkeley-20261021
people/units.json), plus up to three pages those sites link as publications / papers; robots.txt honoured, one
request per 3 s. A missing lab paper of that PI gains the one PDF (or arXiv id -> bulk copy) of the bibliography
entry that carries its exact title."""
from channels import _legacy

NAME = 'homepages'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
