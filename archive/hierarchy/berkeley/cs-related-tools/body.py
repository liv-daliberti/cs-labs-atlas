"""usage: body.py URL NEEDLE [n]: the stored page text from the first NEEDLE occurrence after the site navigation."""
import sys, mpcap
t = mpcap.cached(sys.argv[1])['text']; n = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
idx = [i for i in range(len(t)) if t.startswith(sys.argv[2], i)]
start = next((i for i in idx if i > 1200), idx[0] if idx else 0)
print('##', sys.argv[1]); print(t[max(0, start-100):start+n]); print()
