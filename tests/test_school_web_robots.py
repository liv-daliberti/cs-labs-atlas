"""school_web.robots_decision: allowed-for-us, allowed-for-AI-agents-by-name, and the crawl delay that binds this project."""
import school_web as W

ROBOTS_NAMED_DELAY = """User-agent: PerplexityBot
User-agent: ClaudeBot
User-agent: CCBot
Crawl-delay: 10

User-agent: *
Disallow: /core/
"""


def test_a_crawl_delay_in_a_group_naming_claudebot_binds_us():
    ours, ai, delay = W.robots_decision(200, ROBOTS_NAMED_DELAY, '/people/')
    assert ours and ai and delay == 10.0


def test_star_group_delay_and_floor():
    assert W.robots_decision(200, 'User-agent: *\nCrawl-delay: 20\n', '/')[2] == 20.0
    assert W.robots_decision(200, 'User-agent: *\nDisallow:\n', '/')[2] == 2.0
    assert W.robots_decision(404, '', '/')[2] == 2.0


def test_ai_agent_disallow_is_detected_by_name():
    ours, ai, _ = W.robots_decision(200, 'User-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nDisallow:\n', '/x')
    assert ours and not ai


def test_urls_on_host_lists_department_and_unit_slots():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('sh_by_path', Path(__file__).resolve().parents[1] / 'tools' / 'school_hosts.py')
    H = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(H)
    cfg = {'departments': [{'listings': [{'url': 'https://old.edu/people/'}, {'url': 'https://new.edu/p'}]}],
           'affiliated_units': [{'listings': ['old.edu/people/faculty/', 'x.edu/y']}]}
    assert H.urls_on_host(cfg, 'old.edu') == ['https://old.edu/people/', 'old.edu/people/faculty/']
