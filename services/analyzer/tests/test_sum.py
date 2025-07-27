import pytest
from summarize import summarize_articles, _client

# A dummy response object to mimic OpenAI’s shape
class DummyResponse:
    def __init__(self, content):
        msg = type("Msg", (), {"content": content})
        choice = type("Choice", (), {"message": msg})
        self.choices = [choice]

# Fixture to monkey‐patch the OpenAI client before every test
@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    class FakeClient:
        def chat(self):
            return self
        def completions(self):
            return self
        def create(self, model, messages):
            return DummyResponse("Brief summary")
    monkeypatch.setattr("summarize._client", FakeClient(), raising=False)
    class FakeClient:
        def __init__(self):
           
            self.chat = self
            self.completions = self
        def create(self, *args, **kwargs):
            return DummyResponse("Brief summary")
        
    import summarize
    monkeypatch.setattr(summarize, "_client", FakeClient(), raising=True)

    yield

def test_summarize_returns_summary_and_relevance():
    text = "Lorem ipsum " * 10  # ~110 chars
    summary, relevance = summarize_articles(text)
    # We patched the LLM to always return "Brief summary"
    assert summary == "Brief summary"
    # relevance = len(summary) / len(text)
    assert pytest.approx(relevance, rel=1e-3) == len("Brief summary") / len(text)
