"""Channel dspace: lab_channels.step_dspace, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['dspace']). What it does: (mit) DSpace@MIT handles among the lab works' known
links -> the items' ORIGINAL PDFs through OAI-PMH ORE records (one request per 8 s; robots.txt leaves /server/oai
open) -> REST bitstream URLs (../../claude-mit-20261020/tools/mit_dspace_rest.py resolve + add, restricted to these
works). It writes its own candidates; the web front end (rate-limited) is never used."""
from channels import _legacy

NAME = 'dspace'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
