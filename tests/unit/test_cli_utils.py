"""
Unit tests for CLI utilities.
"""

import pytest
from agentosx.cli.utils import (
    format_duration,
    load_config,
    save_config,
)


@pytest.mark.unit
def test_format_duration_milliseconds():
    """Test duration formatting for milliseconds."""
    assert format_duration(0.001) == "1.00ms"
    assert format_duration(0.050) == "50.00ms"


@pytest.mark.unit
def test_format_duration_seconds():
    """Test duration formatting for seconds."""
    assert format_duration(1.5) == "1.50s"
    assert format_duration(30.0) == "30.00s"


@pytest.mark.unit
def test_format_duration_minutes():
    """Test duration formatting for minutes."""
    assert format_duration(90.0) == "1.50m"
    assert format_duration(180.0) == "3.00m"


@pytest.mark.unit
def test_load_config_missing_file(tmp_path):
    """Test loading config when file doesn't exist."""
    config = load_config(tmp_path / "nonexistent.yaml")
    assert config == {}


@pytest.mark.unit
def test_save_and_load_config(tmp_path):
    """Test saving and loading config."""
    config_path = tmp_path / ".agentosx.yaml"
    
    test_config = {
        "default_provider": "openai",
        "default_model": "gpt-4",
    }
    
    save_config(config_path, test_config)
    loaded = load_config(config_path)
    
    assert loaded == test_config
