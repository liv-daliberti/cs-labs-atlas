"""Actual body and asset eligibility, distinct from work scope and licence/identity."""
import hashlib
import sqlite3
from types import SimpleNamespace

import pytest

import copy_quality as Q
import lab_paper_copies as C
import reader_export as R
import collector_quality as D

NOTICE = ('Full Text Availability The license terms selected by the author(s) for this preprint version do not permit '
          'archiving in PMC. The full text is available from the preprint server.')
TEXT = ('We measured the response in a controlled experiment and compared it with a prespecified baseline. '
        'The observed difference persisted across repeated measurements. We report the complete result in this brief '
        'letter, including its uncertainty and the conditions needed to reproduce the measurement. ')


def article(body, namespace=''):
    return (f'<article{namespace}><front><article-meta><article-id pub-id-type="doi">10.1/x</article-id>'
            '<title-group><article-title>Real paper</article-title></title-group>'
            '<abstract><p>A long abstract does not supply the article body.</p></abstract>'
            f'</article-meta></front>{body}</article>').encode()


def test_exact_177_character_PMC_notice_is_not_a_full_article():
    assert len(NOTICE) == 177
    raw = article('<body><sec><title>Full Text Availability</title><p>' + NOTICE.split('Availability ', 1)[1] + '</p></sec></body>')
    result = Q.xml_quality(raw)
    assert result['ok'] is False and result['reason'] == 'xml_rights_notice_only'
    assert result['body_characters'] == 0


@pytest.mark.parametrize('namespace', ['', ' xmlns="http://jats.nlm.nih.gov"'])
def test_complete_short_one_paragraph_article_is_preserved(namespace):
    # A real letter need not reach an arbitrary 1,000-character/3-paragraph quota.
    result = Q.xml_quality(article('<body><p>' + TEXT + '</p></body>', namespace))
    assert result['ok'] is True and result['body_paragraphs'] == 1
    assert 200 <= result['body_characters'] < 1000


@pytest.mark.parametrize('body,reason', [('', 'xml_no_article_body'), ('<body/>', 'xml_no_substantive_body'),
    ('<body><abstract><p>' + TEXT * 10 + '</p></abstract></body>', 'xml_no_substantive_body'),
    ('<body><sec><title>Abstract</title><p>' + TEXT * 10 + '</p></sec></body>', 'xml_no_substantive_body')])
def test_metadata_or_abstract_only_XML_is_not_a_full_article(body, reason):
    assert Q.xml_quality(article(body))['reason'] == reason


def test_notice_does_not_discard_a_real_body_in_another_section():
    raw = article('<body><sec><p>' + NOTICE + '</p></sec><sec><title>Results</title><p>' + TEXT + '</p></sec></body>')
    assert Q.xml_quality(raw)['ok'] is True


def test_XML_comments_and_external_entities_cannot_supply_article_text(tmp_path):
    assert Q.xml_quality(article('<body><!-- harmless --><p>' + TEXT + '</p></body>'))['ok']
    secret = tmp_path / 'secret'; secret.write_text(TEXT * 10)
    raw = f'<!DOCTYPE article [<!ENTITY external SYSTEM "{secret.as_uri()}">]><article><body><p>&external;</p></body></article>'.encode()
    assert not Q.xml_quality(raw)['ok']


def test_slide_metadata_needs_document_content_and_does_not_reclassify_a_work():
    slides = 'Improving Client Web Availability with MONET\n\fAvailability We Want\n• Carrier Airlines\n• 911 Phone service\n'
    assert Q.pdf_nonpaper_reason(slides, 'Title: slides.dvi\n') == 'pdf_slide_deck'
    assert Q.pdf_nonpaper_reason('Real Paper\nAbstract\n' + TEXT, 'Title: slides.dvi\n') is None
    assert Q.pdf_nonpaper_reason('Real Paper\nAbstract\nOur panel-data analysis studies CHI.\n') is None


@pytest.mark.parametrize('front', ['Panel Session: Rising CS Enrollments\nSIGCSE2018\n',
    'Panel\n\nCSCW2017\nCSCW Research Ethics Town Hall\n', 'CHI2018 unrelated research',
    'CHI 2018 Panel & Roundtable Discussion\nResearch Ethics for HCI\n', 'CHI 2019 SIG\nLearning, Education, and HCI\n'])
def test_explicit_event_headers_are_asset_failures_only(front):
    assert Q.pdf_nonpaper_reason(front) == (None if front == 'CHI2018 unrelated research' else 'pdf_event_description')


def store(tmp_path, raw):
    folder = tmp_path / 'mit'; folder.mkdir(); (folder / 'objects').mkdir()
    h = hashlib.sha256(raw).hexdigest(); path = folder / 'objects' / (h + '.xml'); path.write_bytes(raw)
    db = sqlite3.connect(folder / 'catalog.sqlite')
    db.executescript('''create table works(id text primary key,status text,file_path text,sha256 text,byte_count integer,
        download_url text,identity_check text,doi text,title text,year integer);
        create table assets(work_id text,kind text,path text,sha256 text,bytes integer,identity_check text,url text,version text,license text);
        create table candidates(work_id text,url text,landing_url text,license text,version text);
        create table attempts(work_id text,url text,status text,detail text);''')
    # Actual audit: the works row still points to an older quarantined PDF.
    db.execute('insert into works values(?,?,?,?,?,?,?,?,?,?)', ('w','fulltext_xml','quarantine/old.pdf','a'*64,999,'https://old/x.pdf','old_pdf_identity','10.1/x','Real paper',2025))
    db.execute('insert into assets values(?,?,?,?,?,?,?,?,?)', ('w','xml',str(path.relative_to(folder)),h,len(raw),'doi_in_jats_article_metadata','https://pmc.example/x.xml','publishedVersion','cc-by'))
    db.commit()
    w = dict(id='w', status='fulltext_xml', file_path='quarantine/old.pdf', sha256='a'*64, byte_count=999,
             download_url='https://old/x.pdf', identity_check='old_pdf_identity', doi='10.1/x', title='Real paper', year=2025)
    a = dict(work_id='w', kind='xml', path=str(path.relative_to(folder)), sha256=h, bytes=len(raw),
             identity_check='doi_in_jats_article_metadata', url='https://pmc.example/x.xml', version='publishedVersion', license='cc-by')
    return folder, db, w, a


@pytest.mark.parametrize('full', [True, False])
def test_counter_and_reader_use_actual_XML_asset_and_preserve_target_work(tmp_path, full):
    raw = article('<body><p>' + (TEXT if full else NOTICE) + '</p></body>')
    folder, db, w, a = store(tmp_path, raw)
    target = dict(work='w', oa='W1', doi='10.1/x', title='Real paper', year=2025, editions=[])
    out, counts = C.resolve('mit', [target], {'w':'fulltext_xml'}, {'10.1/x':'w'}, set(),
                            quality=lambda wid, st: Q.catalog_status(db, folder, wid, st))
    cp = R.copy_for('w', w, [a], [], R.ArxivLicenses(), store=folder)
    if full:
        assert counts['local'] == 1
        assert (cp['format'], cp['sha256'], cp['bytes'], cp['path']) == ('xml', a['sha256'], len(raw), a['path'])
        assert cp['download_url'] == a['url']
    else:
        assert counts['local'] == 0 and out['w']['status'] == 'copy_quality_unconfirmed'
        assert out['w']['copy_quality_reason'] == 'xml_rights_notice_only' and cp is None
    assert target['title'] == 'Real paper' and db.execute('select status from works').fetchone()[0] == 'fulltext_xml'
    assert set(out) == {'w'}  # no work removal/reclassification


def test_invalid_XML_does_not_hide_a_valid_same_work_asset(tmp_path):
    folder, db, w, a = store(tmp_path, article('<body><p>' + NOTICE + '</p></body>'))
    good = article('<body><p>' + TEXT + '</p></body>');h=hashlib.sha256(good).hexdigest();path=folder/'objects'/(h+'.xml');path.write_bytes(good)
    b=dict(a,path=str(path.relative_to(folder)),sha256=h,bytes=len(good),url='https://pmc.example/good.xml')
    chosen, result=Q.catalog_copy(folder,w,[a,b])
    assert result['ok'] and chosen['sha256']==h


def test_changed_file_invalidates_only_in_process_quality_cache(tmp_path):
    p=tmp_path/'copy.xml';p.write_bytes(article('<body><p>'+TEXT+'</p></body>'))
    assert Q.file_quality(p,'xml')['ok']
    p.write_bytes(article('<body><p>'+NOTICE+'</p></body>'))
    assert not Q.file_quality(p,'xml')['ok']


@pytest.mark.parametrize('full', [True, False])
def test_collector_catalog_state_uses_actual_XML_body(tmp_path, monkeypatch, full):
    import ftp_common as F
    folder, db, w, a=store(tmp_path,article('<body><p>'+(TEXT if full else NOTICE)+'</p></body>'))
    monkeypatch.setattr(F,'FT',tmp_path)
    state=F.catalog_state('mit',with_urls=False)
    assert (state['status']['w']=='fulltext_xml') is full
    assert ('w' in state['local']) is full
    assert db.execute('select status from works').fetchone()[0]=='fulltext_xml'


def test_XML_licence_never_authorizes_the_stale_PDF_hash(tmp_path,monkeypatch):
    folder,db,w,a=store(tmp_path,article('<body><p>'+TEXT+'</p></body>'))
    monkeypatch.setattr(R.P,'STORES',tmp_path)
    paper=dict(work='w',oa='W1',doi='10.1/x',title='Real paper',year=2025,editions=[])
    records,stats,checks,requests=R.school_rows('mit',[paper],R.ArxivLicenses(),hosted_shas={'a'*64})
    assert records[0]['sha256']==a['sha256'] and records[0]['format']=='xml'
    assert checks['a'*64][0]['decision']=='not_confirmed'


def test_download_guard_calls_original_policy_client_and_keeps_other_candidates():
    calls=[]
    class Client:
        def get(self,url):
            calls.append(url)
            return article('<body><p>'+(NOTICE if 'stub' in url else TEXT)+'</p></body>'),url,'application/xml'
    wrapper=SimpleNamespace(c=SimpleNamespace(PublicClient=Client,base=SimpleNamespace(validate_pdf=lambda data,path:1)))
    D.install(wrapper,Q)
    with pytest.raises(ValueError,match='copy_quality: xml_rights_notice_only'):
        Client().get('https://pmc.example/stub.xml')
    assert Client().get('https://pmc.example/full.xml')[0]
    assert calls==['https://pmc.example/stub.xml','https://pmc.example/full.xml']
