"""Channel oar: lab_channels.step_oar, ported to the plugin interface through channels._legacy (behaviour unchanged;
scope lab_channels.SCOPE['oar']). What it does: documented in fulltext-push/repo_index.py"""
from channels import _legacy

NAME = 'oar'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
