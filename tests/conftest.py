"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from datetime import datetime


@pytest.fixture
def sample_xml_content():
    """Sample TTAB XML content for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<ttab-proceedings>
    <proceeding-entry>
        <proceeding-number>91234567</proceeding-number>
        <filing-date>20250115</filing-date>
        <proceeding-type>Opposition</proceeding-type>
        <status>Terminated</status>
        <party-information>
            <party>
                <party-name>Test Company Inc</party-name>
                <role-code>P</role-code>
            </party>
            <party>
                <party-name>Defendant Corp</party-name>
                <role-code>D</role-code>
            </party>
        </party-information>
    </proceeding-entry>
</ttab-proceedings>"""


@pytest.fixture
def sample_date_strings():
    """Sample date strings in different formats."""
    return {
        'yyyymmdd': '20250115',
        'iso': '2025-01-15',
        'invalid': 'not-a-date'
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for testing."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir
