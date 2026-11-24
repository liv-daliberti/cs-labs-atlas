"""Run tools/oa_identity_school.py for a school in its overlay and keep ONLY the missed-labs additions' override entries, in the school-local file
hierarchy/<school>/reviewed/census-overrides-school.json (never the tracked shared census-overrides.json: the shared file is restored).
usage: missed_labs_overrides.py <school>   (run with CS_ATLAS_CODE=<overlay>)
"""
import json, subprocess, sys
from pathlib import Path

W = Path(__file__).resolve().parents[1]


def main(school):
    shared = W / 'hierarchy/reviewed/census-overrides.json'
    before = json.loads(shared.read_text()).get(school) or {}
    subprocess.run([sys.executable, str(W / 'tools/oa_identity_school.py'), school], check=True)
    after = json.loads(shared.read_text()).get(school) or {}
    subprocess.run(['git', '-C', str(W), 'checkout', '--', 'hierarchy/reviewed/census-overrides.json'], check=True)
    loc = W / f'hierarchy/{school}/reviewed/census-overrides-school.json'
    cur = json.loads(loc.read_text()) if loc.exists() else {}
    new = [r['name'] for r in json.loads((W / f'hierarchy/{school}/reviewed/census-additions.json').read_text()) if r.get('added') == 'missed_labs_20261109']
    # the tool writes either file: collect from whichever changed
    after_local = json.loads(loc.read_text()) if loc.exists() else {}
    got = 0
    for n in new:
        e = after.get(n) or after_local.get(n)
        if e and (n not in before):
            cur[n] = {**(cur.get(n) or {}), **e}; got += 1
    loc.write_text(json.dumps(cur, indent=1, ensure_ascii=False) + '\n')
    print(school, 'override entries for new PIs', got, 'of', len(new))


if __name__ == '__main__':
    main(sys.argv[1])
