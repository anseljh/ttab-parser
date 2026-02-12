"""Integration tests for CourtListener API."""

import os
import pytest
import requests


@pytest.mark.integration
def test_citation_lookup_brown_v_board():
    """Test that the CourtListener Citation Lookup API resolves 347 U.S. 483 (Brown v. Board of Education)."""
    api_token = os.getenv("COURTLISTENER_API_TOKEN")
    if not api_token:
        pytest.skip("COURTLISTENER_API_TOKEN not set")

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
