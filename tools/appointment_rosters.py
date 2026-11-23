"""Parse dated academic appointment tables; retain no financial fields.

Inputs are pdftotext -layout output from the official Illinois Gray Books.
Rows establish only their printed observation year, never an appointment span.
Campus, college and unit boundaries are required on every personnel page.
"""
import datetime
import re


def illinois_graybook(text, campus='Urbana-Champaign'):
    rows = []
    for page_number, page in enumerate(text.split('\f'), 1):
        if ('Employee Name' not in page or 'Job Title' not in page
                or 'UIUC Non-Tenure Faculty NTFC Agreement' in page):
            continue
        scope = re.search(r'September,\s+(\d{4})\s+-\s+\(([^)]+)\)', page)
        stamp = re.search(r'^([A-Z][a-z]+ \d{1,2}, \d{4})\s+Board of Trustees', page, re.M)
        if not scope or not stamp:
            raise ValueError(f'Personnel page {page_number} lacks date/campus')
        if scope[2] not in (campus + ' Campus', campus + ' University'):
            continue
        date = datetime.datetime.strptime(stamp[1], '%B %d, %Y').date()
        if date.year != int(scope[1]):
            raise ValueError(f'Inconsistent roster year on page {page_number}')
        college = unit = name = None
        for line in page.splitlines():
            heading = re.fullmatch(r'\s*([A-Z]{2}|\d{3}) - (.+?)\s*', line)
            if heading:
                if heading[1].isalpha():
                    college = heading[0].strip()
                    unit = None
                else:
                    unit = heading[0].strip()
                name = None
                continue
            # Stop before numerical columns; neither salaries nor FTEs enter a row.
            employment = re.search(r'\s{2,}([ABP][A-Z])\s+\d+\.\d+\s+\d+\.\d+', line)
            if not employment:
                continue
            if not college or not unit:
                raise ValueError(f'Personnel row outside unit on page {page_number}')
            left = line[:employment.start()].rstrip()
            tenure = re.search(r'\s{2,}([AMNPQTW])$', left)
            if tenure:
                left = left[:tenure.start()].rstrip()
            if line.startswith(' '):
                title = left.strip()
                if not name:
                    raise ValueError(f'Orphan continuation on page {page_number}')
                quote = title
            else:
                fields = re.split(r'\s{2,}', left)
                if len(fields) < 2:
                    raise ValueError(f'Ambiguous name/title columns on page {page_number}: {left}')
                name, title = fields[0], ' '.join(fields[1:])
                quote = ' '.join(left.split())
            rows.append(dict(name=name, title=title, tenure=tenure[1] if tenure else '',
                             employee_class=employment[1], campus=campus,
                             college=college, unit=unit, year=date.year,
                             document_date=date.isoformat(), date_quote=stamp[1],
                             page=page_number, quote=quote))
    if not rows:
        raise ValueError('No personnel rows for the requested campus')
    return rows


def regular_professor(title):
    """Conservative role test; special appointments need separate PI evidence."""
    upper = title.upper()
    return bool(re.search(r'\bPROF(?:ESSOR)?\b', upper) and not re.search(
        r'\b(?:EMER\w*|RES(?:EARCH)?|TCH\w*|TEACH\w*|ADJ\w*|VIS\w*|VST|CLIN\w*|AFFIL\w*|PRACTICE)\b', upper))
