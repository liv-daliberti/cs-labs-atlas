"""Channel s2_title: lab_channels.step_s2_title, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['s2_title']). What it does: documented in fulltext-push/s2_title.py"""
from channels import _legacy

NAME = 's2_title'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
