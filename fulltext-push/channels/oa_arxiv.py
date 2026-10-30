"""Channel oa_arxiv: lab_channels.step_oa_arxiv, ported to the plugin interface through channels._legacy (behaviour
unchanged; scope lab_channels.SCOPE['oa_arxiv']). What it does: documented in fulltext-push/lab_channels.py (module
docstring)"""
from channels import _legacy

NAME = 'oa_arxiv'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
