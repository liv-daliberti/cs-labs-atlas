import json, collections, re, sys
d = json.load(open('sweep_hits.json'))
RX = {'Tim Berners-Lee': r'Berners', 'Cheng Zhi (Anna) Huang': r'Anna|Cheng-?\s?Zhi|Chengzhi', 'Gerald Sussman': r'Gerald', 'Rodney Brooks': r'Rodney',
      'Zana Bucinca': r'Zana', 'Mitchell Gordon': r'Mitch', 'Christopher Terman': r'Terman', 'Alan Willsky': r'Willsky', 'Ted Adelson': r'Adelson',
      'Tom Leighton': r'Leighton', 'Albert R. Meyer': r'Albert', 'Michael Sipser': r'Sipser', 'Steve Ward': r'Steve|Stephen', 'Arvind': r'Arvind',
      'Judy Brewer': r'Jud', 'Michael Goemans': r'Goemans', 'Jeffrey Jaffe': r'Jeff', 'Bill Long': r'Bill|William', 'F. J. Corbato': r'Corbat'}
only = sys.argv[1:]
for pi, rows in d.items():
    if only and pi not in only:
        continue
    rows = [r for r in rows if re.search(RX.get(pi, '.'), r['raw'], re.I)]
    print('=====', pi, 'all', len(rows), 'mit', sum(r['mit'] for r in rows), collections.Counter(r['author'] for r in rows).most_common(8))
    for r in rows[:60]:
        print('  ', r['year'], 'MIT' if r['mit'] else '---', r['author'], (r['orcid'] or '')[-19:], '|', r['raw'], '|', r['title'][:70], '|', (r['affs'] or [''])[0][:60], '|', r['work'][21:])
