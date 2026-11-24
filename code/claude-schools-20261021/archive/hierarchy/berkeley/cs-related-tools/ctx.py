"""usage: ctx.py URL-LIKE REGEX [width]: contexts of REGEX in stored pages matching URL-LIKE."""
import sys, re, mpcap
w = int(sys.argv[3]) if len(sys.argv) > 3 else 120
con = mpcap.connect()
for url, text in con.execute('select url, text from captures where status=200 and error is null and url like ? order by id', (sys.argv[1],)).fetchall():
    hits = [text[max(0, m.start()-w):m.end()+w] for m in re.finditer(sys.argv[2], text)]
    print('##', url, len(text)); [print('   ', h) for h in hits[:6]]
