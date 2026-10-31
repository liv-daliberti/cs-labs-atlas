"""Every rule in docs/RULES.md has a test named after its id (ROADMAP item 8): R-PAP-17 -> test_R_PAP_17_<what>, R-LNK-02a ->
test_R_LNK_02a_<what>. A test may be an alias (tests/test_rule_aliases.py). A test name naming an id that RULES.md does not
have fails too, so that renamed or retired rules take their tests along."""
import ast
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
RULES = TESTS.parent / 'docs' / 'RULES.md'
TEST_ID = re.compile(r'^test_R_([A-Z]+)_(\d+[a-z]?)(?:_|$)')


def rule_ids():
    return re.findall(r'^### (R-[A-Z]+-\d+[a-z]?) ', RULES.read_text(), re.M)


def collected_test_names():
    """Every test function name in tests/*.py: defined, or imported under a test_ name."""
    out = {}
    for f in sorted(TESTS.glob('test_*.py')):
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                out.setdefault(node.name, f.name)
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    if (a.asname or a.name).startswith('test_'):
                        out.setdefault(a.asname or a.name, f.name)
    return out


def ids_tested():
    got = {}
    for name, f in collected_test_names().items():
        m = TEST_ID.match(name)
        if m:
            got.setdefault(f'R-{m.group(1)}-{m.group(2)}', []).append(f'{f}::{name}')
    return got


def test_rules_md_lists_rules():
    ids = rule_ids()
    assert len(ids) >= 60 and len(ids) == len(set(ids))


def test_every_rule_has_a_test():
    missing = [i for i in rule_ids() if i not in ids_tested()]
    assert not missing, f'rules in docs/RULES.md without a test named test_R_<..>_<..>: {missing}'


def test_every_rule_test_names_a_rule():
    stale = {i: t for i, t in ids_tested().items() if i not in set(rule_ids())}
    assert not stale, f'tests named after ids docs/RULES.md does not have: {stale}'
