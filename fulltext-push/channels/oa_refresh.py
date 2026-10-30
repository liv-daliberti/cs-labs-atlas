"""Channel oa_refresh: lab_channels.step_oa_refresh, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['oa_refresh']). What it does: documented in fulltext-push/oa_refresh.py"""
from channels import _legacy

NAME = 'oa_refresh'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
