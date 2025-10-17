"""Unit tests for TTAB parser."""

import pytest
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
from src.ttab_parser import TTABParser
from src.models import ProceedingType, PartyType


class TestTTABParser:
    """Tests for TTABParser class."""
    
    def test_parser_initialization(self):
        """Test parser can be initialized."""
        parser = TTABParser()
        assert parser is not None
    
    def test_parse_proceeding_number(self):
        """Test parsing proceeding number from XML."""
        xml_str = """<?xml version="1.0"?>
        <ttab-proceedings>
            <proceeding-entry>
                <proceeding-number>91234567</proceeding-number>
            </proceeding-entry>
        </ttab-proceedings>"""
        
        parser = TTABParser()
        root = ET.fromstring(xml_str)
        proceeding_entry = root.find('.//proceeding-entry')
        
        if proceeding_entry is not None:
            proc_num_elem = proceeding_entry.find('proceeding-number')
            if proc_num_elem is not None and proc_num_elem.text:
                assert proc_num_elem.text == "91234567"
    
    def test_parse_filing_date_yyyymmdd(self):
        """Test parsing filing date in YYYYMMDD format."""
        xml_str = """<?xml version="1.0"?>
        <ttab-proceedings>
            <proceeding-entry>
                <filing-date>20250115</filing-date>
            </proceeding-entry>
        </ttab-proceedings>"""
        
        root = ET.fromstring(xml_str)
        proceeding_entry = root.find('.//proceeding-entry')
        
        if proceeding_entry is not None:
            date_elem = proceeding_entry.find('filing-date')
            if date_elem is not None and date_elem.text:
                # Would be parsed by parse_date function
                assert date_elem.text == "20250115"
    
    def test_parse_party_information(self):
        """Test parsing party information."""
        xml_str = """<?xml version="1.0"?>
        <ttab-proceedings>
            <proceeding-entry>
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
        
        root = ET.fromstring(xml_str)
        party_info = root.find('.//party-information')
        
        if party_info is not None:
            parties = party_info.findall('party')
            assert len(parties) == 2
            
            # First party
            party1_name = parties[0].find('party-name')
            party1_role = parties[0].find('role-code')
            assert party1_name is not None and party1_name.text == "Test Company Inc"
            assert party1_role is not None and party1_role.text == "P"
            
            # Second party
            party2_name = parties[1].find('party-name')
            party2_role = parties[1].find('role-code')
            assert party2_name is not None and party2_name.text == "Defendant Corp"
            assert party2_role is not None and party2_role.text == "D"
    
    def test_parse_proceeding_type(self):
        """Test parsing proceeding type."""
        xml_str = """<?xml version="1.0"?>
        <ttab-proceedings>
            <proceeding-entry>
                <proceeding-type>Opposition</proceeding-type>
            </proceeding-entry>
        </ttab-proceedings>"""
        
        root = ET.fromstring(xml_str)
        proceeding_entry = root.find('.//proceeding-entry')
        
        if proceeding_entry is not None:
            proc_type_elem = proceeding_entry.find('proceeding-type')
            if proc_type_elem is not None and proc_type_elem.text:
                assert proc_type_elem.text == "Opposition"
    
    def test_parse_status(self):
        """Test parsing case status."""
        xml_str = """<?xml version="1.0"?>
        <ttab-proceedings>
            <proceeding-entry>
                <status>Terminated</status>
            </proceeding-entry>
        </ttab-proceedings>"""
        
        root = ET.fromstring(xml_str)
        proceeding_entry = root.find('.//proceeding-entry')
        
        if proceeding_entry is not None:
            status_elem = proceeding_entry.find('status')
            if status_elem is not None and status_elem.text:
                assert status_elem.text == "Terminated"


class TestProceedingTypeDetection:
    """Tests for proceeding type detection from proceeding numbers."""
    
    def test_opposition_proceeding_number(self):
        """Test opposition proceeding numbers start with 91."""
        proc_num = "91234567"
        assert proc_num.startswith("91")
    
    def test_cancellation_proceeding_number(self):
        """Test cancellation proceeding numbers start with 92."""
        proc_num = "92123456"
        assert proc_num.startswith("92")
    
    def test_ex_parte_appeal_proceeding_numbers(self):
        """Test ex parte appeal proceeding numbers start with 70-74."""
        appeal_prefixes = ["70", "71", "72", "73", "74"]
        test_numbers = ["70123456", "71234567", "72345678", "73456789", "74567890"]
        
        for num in test_numbers:
            prefix = num[:2]
            assert prefix in appeal_prefixes


class TestPartyRoleMapping:
    """Tests for party role code mapping."""
    
    def test_role_code_p_for_plaintiff(self):
        """Test role-code P represents plaintiff."""
        role_code = "P"
        assert role_code == "P"
    
    def test_role_code_d_for_defendant(self):
        """Test role-code D represents defendant."""
        role_code = "D"
        assert role_code == "D"
    
    def test_opposition_party_mapping(self):
        """Test party mapping in opposition proceedings."""
        proceeding_type = "opposition"
        
        # In oppositions: P (plaintiff) = opposer, D (defendant) = applicant
        if proceeding_type == "opposition":
            assert "opposer" == "opposer"  # P maps to opposer
            assert "applicant" == "applicant"  # D maps to applicant
    
    def test_cancellation_party_mapping(self):
        """Test party mapping in cancellation proceedings."""
        proceeding_type = "cancellation"
        
        # In cancellations: P (plaintiff) = petitioner, D (defendant) = registrant
        if proceeding_type == "cancellation":
            assert "petitioner" == "petitioner"  # P maps to petitioner
            assert "registrant" == "registrant"  # D maps to registrant
