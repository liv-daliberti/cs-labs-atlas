"""Channel wayback_acm: lab_channels.step_wayback_acm, ported to the plugin interface through channels._legacy
(behaviour unchanged; scope lab_channels.SCOPE['wayback_acm']). What it does: documented in fulltext-
push/lab_channels.py (module docstring)"""
from channels import _legacy

NAME = 'wayback_acm'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
