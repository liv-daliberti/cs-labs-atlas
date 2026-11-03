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
