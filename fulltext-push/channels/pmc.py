"""Channel pmc: lab_channels.step_pmc, ported to the plugin interface through channels._legacy (behaviour unchanged;
scope lab_channels.SCOPE['pmc']). What it does: documented in fulltext-push/lab_channels.py (module docstring)"""
from channels import _legacy

NAME = 'pmc'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
