"""Channel core: lab_channels.step_core, ported to the plugin interface through channels._legacy (behaviour unchanged;
scope lab_channels.SCOPE['core']). What it does: documented in fulltext-push/lab_channels.py (module docstring)"""
from channels import _legacy

NAME = 'core'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
