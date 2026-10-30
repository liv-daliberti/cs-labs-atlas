"""Channel pubpages: lab_channels.step_pubpages, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['pubpages']). What it does: documented in fulltext-push/lab_channels.py (module
docstring)"""
from channels import _legacy

NAME = 'pubpages'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
