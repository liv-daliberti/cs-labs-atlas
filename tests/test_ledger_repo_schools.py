"""2026-11-05: the unavailability ledger runs over every charter school (onboarding ones too); release 20261105c's ledger stage crashed with
KeyError 'uchicago' because the repository table and its link patterns covered only the released schools."""
import re

import school_config as C
import unavailable_ledger as U


def test_every_charter_school_has_a_repository_name_and_pattern():
    schools = set(C.released()) | set(C.onboarding()) if hasattr(C, 'released') else set(C.onboarding()) | {'princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan'}
    for s in schools:
        assert s in U.REPO, s
        if s not in ('princeton', 'mit', 'cmu', 'epfl'):   # these four are matched by their own harvest, not a link pattern
            assert re.compile(U.REPO_PATTERN[s], re.I).search('https://' + {'uchicago': 'knowledge.uchicago.edu/record/1', 'gatech': 'repository.gatech.edu/entities/publication/x',
                                                                          'berkeley': 'escholarship.org/uc/item/1', 'michigan': 'deepblue.lib.umich.edu/handle/1',
                                                                          'stanford': 'purl.stanford.edu/ab1'}[s]), s
