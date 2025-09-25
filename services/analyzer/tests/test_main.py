"""Basic tests for analyzer service."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

def test_analyzer_imports():
    """Test that analyzer modules can be imported."""
    try:
        from services.analyzer.main import app
        from services.analyzer.summarize import summarize_articles
        from services.analyzer.filter import mark_developer_focus
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_app_creation():
    """Test that FastAPI app can be created."""
    from services.analyzer.main import app
    assert app is not None
    assert app.title == "Rave Digest Analyzer"

def test_developer_focus_function():
    """Test developer focus detection function."""
    from services.analyzer.filter import mark_developer_focus

    # Test developer-focused content
    dev_title = "New Python Framework Released"
    dev_summary = "A new web framework for Python developers with async support"
    assert mark_developer_focus(dev_title, dev_summary) == True

    # Test non-developer content (should return bool)
    non_dev_title = "Celebrity News Update"
    non_dev_summary = "Latest entertainment news"
    result = mark_developer_focus(non_dev_title, non_dev_summary)
    assert isinstance(result, bool)