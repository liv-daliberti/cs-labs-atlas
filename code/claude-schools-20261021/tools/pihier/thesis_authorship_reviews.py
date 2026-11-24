"""Exact-work authorship from the same author-owned ORCID in two original sources."""
import datetime
import hashlib
import json
import re

from bs4 import BeautifulSoup


def orcid(value):
    m = re.fullmatch(r'https?://orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', value or '')
    return m[1] if m else None


def forward(name):
    parts = name.split(',')
    return ' '.join(reversed([x.strip() for x in parts])) if len(parts) == 2 else name


def fields(soup, label):
    out=[]
    for h in soup.find_all(['h2','h3']):
        if h.get_text(' ',strip=True)==label:
            wrapper=h.find_parent('div',class_='simple-view-element')
            if wrapper is not None:out.append(wrapper)
    return out


def annotation_author(raw, pdf, expected):
    """A real author badge immediately follows exactly one complete header name."""
    import pymupdf
    from . import student_authorship_reviews as V
    try:
        with pymupdf.open(stream=raw,filetype='pdf') as doc:
            page=doc[pdf.get('article_page',1)-1];words=page.get_text('words');spans=[]
            abstracts=[w[1] for w in words if V.norm(w[4])=='abstract']
            bottom=min(abstracts,default=page.rect.height*.45)
            for name in pdf['authors']:
                found=[]
                for top in sorted({w[1] for w in words if w[1]<bottom}):
                    row=sorted([w for w in words if abs(w[1]-top)<3],key=lambda w:w[0])
                    for a in range(len(row)):
                        for b in range(a+1,min(a+8,len(row))+1):
                            literal=V.norm(' '.join(w[4] for w in row[a:b])).rstrip('*∗†‡,')
                            literal=re.sub(r'\d+(?:\s*,\s*\d+)*$','',literal).rstrip('*∗†‡,')
                            if literal==V.norm(name):
                                box=(row[a][0],min(w[1] for w in row[a:b]),row[b-1][2],max(w[3] for w in row[a:b]))
                                if box not in found:found.append(box)
                if len(found)!=1:return False
                spans.append(found[0])
            selected=[]
            for link in page.get_links():
                if orcid(link.get('uri'))!=expected:continue
                rect=link['from'];owners=[]
                if pdf.get('orcid_mapping','adjacent_badge')=='whole_author_name':
                    i=pdf['author_index'];name=pymupdf.Rect(spans[i])
                    if (any(abs(a-b)>2 for a,b in zip(rect,name))
                            or any(rect.intersects(pymupdf.Rect(box)) for j,box in enumerate(spans) if j!=i)):
                        return False
                    selected.append(i)
                    continue
                if not (0<rect.width<=18 and 0<rect.height<=18):return False
                for i,(x0,y0,x1,y1) in enumerate(spans):
                    if max(y0,rect.y0)<min(y1,rect.y1) and -1<=rect.x0-x1<=16:
                        owners.append((rect.x0-x1,i))
                if not owners:return False
                owners.sort()
                if len(owners)>1 and abs(owners[0][0]-owners[1][0])<1:return False
                owner=owners[0][1]
                if any(rect.intersects(pymupdf.Rect(box)) for j,box in enumerate(spans) if j!=owner):return False
                selected.append(owner)
            return bool(selected) and set(selected)=={pdf['author_index']}
    except (RuntimeError,ValueError,IndexError,KeyError):
        return False


def printed_name(member, printed, kind):
    from . import student_authorship_reviews as V
    if kind!='given_initials':return V.name_variant_ok(member,printed,kind)
    a=re.findall(r'[^\W_]+',V.norm(member));b=re.findall(r'[^\W_]+',V.norm(printed))
    return (len(a)==len(b) and len(a)>=2 and a[-1]==b[-1] and len(a[-1])>1
            and any(len(x)==1 for x in b[:-1])
            and all(x==y or len(y)==1 and x.startswith(y) for x,y in zip(a[:-1],b[:-1])))


def numbered_blocks(raw, pdf):
    """Replay complete numbered definition rows in the actual author header column."""
    import pymupdf
    from . import student_authorship_reviews as V
    try:
        with pymupdf.open(stream=raw,filetype='pdf') as doc:
            page=doc[pdf.get('article_page',1)-1];words=page.get_text('words')
            stop=min((w[1] for w in words if V.norm(w[4])=='abstract'),default=0)
            names=[]
            for name in pdf['authors']:
                found=[]
                for top in sorted({w[1] for w in words if w[1]<stop}):
                    row=sorted([w for w in words if abs(w[1]-top)<3],key=lambda w:w[0])
                    for a in range(len(row)):
                        for b in range(a+1,min(a+8,len(row))+1):
                            text=V.norm(' '.join(w[4] for w in row[a:b])).rstrip('*∗†‡,')
                            text=re.sub(r'\d+(?:\s*,\s*\d+)*$','',text).rstrip('*∗†‡,')
                            if text==V.norm(name):
                                box=(row[a][0],min(w[1] for w in row[a:b]),row[b-1][2],max(w[3] for w in row[a:b]))
                                if box not in found:found.append(box)
                if len(found)!=1:return {}
                names.append(found[0])
            left=min(b[0] for b in names)-5;top=max(b[3] for b in names)-1
            rows=[]
            for w in sorted([w for w in words if w[0]>=left and top<=w[1]<stop],key=lambda w:(w[1],w[0])):
                if not rows or w[1]-rows[-1][0][1]>5:rows.append([w])
                else:rows[-1].append(w)
            definitions={};current=None
            for row in rows:
                row.sort(key=lambda w:w[0]);tokens=[w[4] for w in row]
                joined=re.fullmatch(r'([1-9][0-9]?)([A-Za-z].*)',tokens[0])
                if joined:tokens=[joined[1],joined[2]]+tokens[1:]
                if current and re.match(r'^\*?\s*(?:Corresponding\s+author|Received\s*:|Keywords\s*:|Abstract\b)',' '.join(tokens),re.I):break
                if re.fullmatch(r'[1-9][0-9]?',tokens[0]):
                    current=tokens[0]
                    if current in definitions:return {}
                    definitions[current]=[]
                if current:definitions[current].extend(tokens)
            return {k:' '.join(v) for k,v in definitions.items()}
    except (RuntimeError,ValueError,IndexError,KeyError):return {}


def indexed_affiliations(p, header, raw):
    from . import student_authorship_reviews as V
    blocks=p.get('affiliation_blocks') or [];by={b['marker']:b for b in blocks}
    if not by or len(by)!=len(blocks):return False
    actual=numbered_blocks(raw,p['pdf'])
    if set(actual)!=set(by):return False
    for marker,b in by.items():
        quote=b['quote'].strip()
        if (V.norm(quote)!=V.norm(actual[marker]) or not re.match(r'^'+re.escape(marker)+r'(?!\d)',quote)
                or any(not V.has_name(quote,f) for f in b['affiliations'])):return False
        if b.get('marker_kind','institution')=='correspondence':
            if b['affiliations'] or not re.match(r'^'+re.escape(marker)+r'\s+(?:Authors? to whom.*correspondence|Corresponding authors?)\b',quote,re.I):return False
        elif not b['affiliations']:return False
    for a in p['authors']:
        q=a.get('marker_quote','');marks=a.get('affiliation_markers') or []
        if not q or not marks or not V.literal_occurrences(q,header) or not V.norm(q).startswith(V.norm(a['printed'])):return False
        tail=V.norm(q)[len(V.norm(a['printed'])):]
        if (re.findall(r'\d+',tail)!=marks or re.search(r'[^\d\s,*†‡]',tail)
                or any(m not in by for m in marks)):return False
        original=re.findall(re.escape(V.norm(a['printed']))+r'(\s*\d+(?:\s*,\s*\d+)*(?:\s*[,]*[*†‡])*)',V.norm(header))
        if len(original)!=1 or re.findall(r'\d+',original[0])!=marks:return False
        if a['affiliations']!=list(dict.fromkeys(f for m in marks for f in by[m]['affiliations'])):return False
    return True


def named_affiliations(p, original, paragraphs=None):
    from . import student_authorship_reviews as V
    authors=p['authors'];seen=[]
    for g in p.get('affiliation_groups') or []:
        ids=g['authors'];quote=g['quote']
        whole=(V.norm(quote) in paragraphs if paragraphs is not None else V.named_author_clause(quote,original))
        if not ids or len(set(ids))!=len(ids) or any(i>=len(authors) for i in ids) or not whole:return False
        if not V.starts_name(quote,authors[ids[0]]['printed']):return False
        if paragraphs is not None:
            prefix=r'\s*(?:,\s*and\s+|\s+and\s+|,\s*)'.join(re.escape(authors[i]['printed']) for i in ids)
            if not re.match(r'^'+prefix+r'\s+'+('is' if len(ids)==1 else 'are')+r'\s+with\b',quote,re.I):return False
            if re.search(r'(?i)\b(?:thanks|thank|acknowledg\w*|helpful comments|supported by)\b',quote):return False
        if any(not V.has_name(quote,authors[i]['printed']) for i in ids):return False
        if any(V.has_name(quote,a['printed']) for i,a in enumerate(authors) if i not in ids):return False
        if any(not V.has_name(quote,f) for f in g['affiliations']):return False
        if any(authors[i]['affiliations']!=g['affiliations'] for i in ids):return False
        seen.extend(ids)
    return sorted(seen)==list(range(len(authors)))


def original_blocks(raw, pdf):
    import pymupdf
    try:
        with pymupdf.open(stream=raw,filetype='pdf') as doc:
            return doc[pdf.get('article_page',1)-1].get_text('dict')['blocks']
    except (RuntimeError,ValueError,IndexError):return []


def block_text(block):
    return '\n'.join(''.join(s['text'] for s in line['spans']) for line in block.get('lines',[]))


def original_title(raw, pdf):
    import pymupdf
    from . import student_authorship_reviews as V
    try:
        with pymupdf.open(stream=raw,filetype='pdf') as doc:
            page=doc[pdf.get('article_page',1)-1]
            author=page.search_for(pdf['authors'][0])
            blocks=[b for b in page.get_text('dict')['blocks'] if b['type']==0 and V.norm(block_text(b))==V.norm(pdf['title'])]
            return (len(blocks)==1 and bool(author) and blocks[0]['bbox'][3]<min(r.y0 for r in author)
                    and V.norm(pdf['title_quote'])==V.norm(block_text(blocks[0])))
    except (RuntimeError,ValueError,IndexError,KeyError):return False


def publisher_footer_doi(raw, pdf):
    """A complete formal identifier or same-column ACM publisher-imprint footer."""
    import pymupdf
    from . import student_authorship_reviews as V
    try:
        with pymupdf.open(stream=raw,filetype='pdf') as doc:
            page=doc[pdf.get('article_page',1)-1]
            lines=[]
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    text=''.join(s['text'] for s in line['spans'])
                    lines.append((V.norm(text),line['bbox']))
                    if (line['bbox'][1]>.7*page.rect.height
                            and V.norm(text)=='digital object identifier '+pdf['doi']):return True
            for text,box in lines:
                if box[1] <= .7*page.rect.height or not re.fullmatch(r'https?://doi\.org/(?:doi\.org/)?'+re.escape(pdf['doi']),text):continue
                context=[t for t,b in lines if abs(b[0]-box[0])<5 and 0<box[1]-b[1]<80]
                if (any(re.search(r'\bacm\b',t) for t in context)
                        and any(re.search(r'©|\bcopyright\b',t) and pdf['date'][:4] in t for t in context)):
                    return True
    except (RuntimeError,ValueError,IndexError,KeyError):pass
    return False


def shared_affiliation(raw, pdf):
    """One complete unindexed institution block below the whole author row.

    Separate author-column affiliations, including non-university employers,
    cannot be promoted to a shared affiliation by selecting a Cambridge token.
    """
    import pymupdf
    from . import student_authorship_reviews as V
    try:
        with pymupdf.open(stream=raw,filetype='pdf') as doc:
            page=doc[pdf.get('article_page',1)-1]
            abstracts=page.search_for('Abstract')
            if not abstracts:return False
            stop=min(r.y0 for r in abstracts)
            spans=[]
            for name in pdf['authors']:
                hits=[r for r in page.search_for(name) if r.y1<stop]
                if len(hits)!=1:return False
                spans.append(hits[0])
            if max(r.y0 for r in spans)-min(r.y0 for r in spans)>3:return False
            top=max(r.y1 for r in spans)
            blocks=[b for b in page.get_text('dict')['blocks'] if b['type']==0 and top+1<b['bbox'][1]<stop]
            if len(blocks)!=1:return False
            block=blocks[0];lines=block['lines']
            if not lines or max(line['bbox'][0] for line in lines)-min(line['bbox'][0] for line in lines)>3:return False
            for line in lines:
                words=sorted(line['spans'],key=lambda s:s['bbox'][0])
                if any(b['bbox'][0]-a['bbox'][2]>20 for a,b in zip(words,words[1:])):return False
            return V.norm(block_text(block))==V.norm(pdf['affiliation_quote']) and V.has_name(block_text(block),'University of Cambridge')
    except (RuntimeError,ValueError,IndexError,KeyError):return False


def proof_error(d, member, paper, pi, school, *, source=None, root=None):
    from . import student_authorship_reviews as V
    if school!='cambridge' or d['school']!=school or source is None:return 'unsupported_thesis_school_or_source'
    if d['preimages']!=V.preimages(member,paper,pi,source):return 'stale_scientific_preimage'
    p=d['proof'];t=p['thesis'];pdf=p['pdf'];identity=orcid(p['orcid'])
    if identity is None:return 'invalid_author_orcid'
    match=re.fullmatch(r'https://www\.repository\.cam\.ac\.uk/items/([a-f0-9-]{36})',t['url'])
    if not match or member.get('sourceRecordKey')!='cambridge-thesis:'+match[1]:return 'different_thesis_source_person'
    raw=V.evidence_bytes(school,t['sha256'],root=root)
    if raw is None or hashlib.sha256(raw).hexdigest()!=t['sha256']:return 'missing_or_changed_original_thesis'
    soup=BeautifulSoup(raw,'html.parser')
    urls=[]
    for tag in soup.find_all('script',type='application/ld+json'):
        try:
            obj=json.loads(tag.get_text());urls.append(obj.get('url') if isinstance(obj,dict) else None)
        except (ValueError,TypeError):pass
    if t['url'] not in urls:return 'unbound_original_thesis_item'
    authors=fields(soup,'Authors')
    if len(authors)!=1:return 'competing_thesis_author_fields'
    people=authors[0].find_all('ds-orcid-metadata-representation-loader')
    if len(people)!=1:return 'competing_thesis_author_slots'
    spans=people[0].find_all('span');links=people[0].find_all('a',href=True)
    if (len(spans)!=1 or V.norm(forward(spans[0].get_text(' ',strip=True)))!=V.norm(member['name'])
            or [orcid(a['href']) for a in links]!=[identity]
            or ' '.join(authors[0].get_text(' ',strip=True).split())!=t['quote']):
        return 'different_original_thesis_author_orcid'
    expected={'Date':t['date'],'Qualification':t['qualification'],'Awarding Institution':'University of Cambridge'}
    for label,value in expected.items():
        owned=fields(soup,label)
        if len(owned)!=1 or ' '.join(owned[0].get_text(' ',strip=True).split())!=label+' '+value:return 'different_original_thesis_'+label.lower().replace(' ','_')
    advisors=fields(soup,'Advisors')
    if len(advisors)!=1:return 'different_original_thesis_advisors'
    if t.get('advisors'):
        body=advisors[0].find('div',class_='simple-view-element-body')
        entries=[s.get_text(' ',strip=True) for s in body.find_all('span',class_='dont-break-out')] if body else []
        if entries!=t['advisors'] or t['advisor'] not in entries:return 'different_original_thesis_advisors'
    elif ' '.join(advisors[0].get_text(' ',strip=True).split())!='Advisors '+t['advisor']:
        return 'different_original_thesis_advisors'
    if t['qualification']!='Doctor of Philosophy (PhD)' or 'phd' not in member.get('roles',[]):return 'unbound_thesis_student_role'
    if not any(V.name_variant_ok(forward(t['advisor']),n,'middle_names') for n in [pi['pi']]+pi.get('names',[])):return 'different_thesis_adviser'
    retained=[r for r in member.get('relations',[]) if r.get('role')=='phd' and r.get('type')=='researched_advising' and any(all(q.get(k)==t[k] for k in ['url','sha256','quote']) for q in r.get('sources',[]))]
    try:
        year=datetime.date.fromisoformat(t['date']).year
        if len(retained)!=1 or retained[0].get('years')!=[year]:return 'unbound_thesis_recorded_year'
        lo,hi=datetime.date(year-2,1,1),datetime.date(year+6,12,31)
        a,b=V.bounds(paper['date']);c,e=V.bounds(pdf['date'])
        if paper['year']!=a.year or a.year!=b.year or a.year!=c.year or c.year!=e.year:return 'publication_date_conflict'
        if not(lo<=a<=b<=hi and lo<=c<=e<=hi):return 'outside_recorded_student_publication_window'
    except (ValueError,TypeError,KeyError):return 'invalid_thesis_or_publication_date'
    if paper.get('editions') or not paper.get('identity') or not paper.get('appointment') or str(paper['identity']).startswith(('candidate','unknown','unverified')):return 'ineligible_or_multiple_edition_lab_paper'
    native=[a.get('raw_author_name') or (a.get('author') or {}).get('display_name') for a in source.get('authorships',[])]
    if source.get('id')!=d['match']['oa'] or V.ndoi(source.get('doi'))!=V.ndoi(paper.get('doi')) or native!=paper.get('byline') or native!=[a['native'] for a in p['authors']]:return 'different_native_source_byline'
    text=V.original_pdf_text(school,pdf,root=root)
    if text is None:return 'missing_or_changed_primary_pdf'
    if not (pdf['complete_body'] and pdf['parse_returncode']==0 and pdf['pages']>0 and pdf['bytes']>0):return 'incomplete_primary_pdf'
    head=V.article_page_text(p,text)
    if head is None:return 'unbound_primary_article_page_or_cover'
    plain=' '.join(head.split());header=re.split(r'(?i)\bAbstract\b',plain,maxsplit=1)[0]
    before_references=re.split(r'(?i)\b(?:References|Bibliography)\b',plain,maxsplit=1)[0]
    header_dois=V.printed_dois(header)
    if (V.printed_dois(before_references)!={pdf['doi']}
            or header_dois and header_dois!={pdf['doi']}
            or not (header_dois=={pdf['doi']} or publisher_footer_doi(V.evidence_bytes(school,pdf['sha256'],root=root),pdf))):
        return 'unbound_primary_article_doi'
    lines=[V.norm(x) for x in head.splitlines() if x.strip()]
    coordinate_title=pdf.get('title_parser')=='original_pdf_block'
    title_replay=(original_title(V.evidence_bytes(school,pdf['sha256'],root=root),pdf) if coordinate_title else
                  any(V.norm(' '.join(lines[i:j]))==V.norm(pdf['title']) for i in range(len(lines)) for j in range(i+1,min(i+12,len(lines))+1)))
    if not V.title_ok(p,paper,plain) or V.norm(pdf['title_quote'])!=V.norm(pdf['title']) or not title_replay:return 'different_complete_primary_title'
    for field in (['byline_quote'] if coordinate_title else ['title_quote','byline_quote']):
        if not V.literal_occurrences(pdf[field],header):return 'unbound_primary_publication_header'
    fields_to_check=['date_quote','identifier_quote']+([] if pdf['mapping'] in ['shared_unindexed_affiliation','named_affiliation_paragraphs'] else ['affiliation_quote'])
    for field in fields_to_check:
        if not V.literal_occurrences(pdf[field],before_references):return 'unbound_primary_publication_quote'
    if (re.search(r'(?i)\b(?:received|accepted|revised)\b',pdf['date_quote'])
            or not re.search(r'(?i)©|\bcopyright\b|\bpublished\b|\bpublication date\b',pdf['date_quote'])):
        return 'unbound_primary_publication_date_event'
    if (pdf['doi']!=V.ndoi(paper.get('doi')) or not V.token_in_original(pdf['identifier_quote'],before_references,pdf['doi'],V.doi_tokens)
            or V.printed_dois(pdf['identifier_quote'])!={pdf['doi']} or pdf['date'] not in V.stated_dates(pdf['date_quote'])):return 'unbound_primary_work_or_date'
    printed=[a['printed'] for a in p['authors']];i=pdf['author_index']
    if (len(set(printed))!=len(printed) or printed!=pdf['authors'] or i>=len(printed)
            or printed[i]!=pdf['member_name'] or p['authors'][i]['member']!=member['person']
            or any(a['member'] is not None for j,a in enumerate(p['authors']) if j!=i)
            or not printed_name(member['name'],printed[i],p['name_variant'])):return 'different_primary_author'
    positions=[V.norm(pdf['byline_quote']).find(V.norm(n)) for n in printed]
    if min(positions)<0 or positions!=sorted(positions):return 'different_primary_byline_order'
    if any((pdf['mapping']!='indexed_affiliations' and not V.has_name(a['source_quote'],a['printed'])) or not V.literal_occurrences(a['source_quote'],plain) for a in p['authors']):return 'unbound_primary_affiliation_quote'
    if 'University of Cambridge' not in p['authors'][i]['affiliations']:return 'different_primary_author_affiliation'
    if pdf['mapping']=='shared_unindexed_affiliation':
        if re.search(r'\d',pdf['byline_quote']) or not shared_affiliation(V.evidence_bytes(school,pdf['sha256'],root=root),pdf):
            return 'ambiguous_shared_thesis_primary_affiliation'
        if any(a['affiliations']!=['University of Cambridge'] for a in p['authors']):return 'unbound_shared_thesis_primary_affiliation'
    elif pdf['mapping']=='indexed_affiliations':
        if not indexed_affiliations(p,header,V.evidence_bytes(school,pdf['sha256'],root=root)):return 'unbound_indexed_primary_affiliations'
    elif pdf['mapping']=='named_affiliation_groups':
        if not named_affiliations(p,head):return 'unbound_named_primary_affiliations'
    elif pdf['mapping']=='named_affiliation_paragraphs':
        paragraphs=[V.norm(block_text(b)) for b in original_blocks(V.evidence_bytes(school,pdf['sha256'],root=root),pdf) if b.get('type')==0]
        if not named_affiliations(p,head,paragraphs):return 'unbound_named_primary_affiliations'
    elif pdf['mapping']=='author_columns':
        boxes=V.original_pdf_boxes(school,pdf,root=root);page=pdf.get('article_page',1)-1
        columns=V.author_columns(head,printed,boxes[page]) if boxes and page<len(boxes) else None
        if not columns or ' '.join(pdf.get('author_binding_quote','').split())!=' '.join(columns[0].split()):return 'unbound_primary_author_columns'
        if any(any(not V.has_name(col,f) for f in a['affiliations']) for a,col in zip(p['authors'],columns[1])):return 'different_primary_column_affiliation'
    else:return 'unsupported_thesis_primary_affiliation_mapping'
    if not V.has_name(pdf['affiliation_quote'],'University of Cambridge'):return 'different_primary_author_affiliation'
    pdfraw=V.evidence_bytes(school,pdf['sha256'],root=root)
    if not annotation_author(pdfraw,pdf,identity):return 'unbound_original_primary_author_orcid_badge'
    return None
