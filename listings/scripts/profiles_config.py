"""Profile-page targets for gap PI-years (frozen in profile_targets_<school>.json by make_profile_targets.py)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def targets(school):
    p = os.path.join(HERE, f"profile_targets_{school}.json")
    return json.load(open(p)) if os.path.exists(p) else []
