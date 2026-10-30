"""Channel proceedings: lab_channels.step_proceedings, ported to the plugin interface through channels._legacy
(behaviour unchanged; scope lab_channels.SCOPE['proceedings']). What it does: Open proceedings (the Princeton
sweep's index of NeurIPS, PMLR, ICLR, CVF, ACL Anthology, IJCAI, USENIX, JMLR, PVLDB, ECCC, RSS, ...: claude-
princeton-20261015/cs-structure/raw/proceedings/index.json.gz): an entry whose normalized title equals the paper's
(>= 20 characters) and whose year is within 2 -> its PDF on the open host."""
from channels import _legacy

NAME = 'proceedings'
APPLIES = _legacy.applies(NAME)


def discover(school, papers, ctx):
    return _legacy.discover(NAME, school, papers, ctx)
