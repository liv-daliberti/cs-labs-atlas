"""R-PAP-32 (a reviewed blocked cluster) and R-STU-19 (student-link rules A and B), each on the real rows that failed the
2026-11-05 stage-9 samples (UChicago, Georgia Tech)."""
import json
from pathlib import Path

import pytest

from pihier import identity, links

CHEN = {'blockedClusters': [{'coauthors': ['Ben Y. Zhao', 'Haitao Zheng', 'Heather Zheng', 'Pedro Lopes'], 'min_coauthors': 2}]}


def work(*names):
    return {'authorships': [{'raw_author_name': n} for n in names]}


@pytest.mark.parametrize('byline', [
    ['Chen, Yuxin', 'Li, Huiying', 'Nagels, Steven', 'Li, Zhijing', 'Lopes, Pedro', 'Zhao, Ben Y.', 'Zheng, Haitao'],
    ['Yanzi Zhu', 'Zhujun Xiao', 'Yuxin Chen', 'Zhijing Li', 'Max Liu', 'Ben Y. Zhao', 'Heather Zheng'],
    ['Yuxin Chen', 'Huiying Li', 'Shan-Yuan Teng', 'Steven Nagels', 'Zhijing Li', 'Pedro Lopes', 'Ben Y. Zhao', 'Haitao Zheng'],
    ['Yuxin Chen', 'Zhuolin Yang', 'Ruben Abbou', 'Pedro Lopes', 'Ben Y. Zhao', 'Haitao Zheng']])
def test_R_PAP_32_the_security_namesake_is_blocked(byline):
    assert identity.in_blocked_cluster(CHEN, work(*byline))


def test_R_PAP_32_the_real_chen_and_other_pis_stay():
    assert not identity.in_blocked_cluster(CHEN, work('Yuxin Chen', 'Yuejie Chi', 'Ben Recht'))
    assert not identity.in_blocked_cluster(CHEN, work('Yuxin Chen', 'Ben Y. Zhao'))   # one coauthor is not a cluster
    assert not identity.in_blocked_cluster({}, work('Ben Y. Zhao', 'Haitao Zheng'))


def test_R_PAP_32_the_reviewed_override_carries_evidence():
    f = Path(__file__).resolve().parents[1] / 'hierarchy/uchicago/reviewed/census-overrides-school.json'
    c = json.loads(f.read_text())['Yuxin Chen']['blocked_clusters'][0]
    assert len(c['evidence']) == 6 and c['why'] and all(len(e['sha256']) == 64 for e in c['evidence'])


def test_R_STU_19_A_initials_only():
    assert links.initials_only('Y. Zhou') and links.initials_only('Zhou, Y. H.') and links.initials_only('B Zhou')
    assert not links.initials_only('Yuhao Zhou') and not links.initials_only('Zhou, Yuhao') and not links.initials_only('H. J. Terry Suh')
    assert not links.initials_only('Zhou')


def test_R_STU_19_A_hyper_authored_threshold():
    assert links.hyper_authored({'byline': ['x'] * 2938}) and links.hyper_authored({'byline': ['x'] * 50})
    assert not links.hyper_authored({'byline': ['x'] * 49}) and not links.hyper_authored({})


def student(roles, quote='x', role=None):
    return {'roles': roles, 'relations': [{'role': role or roles[0], 'sources': [{'quote': quote}]}]}


def test_R_STU_19_B_roles():
    assert links.student_role_ok(student(['phd'])) and links.student_role_ok(student(['phd_alumnus', 'phd_student']))
    assert links.student_role_ok(student(['student_or_alumnus'])) and links.student_role_ok(student(['masters']))
    assert not links.student_role_ok(student(['other']))        # Anderson (Batra's research scientist), Elola (Clifford's visitor)
    assert not links.student_role_ok(student(['postdoc'])) and not links.student_role_ok(student(['visiting']))
    assert not links.student_role_ok(student(['member']))


def test_R_STU_19_B_the_pi_is_among_the_advisers():
    q = 'Beste Basciftci Advisors: Shabbir Ahmed Nagi Gebraeel Operations Research Arden Baxter Advisor: Pinar Keskinocak Operations Research'
    s = student(['phd'], q)
    assert not links.pi_is_adviser(s, ['Pascal Van Hentenryck'])    # Basciftci's advisers are Ahmed and Gebraeel
    assert links.pi_is_adviser(s, ['Shabbir Ahmed'])
    assert links.pi_is_adviser(student(['phd'], 'Jane Doe, PhD student'), ['Pascal Van Hentenryck'])   # no adviser named: stays
