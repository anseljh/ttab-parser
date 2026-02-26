"""
CourtListener API client for Federal Circuit appeals search.

Handles authentication, rate limiting, and search functionality
for matching TTAB cases with Federal Circuit appeals.
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
import requests
from urllib.parse import urlencode

from src.models import FederalCircuitAppeal, OutcomeType
from src.settings import get as get_setting

logger = logging.getLogger(__name__)


class CourtListenerClient:
    """Client for CourtListener REST API v4."""
    
    BASE_URL = "https://www.courtlistener.com/api/rest/v4/"
    FEDERAL_CIRCUIT_COURT_ID = "cafc"
    
    def __init__(self, api_token=None):
        """
        Initialize CourtListener client.
        
        Args:
            api_token (str, optional): API token. If not provided, will try to get from environment.
        """
        self.api_token = api_token or get_setting("CourtListener", "api_token")
        self.session = requests.Session()
        
        if self.api_token:
            self.session.headers.update({
                'Authorization': f'Token {self.api_token}',
                'User-Agent': 'TTAB-Federal-Circuit-Tracker/1.0'
            })
            self.enabled = True
            logger.info("CourtListener API client initialized successfully")
        else:
            self.enabled = False
            logger.warning("No CourtListener API token found. Set api_token under [CourtListener] in settings.toml to enable Federal Circuit appeal tracking.")
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
    
    def _rate_limit(self):
        """Enforce rate limiting between API requests."""
        if not self.enabled:
            return
            
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint, params=None):
        """
        Make authenticated request to CourtListener API.
        
        Args:
            endpoint (str): API endpoint path
            params (dict): Query parameters
            
        Returns:
            dict: JSON response or None if error
        """
        if not self.enabled:
            return None
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}{endpoint.lstrip('/')}"
            
            logger.debug(f"Making request to: {url}")
            if params:
                logger.debug(f"Parameters: {params}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"CourtListener API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CourtListener API response: {e}")
            return None
    
    def search_federal_circuit_cases(self, query, limit=20):
        """
        Search Federal Circuit cases using the search API.
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results
            
        Returns:
            list: List of search results
        """
        params = {
            'court': self.FEDERAL_CIRCUIT_COURT_ID,
            'type': 'o',  # Opinions
            'q': query,
            'format': 'json',
            'order_by': 'dateFiled desc'
        }
        
        if limit:
            params['page_size'] = min(limit, 100)  # API max is usually 100
        
        response = self._make_request('search/', params)
        
        if response and 'results' in response:
            return response['results']
        
        return []
    
    def search_by_case_number(self, case_number):
        """
        Search for Federal Circuit case by case number.
        
        Args:
            case_number (str): TTAB case number
            
        Returns:
            list: Matching Federal Circuit cases
        """
        # Clean and format case number for search
        clean_case_number = re.sub(r'[^\w\d\-]', ' ', case_number)
        
        query = f'"{case_number}" OR "{clean_case_number}"'
        return self.search_federal_circuit_cases(query, limit=10)
    
    def search_by_party_names(self, party_names, additional_terms=None):
        """
        Search for Federal Circuit cases by party names.
        
        Args:
            party_names (list): List of party names
            additional_terms (list, optional): Additional search terms
            
        Returns:
            list: Matching Federal Circuit cases
        """
        if not party_names:
            return []
        
        # Build search query with party names
        query_parts = []
        
        for party_name in party_names:
            if party_name and len(party_name.strip()) > 2:
                # Clean party name
                clean_name = re.sub(r'[^\w\s]', ' ', party_name.strip())
                if len(clean_name) > 2:
                    query_parts.append(f'"{clean_name}"')
        
        if additional_terms:
            for term in additional_terms:
                if term and len(term.strip()) > 2:
                    query_parts.append(f'"{term.strip()}"')
        
        if not query_parts:
            return []
        
        # Combine with OR logic for broader search
        query = ' OR '.join(query_parts[:5])  # Limit to avoid too long queries
        
        return self.search_federal_circuit_cases(query, limit=15)
    
    def get_case_details(self, case_id):
        """
        Get detailed information about a specific case.
        
        Args:
            case_id (str): CourtListener case ID
            
        Returns:
            dict: Case details or None
        """
        return self._make_request(f'clusters/{case_id}/')
    
    def parse_federal_circuit_appeal(self, search_result) -> Optional[FederalCircuitAppeal]:
        """
        Parse CourtListener search result into FederalCircuitAppeal object.
        
        Args:
            search_result (dict): CourtListener search result
            
        Returns:
            FederalCircuitAppeal: Parsed appeal information
        """
        try:
            appeal = FederalCircuitAppeal()
            
            # Basic case information
            appeal.case_name = search_result.get('caseName', '')
            appeal.citation = search_result.get('citation', '')
            
            # Extract case number from various fields
            docket_number = search_result.get('docketNumber', '')
            if docket_number:
                appeal.case_number = docket_number
                appeal.docket_number = docket_number
            
            # Dates
            filing_date_str = search_result.get('dateFiled')
            if filing_date_str:
                try:
                    appeal.filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d')
                except ValueError:
                    pass
            
            decision_date_str = search_result.get('date_filed')  # Sometimes different field name
            if decision_date_str:
                try:
                    appeal.decision_date = datetime.strptime(decision_date_str, '%Y-%m-%d')
                except ValueError:
                    pass
            
            # Judges - try to extract from various fields
            judges = []
            
            # Panel information
            panel = search_result.get('panel', [])
            if isinstance(panel, list):
                judges.extend([judge.get('name', '') for judge in panel if judge.get('name')])
            
            # Author information
            author = search_result.get('author')
            if author and isinstance(author, dict):
                author_name = author.get('name', '')
                if author_name and author_name not in judges:
                    judges.append(author_name)
            
            appeal.judges = judges
            
            # CourtListener specific information
            appeal.courtlistener_id = str(search_result.get('id', ''))
            
            # Build CourtListener URL
            if appeal.courtlistener_id:
                appeal.courtlistener_url = f"https://www.courtlistener.com/opinion/{appeal.courtlistener_id}/"
            
            # Try to determine outcome from summary or other fields
            summary = search_result.get('summary', '')
            if summary:
                appeal.outcome = self._extract_outcome_from_text(summary)
            
            return appeal
            
        except Exception as e:
            logger.error(f"Error parsing Federal Circuit appeal: {e}")
            return None
    
    def _extract_outcome_from_text(self, text) -> Optional[str]:
        """
        Extract case outcome from decision text.
        
        Args:
            text (str): Decision text or summary
            
        Returns:
            str: Extracted outcome or None
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Common outcome patterns
        if 'affirmed' in text_lower:
            return OutcomeType.AFFIRMED.value
        elif 'reversed' in text_lower:
            return OutcomeType.REVERSED.value
        elif 'remanded' in text_lower:
            return OutcomeType.REMANDED.value
        elif 'dismissed' in text_lower:
            return OutcomeType.DISMISSED.value
        elif 'granted' in text_lower:
            return OutcomeType.GRANTED.value
        elif 'denied' in text_lower:
            return OutcomeType.DENIED.value
        
        return None
    
    def find_federal_circuit_appeal(self, ttab_opinion) -> Optional[FederalCircuitAppeal]:
        """
        Find Federal Circuit appeal for a TTAB opinion.
        
        Args:
            ttab_opinion: TTABOpinion object
            
        Returns:
            FederalCircuitAppeal: Found appeal or None
        """
        if not self.enabled:
            return None
        
        # Strategy 1: Search by case number
        case_identifiers = ttab_opinion.get_case_identifiers()
        for case_id in case_identifiers:
            results = self.search_by_case_number(case_id)
            if results:
                # Return the most recent/relevant result
                return self.parse_federal_circuit_appeal(results[0])
        
        # Strategy 2: Search by party names
        party_names = ttab_opinion.get_all_party_names()
        if party_names:
            # Add TTAB-specific terms to help filter results
            additional_terms = ["TTAB", "Trademark Trial and Appeal Board"]
            if ttab_opinion.case_title:
                additional_terms.append(ttab_opinion.case_title)
            
            results = self.search_by_party_names(party_names, additional_terms)
            if results:
                # Look for best match based on party names and dates
                best_match = self._find_best_match(results, ttab_opinion)
                if best_match:
                    return self.parse_federal_circuit_appeal(best_match)
        
        return None
    
    def _find_best_match(self, search_results, ttab_opinion):
        """
        Find the best matching Federal Circuit case from search results.
        
        Args:
            search_results (list): CourtListener search results
            ttab_opinion: TTABOpinion object
            
        Returns:
            dict: Best matching result or None
        """
        if not search_results:
            return None
        
        # Simple scoring system
        best_score = 0
        best_match = None
        
        ttab_party_names = [name.lower() for name in ttab_opinion.get_all_party_names()]
        ttab_date = ttab_opinion.decision_date
        
        for result in search_results[:10]:  # Only check top 10 results
            score = 0
            
            # Check party name matches in case name
            case_name = result.get('caseName', '').lower()
            for party_name in ttab_party_names:
                if party_name in case_name:
                    score += 2
            
            # Check for TTAB mention
            if 'ttab' in case_name or 'trademark trial' in case_name:
                score += 3
            
            # Date proximity (if we have TTAB decision date)
            if ttab_date:
                fc_date_str = result.get('dateFiled')
                if fc_date_str:
                    try:
                        fc_date = datetime.strptime(fc_date_str, '%Y-%m-%d')
                        # Federal Circuit cases should typically be after TTAB decisions
                        if fc_date > ttab_date:
                            days_diff = (fc_date - ttab_date).days
                            if days_diff <= 365:  # Within a year
                                score += 2
                            elif days_diff <= 730:  # Within two years
                                score += 1
                    except ValueError:
                        pass
            
            if score > best_score:
                best_score = score
                best_match = result
        
        # Only return match if it has a reasonable score
        return best_match if best_score >= 3 else None
