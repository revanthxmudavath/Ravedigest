# services/collector/tests/test_parse.py

import pytest
from types import SimpleNamespace
from collector.parse import parse_feed

# A tiny sample of two “feed” entries: one valid, one malformed
VALID_ENTRY = {
    "title": "Valid Article",
    "link": "https://example.com/valid",
    "description": "Summary here",
    "published_parsed": (2025,7,20,12,0,0,0,0,0),
    "tags": [SimpleNamespace(term="Test")],
}
BAD_URL_ENTRY = {
    "title": "Bad URL Article",
    "link": "ht!tp:/bad-url",
    "description": "Should fail",
    "published_parsed": (2025,7,20,12,0,0,0,0,0),
    "tags": [],
}

class DummyEntry(SimpleNamespace):
    """A minimal FeedParserDict stand-in: supports .get() and attribute access."""
    def get(self, key, default=None):
        return getattr(self, key, default)

class DummyFeed:
    def __init__(self, entries):
        # convert dict → DummyEntry so .get()/.tags etc work
        self.entries = [DummyEntry(**e) for e in entries]

def test_parse_valid_and_skip_invalid(monkeypatch):
    # feedparser.parse(...) → our DummyFeed with one good + one bad
    monkeypatch.setattr(
        "collector.parse.feedparser.parse",
        lambda url: DummyFeed([VALID_ENTRY, BAD_URL_ENTRY])
    )

    articles = parse_feed("http://fake", "TestSource")

    # Only the valid one should survive
    assert len(articles) == 1
    a = articles[0]
    assert a.title == VALID_ENTRY["title"]
    assert str(a.url) == VALID_ENTRY["link"]
    assert a.source == "TestSource"

def test_all_invalid_entries_are_skipped(monkeypatch):
    # feedparser.parse(...) → DummyFeed with only the bad entry
    monkeypatch.setattr(
        "collector.parse.feedparser.parse",
        lambda url: DummyFeed([BAD_URL_ENTRY])
    )

    articles = parse_feed("http://fake", "TestSource")
    assert articles == []
