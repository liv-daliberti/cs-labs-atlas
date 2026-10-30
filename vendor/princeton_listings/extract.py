# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-listings-20261022/scripts/extract.py (sha256 fbf80692e875cbca71850a034fceab8864e418728c05cf3696a04087cfb4737c); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""HTML -> ordered text blocks (stdlib only).

Each block is [kind, text] where kind is 'h1'..'h6' for headings and 'b' otherwise.
The capture's stored text is '\n'.join(block texts); the verification text is that
string with all whitespace runs collapsed to one space.
"""
import html.parser
import re

BLOCK = {"p", "div", "li", "ul", "ol", "dl", "dt", "dd", "tr", "td", "th", "table", "tbody", "thead",
         "section", "article", "header", "footer", "nav", "aside", "main", "br", "hr", "form",
         "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "figure", "figcaption", "address",
         "option", "select", "button", "label", "fieldset", "legend", "caption", "center", "pre"}
SKIP = {"script", "style", "noscript", "svg", "template", "head", "iframe", "object", "title"}
HEAD = {"h1", "h2", "h3", "h4", "h5", "h6"}
VOID = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}


class P(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.buf = []
        self.skip = 0
        self.skipstack = []
        self.hstack = []

    def flush(self):
        t = " ".join("".join(self.buf).split())
        self.buf = []
        if t:
            kind = self.hstack[-1] if self.hstack else "b"
            self.blocks.append([kind, t])

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in SKIP:
            if tag not in VOID:
                self.skip += 1
                self.skipstack.append(tag)
            return
        if self.skip:
            return
        if tag in BLOCK:
            self.flush()
        if tag in HEAD:
            self.hstack.append(tag)
        if tag == "img":
            pass

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self.skip:
            return
        if tag in BLOCK:
            self.flush()

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip:
            if tag in SKIP and self.skipstack and tag == self.skipstack[-1]:
                self.skipstack.pop()
                self.skip -= 1
            elif tag in SKIP and tag in self.skipstack:
                while self.skipstack:
                    t = self.skipstack.pop()
                    self.skip -= 1
                    if t == tag:
                        break
            return
        if tag in BLOCK:
            self.flush()
        if tag in HEAD:
            if tag in self.hstack:
                while self.hstack:
                    if self.hstack.pop() == tag:
                        break

    def handle_data(self, data):
        if self.skip:
            return
        self.buf.append(data)


def decode(raw, content_type=None):
    cs = None
    if content_type:
        m = re.search(r"charset=([\w-]+)", content_type, re.I)
        if m:
            cs = m.group(1)
    if not cs:
        m = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", raw[:4000], re.I)
        if m:
            cs = m.group(1).decode("ascii", "replace")
    for c in ([cs] if cs else []) + ["utf-8"]:
        try:
            return raw.decode(c)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


def payload(raw):
    """id_ captures keep the origin's Content-Encoding; undo gzip/deflate."""
    import gzip
    import zlib as _z
    if raw[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(raw)
        except Exception:
            try:
                return _z.decompressobj(16 + _z.MAX_WBITS).decompress(raw)
            except Exception:
                return raw
    return raw


def blocks(raw, content_type=None):
    s = decode(payload(raw), content_type)
    p = P()
    try:
        p.feed(s)
        p.close()
    except Exception:
        pass
    p.flush()
    return p.blocks


def collapse(s):
    return " ".join(s.split())
