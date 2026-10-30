"""Channel infoscience: lab_channels.step_infoscience, ported to the plugin interface through channels._legacy
(behaviour unchanged; scope lab_channels.SCOPE['infoscience']). What it does: (epfl) Infoscience handles among the
lab works' known links -> the REST API's ORIGINAL PDF files (../../claude-
epfl-20261019/tools/epfl_infoscience_rest.py resolve + add, restricted to these works; 3 s per request; an empty 202
/ 429 / 503 pauses it and is never worked around). It writes its own candidates."""
from channels import _legacy

NAME = 'infoscience'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
