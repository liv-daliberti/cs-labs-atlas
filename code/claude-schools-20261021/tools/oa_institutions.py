"""Stage 0 id verification from the OpenAlex snapshot's institutions table (all 143k institutions, no API credits).

  oa_institutions.py search <text> [--country US] [--type education]
                                                     institutions whose name contains the text (case-insensitive), names starting with it first: id, name, ROR, type, lineage
  oa_institutions.py children-counts <id|key>        works 2016-2026 per lineage child, and how many lack the school's own id (decide `openalex_excluded` from it)
  oa_institutions.py lineage <id|key>                the institution, its parent lineage, every institution whose lineage holds it (children), and its
                                                     associated institutions with their relationship (related | child | parent): what the charter's
                                                     `openalex`, `openalex_related` and `openalex_excluded` are decided from
Never prints more than 60 rows. Run it as `atlas run tools/oa_institutions.py ...` (not `python -I`: it imports its siblings; it handles no downloads). ROR ids are verified separately (api.ror.org/v2/organizations/<id>).
"""
import argparse, json, sys

import oa_snapshot as O


def rows(root=None):
    db, _ = O.conn(root)
    for i, name, ror, body in db.execute('select id, name, ror, body from institutions'):
        yield i, name, ror, O.unpack(body)


def short_lineage(b):
    return [O.short(x) for x in b.get('lineage') or []]


def search(text, country=None, root=None, type_=None):
    """Name hits, best first: names that start with the text, then shorter names (a bare 'georgia' has 100+ hits, the school is not first in
    snapshot order)."""
    t = text.lower()
    hits = [(O.short(i), n, r, b.get('type'), b.get('country_code'), short_lineage(b)) for i, n, r, b in rows(root)
            if t in (n or '').lower() and (not country or b.get('country_code') == country) and (not type_ or b.get('type') == type_)]
    return sorted(hits, key=lambda h: (not (h[1] or '').lower().startswith(t), len(h[1] or ''), h[1] or ''))


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


def children_counts(iid, root=None, years=(2016, 2026)):
    """{id: (name, works, works without the school's own id)} for the school and each lineage child, over the stored works of the window
    (main store, then extensions). One pass over the works: the evidence for 'which children to keep' (openalex_excluded)."""
    import school_config as SC
    if iid in SC.keys():
        iid = SC.inst(iid)
    iid = O.short(iid)
    me, kids = lineage(iid, root)
    names = {iid: me[1]} if me else {iid: iid}
    names.update({k[0]: k[1] for k in kids})
    n = dict.fromkeys(names, 0)
    alone = dict.fromkeys(names, 0)
    seen = set()
    for db, _ in [O.conn(root)] + O.exts(root):
        for wid, body in db.execute('select w.id, w.body from work_inst i join works w on w.id = i.work_id where i.inst = ? and w.year between ? and ?', (iid,) + tuple(years)):
            if wid in seen:
                continue
            seen.add(wid)
            w = O.unpack(body)
            ids = {O.short(i.get('id')) for a in w.get('authorships') or [] for i in a.get('institutions') or []}
            for k in names:
                if k in ids:
                    n[k] += 1
                    if k != iid and iid not in ids:
                        alone[k] += 1
    return {k: (names[k], n[k], alone[k]) for k in names}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('search'); s.add_argument('text'); s.add_argument('--country'); s.add_argument('--type', dest='type_', help='institution type: education, facility, healthcare, ...')
    g = sub.add_parser('lineage'); g.add_argument('id')
    c = sub.add_parser('children-counts', help='works per lineage child, and those lacking the school\'s own id'); c.add_argument('id')
    a = ap.parse_args(argv)
    if a.cmd == 'search':
        hits = search(a.text, a.country, type_=a.type_)
        for r in hits[:60]:
            print(json.dumps(r, ensure_ascii=False))
        if len(hits) > 60:
            print(f'... {len(hits) - 60} more (add --country, --type or a longer text)')
        return 0
    if a.cmd == 'children-counts':
        for k, (nm, n, alone) in children_counts(a.id).items():
            print(f'{k:<14} {n:>8} works  {alone:>7} without the school id  {nm}')
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
