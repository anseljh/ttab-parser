"""Unit tests for utility functions."""

import pytest
from datetime import datetime
from pathlib import Path
from src.utils import (
    is_xml_file,
    parse_xml_date,
    clean_text,
    extract_text_from_element,
    find_element_by_tag,
    find_elements_by_tag,
    extract_case_number,
    parse_date,
    has_ttab_decision_code,
    is_opinion_document
)
import xml.etree.ElementTree as ET


class TestFileIdentification:
    """Tests for file identification functions."""
    
    def test_is_xml_file_with_xml_extension(self):
        """Test identification of .xml files."""
        assert is_xml_file(Path("test.xml")) is True
        assert is_xml_file(Path("document.XML")) is True
    
    def test_is_xml_file_with_compressed(self):
        """Test identification of compressed XML files."""
        assert is_xml_file(Path("test.xml.gz")) is True
        assert is_xml_file(Path("test.xml.zip")) is True
    
    def test_is_xml_file_with_non_xml(self):
        """Test non-XML files return False."""
        assert is_xml_file(Path("test.txt")) is False
        assert is_xml_file(Path("document.pdf")) is False
        assert is_xml_file(Path("data.csv")) is False


class TestDateParsing:
    """Tests for date parsing functions."""
    
    def test_parse_xml_date_iso_format(self):
        """Test parsing ISO format dates."""
        result = parse_xml_date("2025-01-15")
        assert result == datetime(2025, 1, 15)
    
    def test_parse_xml_date_yyyymmdd(self):
        """Test parsing YYYYMMDD format."""
        result = parse_xml_date("20250115")
        assert result == datetime(2025, 1, 15)
    
    def test_parse_xml_date_slash_format(self):
        """Test parsing MM/DD/YYYY format."""
        result = parse_xml_date("01/15/2025")
        assert result == datetime(2025, 1, 15)
    
    def test_parse_xml_date_with_time(self):
        """Test parsing date with time."""
        result = parse_xml_date("2025-01-15 14:30:00")
        assert result == datetime(2025, 1, 15, 14, 30, 0)
    
    def test_parse_xml_date_invalid(self):
        """Test parsing invalid date returns None."""
        assert parse_xml_date("not-a-date") is None
        assert parse_xml_date("") is None
        assert parse_xml_date(None) is None
    
    def test_parse_date_yyyymmdd(self):
        """Test parse_date with YYYYMMDD format."""
        result = parse_date("20250115")
        assert result == "2025-01-15"
    
    def test_parse_date_iso_format(self):
        """Test parse_date with ISO format."""
        result = parse_date("2025-01-15")
        assert result == "2025-01-15"
    
    def test_parse_date_slash_format(self):
        """Test parse_date with slash format."""
        result = parse_date("01/15/2025")
        assert result == "2025-01-15"
    
    def test_parse_date_invalid(self):
        """Test parse_date with invalid input."""
        assert parse_date("invalid") is None
        assert parse_date("") is None
        assert parse_date(None) is None


class TestTextCleaning:
    """Tests for text cleaning functions."""
    
    def test_clean_text_removes_extra_whitespace(self):
        """Test cleaning removes extra whitespace."""
        assert clean_text("  hello   world  ") == "hello world"
        assert clean_text("text\n\nwith\n\nnewlines") == "text with newlines"
        assert clean_text("tabs\t\there") == "tabs here"
    
    def test_clean_text_decodes_entities(self):
        """Test cleaning decodes HTML entities."""
        assert clean_text("AT&amp;T") == "AT&T"
        assert clean_text("&lt;test&gt;") == "<test>"
        assert clean_text("&quot;quoted&quot;") == '"quoted"'
        assert clean_text("it&apos;s") == "it's"
    
    def test_clean_text_empty_input(self):
        """Test cleaning empty or None input."""
        assert clean_text("") == ""
        assert clean_text(None) == ""
    
    def test_clean_text_preserves_normal_text(self):
        """Test normal text is preserved."""
        assert clean_text("Normal text here") == "Normal text here"


class TestXMLElementExtraction:
    """Tests for XML element extraction."""
    
    def test_extract_text_from_element(self):
        """Test extracting text from XML element."""
        xml_str = "<root>Hello <child>World</child>!</root>"
        root = ET.fromstring(xml_str)
        assert extract_text_from_element(root) == "Hello World !"
    
    def test_extract_text_from_element_none(self):
        """Test extracting text from None returns empty string."""
        assert extract_text_from_element(None) == ""
    
    def test_extract_text_from_nested_elements(self):
        """Test extracting text from nested elements."""
        xml_str = """<root>
            <level1>Text 1
                <level2>Text 2</level2>
            </level1>
        </root>"""
        root = ET.fromstring(xml_str)
        result = extract_text_from_element(root)
        assert "Text 1" in result
        assert "Text 2" in result
    
    def test_find_element_by_tag(self):
        """Test finding element by tag name."""
        xml_str = "<root><target>Found</target><other>Not this</other></root>"
        root = ET.fromstring(xml_str)
        result = find_element_by_tag(root, "target")
        assert result is not None
        assert result.text == "Found"
    
    def test_find_element_by_tag_case_insensitive(self):
        """Test finding element by tag (case insensitive)."""
        xml_str = "<root><Target>Found</Target></root>"
        root = ET.fromstring(xml_str)
        result = find_element_by_tag(root, "target", case_insensitive=True)
        assert result is not None
        assert result.text == "Found"
    
    def test_find_element_by_tag_not_found(self):
        """Test finding non-existent element returns None."""
        xml_str = "<root><other>Text</other></root>"
        root = ET.fromstring(xml_str)
        result = find_element_by_tag(root, "missing")
        assert result is None
    
    def test_find_elements_by_tag(self):
        """Test finding multiple elements by tag."""
        xml_str = "<root><item>1</item><item>2</item><item>3</item></root>"
        root = ET.fromstring(xml_str)
        results = find_elements_by_tag(root, "item")
        assert len(results) == 3
        assert results[0].text == "1"
        assert results[1].text == "2"
        assert results[2].text == "3"


class TestCaseNumberExtraction:
    """Tests for case number extraction."""
    
    def test_extract_case_number_standard_format(self):
        """Test extracting standard TTAB case numbers."""
        assert extract_case_number("Case No. 91/123456") is not None
        assert extract_case_number("Proceeding No. 91/123456") is not None
    
    def test_extract_case_number_numeric_only(self):
        """Test extracting numeric case numbers."""
        result = extract_case_number("Case 12345678 was filed")
        assert result is not None
        assert "12345678" in result
    
    def test_extract_case_number_not_found(self):
        """Test when no case number is found."""
        assert extract_case_number("No case number here") is None
        assert extract_case_number("") is None
        assert extract_case_number(None) is None
    
    def test_extract_case_number_from_text(self):
        """Test extracting case number from longer text."""
        text = "In the matter of Proceeding No. 91/234567, the Board finds..."
        result = extract_case_number(text)
        assert result is not None
        assert "91/234567" in result


class TestTTABDecisionCodes:
    """Tests for TTAB decision code identification."""
    
    def test_valid_code_in_lower_range(self):
        """Test valid TTAB decision codes 802-849."""
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>802</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is True
        
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>849</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is True
    
    def test_valid_code_in_upper_range(self):
        """Test valid TTAB decision codes 855-894."""
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>855</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is True
        
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>870</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is True
        
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>894</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is True
    
    def test_invalid_codes_850_to_854(self):
        """Test that codes 850-854 are NOT valid TTAB decisions."""
        for code in [850, 851, 852, 853, 854]:
            xml_str = f"""
            <proceeding-entry>
                <prosecution-entry>
                    <code>{code}</code>
                </prosecution-entry>
            </proceeding-entry>
            """
            root = ET.fromstring(xml_str)
            assert has_ttab_decision_code(root) is False
    
    def test_invalid_code_below_range(self):
        """Test codes below 802 are not valid."""
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>801</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is False
        
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>500</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is False
    
    def test_invalid_code_above_range(self):
        """Test codes above 894 are not valid."""
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>895</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is False
        
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>900</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is False
    
    def test_non_numeric_code(self):
        """Test non-numeric codes are skipped."""
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>FINALDEC</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is False
    
    def test_no_prosecution_entry(self):
        """Test documents without prosecution-entry elements."""
        xml_str = """
        <proceeding-entry>
            <case-number>91/123456</case-number>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is False
    
    def test_multiple_prosecution_entries_one_valid(self):
        """Test multiple prosecution entries with one valid code."""
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>500</code>
            </prosecution-entry>
            <prosecution-entry>
                <code>870</code>
            </prosecution-entry>
            <prosecution-entry>
                <code>851</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert has_ttab_decision_code(root) is True
    
    def test_is_opinion_document_uses_decision_codes(self):
        """Test that is_opinion_document uses decision codes as primary check."""
        xml_str = """
        <proceeding-entry>
            <prosecution-entry>
                <code>870</code>
            </prosecution-entry>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert is_opinion_document(root) is True
    
    def test_is_opinion_document_falls_back_to_legacy(self):
        """Test that is_opinion_document falls back to legacy heuristics."""
        xml_str = """
        <proceeding-entry>
            <document-type>Final Opinion</document-type>
        </proceeding-entry>
        """
        root = ET.fromstring(xml_str)
        assert is_opinion_document(root) is True
