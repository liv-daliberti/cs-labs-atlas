import sqlite3, zlib, re, sys
from cap import DB
def raw(url):
    c = sqlite3.connect(DB)
    r = c.execute("select raw from captures where url=? order by id desc limit 1", (url,)).fetchone()
    return zlib.decompress(r[0]).decode("utf-8", "replace") if r else None
if __name__ == "__main__":
    s = raw(sys.argv[1])
    for p in sys.argv[2:]:
        for m in re.finditer(p, s):
            print("...", s[max(0, m.start()-400): m.end()+400].replace("\n", " "), "...\n")
