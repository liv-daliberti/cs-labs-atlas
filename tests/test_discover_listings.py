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
