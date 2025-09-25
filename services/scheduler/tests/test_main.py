"""Basic tests for scheduler service."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

def test_scheduler_imports():
    """Test that scheduler modules can be imported."""
    try:
        from services.scheduler.src.main import app, daily_job
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_app_creation():
    """Test that FastAPI app can be created."""
    from services.scheduler.src.main import app
    assert app is not None

@patch('requests.get')
@patch('requests.post')
def test_daily_job_functions(mock_post, mock_get):
    """Test that daily job functions can be imported."""
    from services.scheduler.src.main import trigger_collector, trigger_composer

    # Mock successful responses
    mock_get.return_value.json.return_value = {"status": "success"}
    mock_get.return_value.raise_for_status.return_value = None
    mock_post.return_value.json.return_value = {"status": "success"}
    mock_post.return_value.raise_for_status.return_value = None

    # Test functions exist and are callable
    assert callable(trigger_collector)
    assert callable(trigger_composer)