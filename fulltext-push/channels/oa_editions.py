"""Channel oa_editions: lab_channels.step_oa_editions, ported to the plugin interface through channels._legacy
(behaviour unchanged; scope lab_channels.SCOPE['oa_editions']). What it does: documented in fulltext-
push/oa_refresh.py"""
from channels import _legacy

NAME = 'oa_editions'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
