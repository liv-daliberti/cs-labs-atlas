"""2026-11-05: the unavailability ledger runs over every charter school (onboarding ones too); release 20261105c's ledger stage crashed with
KeyError 'uchicago' because the repository table and its link patterns covered only the released schools."""
import re

import school_config as C
import unavailable_ledger as U


def test_every_charter_school_has_a_repository_name_and_pattern():
    schools = set(C.released()) | set(C.onboarding()) if hasattr(C, 'released') else set(C.onboarding()) | {'princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan'}
    samples = {'uchicago': 'knowledge.uchicago.edu/record/1', 'gatech': 'repository.gatech.edu/entities/publication/x',
               'berkeley': 'escholarship.org/uc/item/1', 'michigan': 'deepblue.lib.umich.edu/handle/1', 'stanford': 'purl.stanford.edu/ab1'}
    for s in schools:
        # 2026-11-06: a school needs a repository name and pattern from the table OR its charter's [repository] (repo_name/repo_pattern fall back),
        # so an onboarding school needs no code edit; the four harvested schools are matched by their own harvest, not a link pattern
        assert U.repo_name(s) != 'the school repository', s
        if s in ('princeton', 'mit', 'cmu', 'epfl'):
            continue
        pat = re.compile(U.repo_pattern(s), re.I)
        if s in samples:
            assert pat.search('https://' + samples[s]), s
