import pytest
import httpx
from services.analyzer.main import fetch_and_extract

class DummyResp:
    text = "<html><body><h1>Hi</h1><p>Earth</p></body></html>"
    def raise_for_status(self): pass

@pytest.mark.asyncio
async def test_fetch_and_extract(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *args, **kw: DummyResp())
    out = await fetch_and_extract("http://example.com")
    assert "Hi" in out and "Earth" in out
