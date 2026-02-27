"""
Utility functions for TTAB data processing.

Contains helper functions for XML parsing, data validation,
file handling, and text processing.
"""

import gzip
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import zipfile

logger = logging.getLogger(__name__)


def setup_logging(level=logging.INFO, log_file=None):
    """
    Setup logging configuration.
    
    Args:
        level: Logging level
        log_file (str, optional): Path to log file
    """
    handlers = []
    handlers.append(logging.StreamHandler())
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def is_xml_file(file_path: Path) -> bool:
    """
    Check if file is an XML file (including compressed).
    
    Args:
        file_path (Path): Path to file
        
    Returns:
        bool: True if file appears to be XML
    """
    suffixes = [s.lower() for s in file_path.suffixes]
    
    # Check for .xml, .xml.gz, .xml.zip patterns
    if '.xml' in suffixes:
        return True
    
    # Check for compressed XML files
    if file_path.suffix.lower() in ['.gz', '.zip'] and '.xml' in str(file_path).lower():
        return True
    
    return False


def open_xml_file(file_path: Path):
    """
    Open XML file, handling compression automatically.
    
    Args:
        file_path (Path): Path to XML file
        
    Returns:
        file object: Opened file handle
    """
    if file_path.suffix.lower() == '.gz':
        return gzip.open(file_path, 'rt', encoding='utf-8')
    elif file_path.suffix.lower() == '.zip':
        # For ZIP files, try to find XML file inside
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            xml_files = [name for name in zip_file.namelist() if name.lower().endswith('.xml')]
            if xml_files:
                return zip_file.open(xml_files[0], 'r')
    
    return open(file_path, 'r', encoding='utf-8')


def parse_xml_date(date_str: str) -> Optional[datetime]:
    """
    Parse various date formats found in XML.
    
    Args:
        date_str (str): Date string
        
    Returns:
        datetime: Parsed date or None
    """
    if not date_str:
        return None
    
    # Common date formats in USPTO XML
    date_formats = [
        '%Y-%m-%d',
        '%Y%m%d',
        '%m/%d/%Y',
        '%m-%d-%Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y%m%d%H%M%S'
    ]
    
    # Clean the date string
    date_str = date_str.strip()
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


def clean_text(text: str) -> str:
    """
    Clean and normalize text extracted from XML.
    
    Args:
        text (str): Raw text
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common XML artifacts
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&apos;', "'", text)
    
    return text


def extract_text_from_element(element) -> str:
    """
    Extract all text content from XML element and its children.
    
    Args:
        element: XML element
        
    Returns:
        str: Extracted text
    """
    if element is None:
        return ""
    
    # Get all text content including from child elements
    text_parts = []
    
    if element.text:
        text_parts.append(element.text)
    
    for child in element:
        child_text = extract_text_from_element(child)
        if child_text:
            text_parts.append(child_text)
        
        if child.tail:
            text_parts.append(child.tail)
    
    return clean_text(' '.join(text_parts))


def find_element_by_tag(root, tag_name: str, case_insensitive=True):
    """
    Find first element with given tag name.
    
    Args:
        root: XML root element
        tag_name (str): Tag name to search for
        case_insensitive (bool): Whether to ignore case
        
    Returns:
        XML element or None
    """
    if case_insensitive:
        tag_name = tag_name.lower()
        for elem in root.iter():
            if elem.tag.lower() == tag_name:
                return elem
    else:
        return root.find(f".//{tag_name}")
    
    return None


def find_elements_by_tag(root, tag_name: str, case_insensitive=True):
    """
    Find all elements with given tag name.
    
    Args:
        root: XML root element
        tag_name (str): Tag name to search for
        case_insensitive (bool): Whether to ignore case
        
    Returns:
        list: List of XML elements
    """
    elements = []
    
    if case_insensitive:
        tag_name = tag_name.lower()
        for elem in root.iter():
            if elem.tag.lower() == tag_name:
                elements.append(elem)
    else:
        elements = root.findall(f".//{tag_name}")
    
    return elements


def extract_case_number(text: str) -> Optional[str]:
    """
    Extract case number from text using common patterns.
    
    Args:
        text (str): Text to search
        
    Returns:
        str: Extracted case number or None
    """
    if not text:
        return None
    
    # Common TTAB case number patterns
    patterns = [
        r'\b\d{2}/\d{6}\b',  # Format: 91/123456
        r'\b\d{8}\b',        # Format: 12345678
        r'\bNo\.\s*\d{2}/\d{6}\b',  # Format: No. 91/123456
        r'\bProceeding\s+No\.\s*\d{2}/\d{6}\b',  # Format: Proceeding No. 91/123456
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group().strip()
    
    return None


def has_ttab_decision_code(root) -> bool:
    """
    Check if element contains a TTAB decision based on prosecution-entry codes.
    
    TTAB decisions have prosecution-entry code values:
    - 802 to 849 (inclusive)
    - 855 to 894 (inclusive)
    - EXCLUDING 850 to 854
    
    Args:
        root: XML root element (typically a proceeding-entry)
        
    Returns:
        bool: True if element contains a TTAB decision code
    """
    # Find all prosecution-entry elements
    prosecution_entries = find_elements_by_tag(root, 'prosecution-entry')
    
    for entry in prosecution_entries:
        # Look for code element within prosecution-entry
        code_elem = find_element_by_tag(entry, 'code')
        if code_elem is not None:
            code_text = extract_text_from_element(code_elem)
            if code_text:
                try:
                    code_value = int(code_text.strip())
                    # Check if code is in TTAB decision range
                    # Valid ranges: 802-849 or 855-894
                    if (802 <= code_value <= 849) or (855 <= code_value <= 894):
                        return True
                except ValueError:
                    # Not a numeric code, skip
                    continue
    
    return False


def is_opinion_document(root) -> bool:
    """
    Determine if XML document represents a TTAB opinion/decision.
    
    Primary method: Check prosecution-entry codes (802-849, 855-894)
    Fallback: Use legacy heuristics for documents without prosecution entries
    
    Args:
        root: XML root element
        
    Returns:
        bool: True if document appears to be an opinion
    """
    # PRIMARY: Check for TTAB decision codes in prosecution entries
    if has_ttab_decision_code(root):
        return True
    
    # FALLBACK: Legacy heuristics for documents without prosecution entries
    # Look for opinion-specific elements and content
    opinion_indicators = [
        'opinion',
        'decision',
        'ruling',
        'judgment',
        'order'
    ]
    
    # Check document type or title
    doc_type = extract_text_from_element(find_element_by_tag(root, 'document-type'))
    if doc_type:
        doc_type_lower = doc_type.lower()
        if any(indicator in doc_type_lower for indicator in opinion_indicators):
            return True
    
    # Check for presence of judge information
    judges_elem = find_element_by_tag(root, 'judges')
    if judges_elem is not None or find_element_by_tag(root, 'judge') is not None:
        return True
    
    # Check for outcome/decision language
    content_text = extract_text_from_element(root).lower()
    decision_phrases = [
        'it is ordered',
        'it is decided',
        'we conclude',
        'we hold',
        'judgment for',
        'proceeding is dismissed',
        'opposition is sustained',
        'opposition is denied'
    ]
    
    if any(phrase in content_text for phrase in decision_phrases):
        return True
    
    return False


def extract_party_type(party_element, proceeding_type: str) -> Optional[str]:
    """
    Determine party type from XML element and proceeding context.
    
    Args:
        party_element: XML party element
        proceeding_type (str): Type of proceeding
        
    Returns:
        str: Party type or None
    """
    # Check for official TTAB DTD role-code element first
    role_code_elem = find_element_by_tag(party_element, 'role-code')
    if role_code_elem is not None:
        role_code = extract_text_from_element(role_code_elem).upper()
        if role_code == 'P':  # Plaintiff in official DTD
            # Map to semantic party type based on proceeding
            if proceeding_type == 'opposition':
                return 'opposer'  # In oppositions, plaintiff is typically the opposer
            elif proceeding_type == 'cancellation':
                return 'petitioner'  # In cancellations, plaintiff is typically the petitioner
            else:
                return 'plaintiff'
        elif role_code == 'D':  # Defendant in official DTD
            # Map to semantic party type based on proceeding
            if proceeding_type == 'opposition':
                return 'applicant'  # In oppositions, defendant is typically the applicant
            elif proceeding_type == 'cancellation':
                return 'registrant'  # In cancellations, defendant is typically the registrant
            else:
                return 'defendant'
    
    # Check for explicit party type in element attribute
    party_type = party_element.get('type')
    if party_type:
        return party_type.lower()
    
    # Check element tag name
    tag_name = party_element.tag.lower()
    if 'applicant' in tag_name:
        return 'applicant'
    elif 'registrant' in tag_name:
        return 'registrant'
    elif 'opposer' in tag_name:
        return 'opposer'
    elif 'petitioner' in tag_name:
        return 'petitioner'
    elif 'plaintiff' in tag_name:
        return 'plaintiff'
    elif 'defendant' in tag_name:
        return 'defendant'
    
    # Infer from proceeding type and context
    if proceeding_type == 'opposition':
        # In oppositions, usually applicant vs opposer
        party_role = party_element.get('role', '').lower()
        if 'applicant' in party_role:
            return 'applicant'
        elif 'opposer' in party_role:
            return 'opposer'
    elif proceeding_type == 'cancellation':
        # In cancellations, usually registrant vs petitioner
        party_role = party_element.get('role', '').lower()
        if 'registrant' in party_role:
            return 'registrant'
        elif 'petitioner' in party_role:
            return 'petitioner'
    
    return None


def validate_ttab_opinion(opinion) -> List[str]:
    """
    Validate TTAB opinion data and return list of warnings.
    
    Args:
        opinion: TTABOpinion object
        
    Returns:
        list: List of validation warnings
    """
    warnings = []
    
    if not opinion.case_number and not opinion.proceeding_number:
        warnings.append("No case or proceeding number found")
    
    if not opinion.parties:
        warnings.append("No parties found")
    elif len(opinion.parties) < 2:
        warnings.append("Fewer than 2 parties found (unusual for TTAB case)")
    
    if not opinion.judges:
        warnings.append("No judges found")
    
    if not opinion.outcome:
        warnings.append("No outcome determined")
    
    if not opinion.decision_date and not opinion.filing_date:
        warnings.append("No dates found")
    
    # Check for party type coverage
    party_types = [party.party_type for party in opinion.parties if party.party_type]
    if not party_types:
        warnings.append("No party types identified")
    
    return warnings


def create_progress_bar(current: int, total: int, width: int = 50) -> str:
    """
    Create a simple text progress bar.
    
    Args:
        current (int): Current progress
        total (int): Total items
        width (int): Width of progress bar
        
    Returns:
        str: Progress bar string
    """
    if total == 0:
        percentage = 100
    else:
        percentage = min(100, (current / total) * 100)
    
    filled = int(width * percentage / 100)
    bar = '█' * filled + '░' * (width - filled)
    
    return f"[{bar}] {percentage:6.1f}% ({current:,}/{total:,})"


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse date string into standard format (YYYY-MM-DD).
    Handles TTAB DTD YYYYMMDD format and other common formats.
    
    Args:
        date_str (str): Date string to parse
        
    Returns:
        str: Formatted date or None
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    if not date_str:
        return None
    
    # Handle numeric-only dates first (YYYYMMDD format from TTAB DTD)
    if date_str.isdigit() and len(date_str) == 8:
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            parsed_date = datetime(year, month, day)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    # Try other common date formats
    date_patterns = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%m-%d-%Y',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%B %d, %Y',
        '%b %d, %Y',
        '%Y%m%d'  # YYYYMMDD format
    ]
    
    for pattern in date_patterns:
        try:
            parsed_date = datetime.strptime(date_str, pattern)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None
