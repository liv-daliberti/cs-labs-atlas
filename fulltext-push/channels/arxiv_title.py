"""Channel arxiv_title: lab_channels.step_arxiv_title, ported to the plugin interface through channels._legacy
(behaviour unchanged; scope lab_channels.SCOPE['arxiv_title']). What it does: documented in fulltext-
push/lab_channels.py (module docstring)"""
from channels import _legacy

NAME = 'arxiv_title'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
