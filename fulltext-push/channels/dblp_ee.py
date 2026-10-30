"""Channel dblp_ee: lab_channels.step_dblp_ee, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['dblp_ee']). What it does: documented in fulltext-push/dblp_ee.py"""
from channels import _legacy

NAME = 'dblp_ee'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
