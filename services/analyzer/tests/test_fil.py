import pytest
from filter import mark_developer_focus, _KEYWORDS, _MODEL, util

def test_keyword_match_triggers_true():
    # If any seed keyword appears, we short-circuit
    title = "Deep dive into developer API design"
    summary = ""
    assert mark_developer_focus(title, summary) is True

def test_cosine_similarity_above_threshold(monkeypatch):
    # Remove keywords so we go to the embedding stage
    monkeypatch.setattr("filter._KEYWORDS", [], raising=False)
    # Stub out embeddings and cos_sim
    monkeypatch.setattr(_MODEL, "encode", lambda text, convert_to_tensor: None)
    class FakeTensor:
        def __init__(self, v): self.v = v
        def max(self): return self
        def item(self): return self.v
    monkeypatch.setattr(util, "cos_sim", lambda emb, embs: FakeTensor(0.8))

    assert mark_developer_focus("nothing", "irrelevant text") is True

def test_cosine_similarity_below_threshold(monkeypatch):
    monkeypatch.setattr("filter._KEYWORDS", [], raising=False)
    monkeypatch.setattr(_MODEL, "encode", lambda text, convert_to_tensor: None)
    class FakeTensor:
        def __init__(self, v): self.v = v
        def max(self): return self
        def item(self): return self.v
    monkeypatch.setattr(util, "cos_sim", lambda emb, embs: FakeTensor(0.5))

    assert mark_developer_focus("nothing", "irrelevant text") is False
