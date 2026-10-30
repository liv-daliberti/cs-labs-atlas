"""Channel pihomes: lab_channels.step_pihomes, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['pihomes']). What it does: documented in fulltext-push/labpage_channel.py"""
from channels import _legacy

NAME = 'pihomes'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
