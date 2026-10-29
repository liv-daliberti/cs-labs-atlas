"""usage: get.py URL... : polite fetch of each URL into the store; prints status, length, error."""
import sys
sys.path.insert(0, '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/berkeley/cs-related-tools')
import mpcap
for u in sys.argv[1:]:
    try:
        r = mpcap.fetch(u)
        print(r.get('status'), len(r.get('text') or ''), r.get('error'), u, flush=True)
    except Exception as e:
        print('EXC', repr(e)[:200], u, flush=True)
