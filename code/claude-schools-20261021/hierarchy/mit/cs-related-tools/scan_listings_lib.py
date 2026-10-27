"""Name helpers shared by the MIT CS-related review tools."""
import re, unicodedata


def fold(s):
    return ''.join((unicodedata.normalize('NFKD', ch)[0] if unicodedata.normalize('NFKD', ch) else ch) for ch in s)


def natural(n):
    n = re.sub(r'\s+', ' ', n).strip()
    if n.count(',') == 1:
        a, b = [x.strip() for x in n.split(',')]
        if a and b and not re.match(r'^(Jr|Sr|II|III)\.?$', b):
            return f'{b} {a}'
    return n


