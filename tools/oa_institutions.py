"""Stage 0 id verification from the OpenAlex snapshot's institutions table (all 143k institutions, no API credits).

  oa_institutions.py search <text> [--country US]    institutions whose name contains the text (case-insensitive): id, name, ROR, type, lineage
  oa_institutions.py lineage <id|key>                the institution, its parent lineage, every institution whose lineage holds it (children), and its
                                                     associated institutions with their relationship (related | child | parent): what the charter's
                                                     `openalex`, `openalex_related` and `openalex_excluded` are decided from
Never prints more than 60 rows. ROR ids are verified separately (api.ror.org/v2/organizations/<id>).
"""
import argparse, json, sys

import oa_snapshot as O


def rows(root=None):
    db, _ = O.conn(root)
    for i, name, ror, body in db.execute('select id, name, ror, body from institutions'):
        yield i, name, ror, O.unpack(body)


def short_lineage(b):
    return [O.short(x) for x in b.get('lineage') or []]


def search(text, country=None, root=None):
    t = text.lower()
    return [(O.short(i), n, r, b.get('type'), b.get('country_code'), short_lineage(b)) for i, n, r, b in rows(root)
            if t in (n or '').lower() and (not country or b.get('country_code') == country)]


def lineage(iid, root=None):
    import school_config as SC
    if iid in SC.keys():
        iid = SC.inst(iid)
    iid = O.short(iid)
    me, kids = None, []
    for i, n, r, b in rows(root):
        if O.short(i) == iid:
            me = (iid, n, r, b)
        elif iid in short_lineage(b):
            kids.append((O.short(i), n, b.get('type')))
    return me, kids


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('search'); s.add_argument('text'); s.add_argument('--country')
    g = sub.add_parser('lineage'); g.add_argument('id')
    a = ap.parse_args(argv)
    if a.cmd == 'search':
        for r in search(a.text, a.country)[:60]:
            print(json.dumps(r, ensure_ascii=False))
        return 0
    me, kids = lineage(a.id)
    if not me:
        sys.exit(f'{a.id}: not in the snapshot')
    i, n, r, b = me
    print(json.dumps(dict(id=i, name=n, ror=r, type=b.get('type'), lineage=short_lineage(b)), ensure_ascii=False))
    for x in b.get('associated_institutions') or []:
        print('  associated', O.short(x.get('id')), x.get('display_name'), x.get('relationship'))
    for k in kids[:60]:
        print('  in lineage ', *k)
    if len(kids) > 60:
        print(f'  ... {len(kids) - 60} more')
    return 0


if __name__ == '__main__':
    sys.exit(main())
