"""Basic tests for notion worker service."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

def test_notion_worker_imports():
    """Test that notion worker modules can be imported."""
    try:
        from services.notion_worker.app.main import app
        from services.notion_worker.app.notion_client import NotionClient
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_app_creation():
    """Test that FastAPI app can be created."""
    from services.notion_worker.app.main import app
    assert app is not None

@patch.dict(os.environ, {'NOTION_API_KEY': 'test_key', 'NOTION_DB_ID': 'test_db'})
def test_notion_client_creation():
    """Test that NotionClient can be created."""
    from services.notion_worker.app.notion_client import NotionClient

    client = NotionClient()
    assert client is not None