"""Integration tests for CourtListener API."""

import pytest
import requests
from src.settings import get as get_setting


@pytest.mark.integration
def test_citation_lookup_brown_v_board():
    """Test that the CourtListener Citation Lookup API resolves 347 U.S. 483 (Brown v. Board of Education)."""
    api_token = get_setting("CourtListener", "api_token")
    if not api_token:
        pytest.skip("CourtListener api_token not set in settings.toml")

    url = "https://www.courtlistener.com/api/rest/v4/citation-lookup/"
    headers = {
        "Authorization": f"Token {api_token}",
    }
    data = {"text": "347 U.S. 483"}

    response = requests.post(url, headers=headers, data=data, timeout=30)
    assert response.status_code == 200

    results = response.json()
    assert len(results) > 0

    result = results[0]
    assert result["citation"] == "347 U.S. 483"
    assert result["status"] == 200

    clusters = result["clusters"]
    assert len(clusters) > 0

    cluster = clusters[0]
    assert "Brown" in cluster["case_name"]
