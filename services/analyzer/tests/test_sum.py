import pytest
from services.analyzer.summarize import summarize_articles
# test_summarize.py
class DummyResponse:
    def __init__(self, content):
        # the real .choices[0].message.content
        msg = type("M", (), {"content": content})
        self.choices = [type("C", (), {"message": msg})]

class DummyChat:
    def __init__(self, response):
        self.completions = self
        self._response = response
    def create(self, *args, **kw):
        return self._response

class DummyClient:
    def __init__(self):
        # _client.chat.completions.create() → DummyResponse
        self.chat = DummyChat(DummyResponse("TEST SUMMARY"))

@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    import services.analyzer.summarize as mod
    monkeypatch.setattr(mod, "_client", DummyClient())


def test_summarize_and_relevance():
    text = "foo bar baz foo bar baz"
    summary, score = summarize_articles(text)
    assert summary == "TEST SUMMARY"
    # ROUGE-L F1 of identical words should be > 0
    assert 0.0 <= score <= 1.0
