"""Bridge the Ha Rim/Eugenia Rho name join with dated VT appointment evidence."""

import json
import zlib

import atlas_paths as P
import school_web as W
from bs4 import BeautifulSoup


def main():
    census = json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']
    person = next(x for x in census if x['name'] == 'Eugenia Rho')
    assert 'Ha Rim Rho' in person['aliases']
    source_by_year = {int(x['observed'][:4]): x for x in person['sources']}
    assert all(year in source_by_year for year in (2022, 2023, 2025))
    url = 'https://news.vt.edu/articles/2024/05/eng-cs-tracing-infectious-pandemic-language.html'
    r = W.con('vt').execute('select status,sha256,raw_zlib from live where url=?', (url,)).fetchone()
    assert r and r[0] == 200
    text = ' '.join(BeautifulSoup(zlib.decompress(r[2]), 'html.parser').stripped_strings)
    assert 'Eugenia Rho' in text and 'assistant professor in the Department of Computer Science' in text
    evidence = [dict(url=source_by_year[year]['url'], sha256=source_by_year[year]['sha256'],
                     quote=source_by_year[year]['quote'], observed=str(year), kind='dept_listing')
                for year in (2022, 2023)]
    evidence.append(dict(url=url, sha256=r[1], observed='2024-05-11', kind='university_news',
                         quote='Eugenia Rho, assistant professor in the Department of Computer Science'))
    evidence.append(dict(url=source_by_year[2025]['url'], sha256=source_by_year[2025]['sha256'],
                         quote=source_by_year[2025]['quote'], observed='2025-10-02',
                         kind='dept_listing'))
    path = P.data('census-overrides-school.json', 'vt')
    data = json.loads(path.read_text())
    item = data.setdefault('Eugenia Rho', {})
    item['periods'] = [dict(id='vt_eugenia_rho_reviewed_2022_2025',
                            start='2022', end='2025', asof='2025-10-02',
                            datePrecision='year', evidence=evidence,
                            note=('One first-party name join joins Ha Rim Rho and Eugenia Rho. '
                                  'VT professor-rank evidence occurs in each year 2022–2025. '
                                  'The end is the last observed VT year, not a claimed exact departure date.'))]
    item['why_periods'] = 'Official VT CS catalogs, a dated 2024 VT news article, and the 2025 archived CS directory support each year 2022–2025.'
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print('recorded Eugenia/Ha Rim Rho 2022–2025 VT period')


if __name__ == '__main__':
    main()
