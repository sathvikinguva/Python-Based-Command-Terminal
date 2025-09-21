"""
Test configuration and fixtures for PyTerm tests.
"""

import pytest
import tempfile
from pathlib import Path
import os


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        'safe_mode': True,
        'allowed_root': '.',
        'dry_run': False,
        'recycle_bin': '.recycle_bin',
        'ai_enabled': False,
        'colors_enabled': True,
        'log_level': 'INFO'
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables and working directory after each test."""
    original_cwd = os.getcwd()
    original_env = os.environ.copy()
    
    yield
    
    # Restore original state
    os.chdir(original_cwd)
    os.environ.clear()
    os.environ.update(original_env)