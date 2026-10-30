"""Channel figshare: lab_channels.step_figshare, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['figshare']). What it does: documented in fulltext-push/lab_channels.py (module
docstring)"""
from channels import _legacy

NAME = 'figshare'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
