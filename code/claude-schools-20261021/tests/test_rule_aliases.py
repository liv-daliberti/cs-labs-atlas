"""Rule-id names for tests that live in files other agents own (tests/test_rule_coverage.py checks that every rule in
docs/RULES.md has a test named after it). Each alias runs the original test under the rule's name."""
from test_unavailable_ledger import test_gate_fails_on_a_missing_entry as test_R_AUD_10_missing_ledger_entry_fails_the_gate  # noqa: F401
from test_unavailable_ledger import test_gate_fails_on_a_stale_entry as test_R_AUD_10_stale_ledger_entry_fails_the_gate  # noqa: F401
