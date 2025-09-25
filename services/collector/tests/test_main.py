"""Basic tests for collector service."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_collector_imports():
    """Test that collector modules can be imported."""
    try:
        import collector.main
        import collector.article
        import collector.utils
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

@patch('collector.main.init_db')
def test_app_creation(mock_init_db):
    """Test that FastAPI app can be created."""
    from collector.main import app
    assert app is not None
    assert app.title == "RaveDigest Collector Service"

def test_article_class():
    """Test Article class basic functionality."""
    from collector.article import Article

    article = Article(
        title="Test Article",
        url="https://example.com",
        published="2024-01-01T00:00:00Z",
        source="Test Source",
        summary="Test summary"
    )

    assert article.title == "Test Article"
    assert article.url == "https://example.com"
    assert article.source == "Test Source"