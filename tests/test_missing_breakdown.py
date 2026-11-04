"""fulltext-push/missing_breakdown.py: reasons per school, venue and host groups, open-archive prefixes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fulltext-push'))
import missing_breakdown as M  # noqa: E402


def rec(school, reason, venue='', doi='', publisher='IEEE', url=None):
    return dict(school=school, reason_code=reason, venue=venue, doi=doi, publisher=publisher,
                attempts=[dict(url=url)] if url else [])


def test_breakdown_groups():
    recs = [rec('mit', 'publisher_only_closed', 'IEEE/CVF Conference on Computer Vision and Pattern Recognition'),
            rec('mit', 'landing_page_without_pdf', 'Zenodo', '10.5281/zenodo.1', url='https://zenodo.org/records/1'),
            rec('cmu', 'landing_page_without_pdf', 'Zenodo', '10.5281/zenodo.2', url='https://zenodo.org/records/2'),
            rec('cmu', 'publisher_only_closed')]
    o = M.breakdown(recs, 5)
    assert o['reason_by_school']['landing_page_without_pdf'] == {'mit': 1, 'cmu': 1}
    assert o['landing_page_without_pdf']['attempt_host'] == [('zenodo.org', 2)]
    assert o['publisher_only_closed']['attempt_host'] == [('(no attempt)', 2)]
    assert o['open_venues']['CVF (CVPR/ICCV/WACV)'] == {'publisher_only_closed': 1}
    assert o['open_archive_prefixes']['Zenodo'] == {'landing_page_without_pdf': 2}
