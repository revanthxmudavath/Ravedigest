"""Basic tests for composer service."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

def test_composer_imports():
    """Test that composer modules can be imported."""
    try:
        from services.composer.app.main import app
        from services.composer.app.digest_utils import generate_and_publish_digest
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

@patch('services.composer.app.main.init_db')
def test_app_creation(mock_init_db):
    """Test that FastAPI app can be created."""
    from services.composer.app.main import app
    assert app is not None

@patch('services.composer.app.digest_utils.get_db')
def test_digest_utils_import(mock_get_db):
    """Test that digest utilities can be imported."""
    from services.composer.app.digest_utils import generate_and_publish_digest
    assert generate_and_publish_digest is not None