"""tools/discover_listings.py summarises CDX rows into half-years and gaps."""
import discover_listings as D


def rows(*ts):
    return [dict(timestamp=t, original='https://x.edu/people/') for t in ts]


def test_summarize_halves_and_gaps():
    s = D.summarize(rows('20160215000000', '20160915000000', '20170301000000'), 2016, 2017)
    assert s['halves'] == ['2016H1', '2016H2', '2017H1'] and s['missing'] == ['2017H2'] and s['captures'] == 3
    assert D.line('x.edu/people/', s) == 'x.edu/people/: 3 captures 20160215..20170301; 2016H1H2 2017H1'


def test_no_capture():
    s = D.summarize([], 2016, 2016)
    assert s['missing'] == ['2016H1', '2016H2'] and D.line('u', s) == 'u: no 200 capture'


def test_sample_picks_the_capture_nearest_mid_year_and_reports_format_and_paging(tmp_path, monkeypatch):
    rs = rows('20200110000000', '20200620000000', '20200912000000', '20240101000000')
    assert D.nearest(rs, 2020)['timestamp'] == '20200620000000' and D.nearest(rs, 2018) is None
    html = ('<div class="row profile-card__content variant-directory"><h4 class="card-block__title"><a href="/p/a">A B</a></h4><h6 class="card-block__subtitle">Professor</h6></div>'
            '<nav class="pager"><a href="?page=1">2</a></nav>')
    monkeypatch.setattr(D.W, 'capture', lambda c, ts, orig, url, key: ('cap' + ts, 200, 'sha', []))
    monkeypatch.setattr(D.W, 'raw_html', lambda c, cap: html)
    out = D.sample(None, 'k', 'x.edu/people/', rs, [2020, 2018], tmp_path)
    assert 'format gt_card, 1 entries, PAGED (1 more pages)' in out[0] and out[1] == '  2018: no capture'
    assert len(list(tmp_path.glob('*.html'))) == 1
