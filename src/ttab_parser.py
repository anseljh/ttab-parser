#!/usr/bin/env python3
"""
TTAB XML Parser

Parses TTAB XML files from a specified directory and extracts opinion data
including parties, judges, outcomes, and Federal Circuit appeal information.
"""

import argparse
import csv
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Generator
import glob
import traceback

from src.models import (
    TTABOpinion, Party, Judge, Attorney, TrademarkMark, FederalCircuitAppeal,
    OutcomeType, PartyType, ProceedingType, ProcessingStats
)
from src.courtlistener_client import CourtListenerClient
from src.utils import (
    setup_logging, is_xml_file, open_xml_file, parse_xml_date, clean_text,
    extract_text_from_element, find_element_by_tag, find_elements_by_tag,
    extract_case_number, is_opinion_document, extract_party_type,
    validate_ttab_opinion, create_progress_bar
)

logger = logging.getLogger(__name__)


class TTABParser:
    """Parses TTAB XML files and extracts opinion data."""
    
    def __init__(self, enable_courtlistener=True):
        """
        Initialize the parser.
        
        Args:
            enable_courtlistener (bool): Whether to enable Federal Circuit appeal lookup
        """
        self.courtlistener_client = None
        if enable_courtlistener:
            self.courtlistener_client = CourtListenerClient()
        
        self.stats = ProcessingStats()
    
    def parse_directory(self, input_dir: Path) -> Generator[TTABOpinion, None, None]:
        """
        Parse all XML files in directory and yield opinion objects.
        
        Args:
            input_dir (Path): Directory containing XML files
            
        Yields:
            TTABOpinion: Parsed opinion objects
        """
        if not input_dir.exists():
            raise FileNotFoundError(f"Directory not found: {input_dir}")
        
        # Find all XML files (including compressed)
        xml_files = []
        for pattern in ['*.xml', '*.xml.gz', '*.xml.zip']:
            xml_files.extend(glob.glob(str(input_dir / pattern)))
        
        xml_files = [Path(f) for f in xml_files if is_xml_file(Path(f))]
        
        if not xml_files:
            logger.warning(f"No XML files found in {input_dir}")
            return
        
        logger.info(f"Found {len(xml_files)} XML files to process")
        self.stats.start_time = datetime.now()
        
        for i, xml_file in enumerate(xml_files, 1):
            logger.info(f"Processing file {i}/{len(xml_files)}: {xml_file.name}")
            
            try:
                opinions = list(self.parse_file(xml_file))
                
                for opinion in opinions:
                    # Look up Federal Circuit appeal if enabled
                    if self.courtlistener_client and self.courtlistener_client.enabled:
                        try:
                            fc_appeal = self.courtlistener_client.find_federal_circuit_appeal(opinion)
                            if fc_appeal:
                                opinion.federal_circuit_appeal = fc_appeal
                                opinion.appeal_indicated = True
                                self.stats.federal_circuit_appeals_found += 1
                                logger.info(f"Found Federal Circuit appeal for case {opinion.case_number}")
                        except Exception as e:
                            logger.error(f"Error looking up Federal Circuit appeal: {e}")
                    
                    yield opinion
                
                self.stats.total_files_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing file {xml_file}: {e}")
                logger.debug(traceback.format_exc())
                self.stats.errors += 1
        
        self.stats.end_time = datetime.now()
    
    def parse_file(self, file_path: Path) -> Generator[TTABOpinion, None, None]:
        """
        Parse single XML file and yield opinion objects.
        
        Args:
            file_path (Path): Path to XML file
            
        Yields:
            TTABOpinion: Parsed opinion objects
        """
        logger.debug(f"Parsing file: {file_path}")
        
        try:
            with open_xml_file(file_path) as f:
                # Parse XML with iterparse for memory efficiency
                context = ET.iterparse(f, events=('start', 'end'))
                context = iter(context)
                event, root = next(context)
                
                current_element = None
                
                for event, elem in context:
                    if event == 'start':
                        continue
                    
                    # Look for official TTAB DTD elements or generic document elements
                    if elem.tag.lower() in ['proceeding-entry', 'document', 'proceeding', 'case', 'filing']:
                        self.stats.total_documents_processed += 1
                        
                        # Check if this is an opinion document
                        if is_opinion_document(elem):
                            self.stats.opinions_found += 1
                            
                            try:
                                opinion = self.parse_opinion_element(elem, file_path)
                                if opinion:
                                    self.stats.opinions_parsed += 1
                                    yield opinion
                            except Exception as e:
                                logger.error(f"Error parsing opinion in {file_path}: {e}")
                                logger.debug(traceback.format_exc())
                                self.stats.errors += 1
                        
                        # Clear element to save memory
                        elem.clear()
                        # Note: getparent() is lxml-specific, skip for xml.etree.ElementTree
                
                root.clear()
                
        except ET.ParseError as e:
            logger.error(f"XML parse error in {file_path}: {e}")
            self.stats.errors += 1
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            logger.debug(traceback.format_exc())
            self.stats.errors += 1
    
    def parse_opinion_element(self, elem, source_file: Path) -> Optional[TTABOpinion]:
        """
        Parse XML element representing an opinion.
        
        Args:
            elem: XML element
            source_file (Path): Source file path
            
        Returns:
            TTABOpinion: Parsed opinion or None
        """
        opinion = TTABOpinion()
        opinion.source_file = str(source_file)
        
        try:
            # Extract case identification
            self._extract_case_info(elem, opinion)
            
            # Extract dates
            self._extract_dates(elem, opinion)
            
            # Extract parties
            self._extract_parties(elem, opinion)
            
            # Extract judges
            self._extract_judges(elem, opinion)
            
            # Extract outcome
            self._extract_outcome(elem, opinion)
            
            # Extract trademark information
            self._extract_trademark_info(elem, opinion)
            
            # Extract legal representation
            self._extract_legal_representation(elem, opinion)
            
            # Check for appeal indicators
            self._check_appeal_indicators(elem, opinion)
            
            # Validate opinion
            warnings = validate_ttab_opinion(opinion)
            if warnings:
                logger.debug(f"Validation warnings for {opinion.case_number}: {', '.join(warnings)}")
            
            return opinion
            
        except Exception as e:
            logger.error(f"Error parsing opinion element: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def _extract_case_info(self, elem, opinion: TTABOpinion):
        """Extract case identification information."""
        
        # Try various fields for case number (official DTD uses 'number')
        case_number_fields = [
            'number',  # Official TTAB DTD element
            'case-number', 'proceeding-number', 'case_number',
            'proceeding_number', 'docket-number', 'docket_number'
        ]
        
        for field in case_number_fields:
            case_elem = find_element_by_tag(elem, field)
            if case_elem is not None:
                case_number = extract_text_from_element(case_elem)
                if case_number:
                    if 'proceeding' in field:
                        opinion.proceeding_number = case_number
                    else:
                        opinion.case_number = case_number
                    break
        
        # Extract from text if not found in structured fields
        if not opinion.case_number and not opinion.proceeding_number:
            full_text = extract_text_from_element(elem)
            extracted_number = extract_case_number(full_text)
            if extracted_number:
                opinion.case_number = extracted_number
        
        # Extract case title
        title_fields = ['title', 'case-title', 'name', 'caption']
        for field in title_fields:
            title_elem = find_element_by_tag(elem, field)
            if title_elem is not None:
                opinion.case_title = extract_text_from_element(title_elem)
                break

        # Extract proceeding type using official DTD mapping
        type_fields = ['type-code', 'type', 'proceeding-type', 'case-type']
        for field in type_fields:
            type_elem = find_element_by_tag(elem, field)
            if type_elem is not None:
                proc_type = extract_text_from_element(type_elem).upper()
                # Official TTAB DTD type codes
                if proc_type == 'OPP' or 'opposition' in proc_type.lower():
                    opinion.proceeding_type = ProceedingType.OPPOSITION
                elif proc_type == 'CAN' or 'cancellation' in proc_type.lower():
                    opinion.proceeding_type = ProceedingType.CANCELLATION
                elif proc_type == 'EXA' or 'appeal' in proc_type.lower():
                    opinion.proceeding_type = ProceedingType.APPEAL
                elif proc_type == 'CNU' or 'concurrent' in proc_type.lower():
                    opinion.proceeding_type = ProceedingType.EXPUNGEMENT  # Map to closest type
                elif 'expungement' in proc_type.lower():
                    opinion.proceeding_type = ProceedingType.EXPUNGEMENT
                elif 'reexamination' in proc_type.lower():
                    opinion.proceeding_type = ProceedingType.REEXAMINATION
                break
        
        # Infer proceeding type from case number if not found
        if not opinion.proceeding_type and opinion.case_number:
            case_num = opinion.case_number.strip()
            if case_num.startswith('91'):
                opinion.proceeding_type = ProceedingType.OPPOSITION
            elif case_num.startswith('92'):
                opinion.proceeding_type = ProceedingType.CANCELLATION
            elif case_num.startswith(('70', '71', '72', '73', '74')):
                opinion.proceeding_type = ProceedingType.APPEAL
    
    def _extract_dates(self, elem, opinion: TTABOpinion):
        """Extract filing and decision dates."""
        
        # Filing date (official DTD uses 'filing-date')
        filing_date_fields = ['filing-date', 'filed-date', 'file-date', 'date-filed']
        for field in filing_date_fields:
            date_elem = find_element_by_tag(elem, field)
            if date_elem is not None:
                date_str = extract_text_from_element(date_elem)
                opinion.filing_date = parse_xml_date(date_str)
                if opinion.filing_date:
                    break

        # Decision date
        decision_date_fields = ['decision-date', 'decided-date', 'date-decided', 'judgment-date']
        for field in decision_date_fields:
            date_elem = find_element_by_tag(elem, field)
            if date_elem is not None:
                date_str = extract_text_from_element(date_elem)
                opinion.decision_date = parse_xml_date(date_str)
                if opinion.decision_date:
                    break
        
        # Also check prosecution history for decision events in official DTD
        if not opinion.decision_date:
            prosecution_history = find_element_by_tag(elem, 'prosecution-history')
            if prosecution_history:
                events = find_elements_by_tag(prosecution_history, 'event')
                for event in events:
                    event_code = extract_text_from_element(find_element_by_tag(event, 'event-code'))
                    if event_code and 'FINALDEC' in event_code.upper():
                        event_date = extract_text_from_element(find_element_by_tag(event, 'event-date'))
                        if event_date:
                            opinion.decision_date = parse_xml_date(event_date)
                            break
    
    def _extract_parties(self, elem, opinion: TTABOpinion):
        """Extract party information."""
        
        # Find parties section (official DTD uses 'party-information')
        parties_sections = find_elements_by_tag(elem, 'party-information')
        if not parties_sections:
            parties_sections = find_elements_by_tag(elem, 'parties')
        if not parties_sections:
            parties_sections = [elem]  # Use root element if no parties section
        
        for parties_section in parties_sections:
            # Find individual party elements
            party_elements = []
            
            # Common party element names
            party_tags = [
                'party', 'applicant', 'registrant', 'opposer', 'petitioner',
                'plaintiff', 'defendant', 'participant'
            ]
            
            for tag in party_tags:
                party_elements.extend(find_elements_by_tag(parties_section, tag))
            
            for party_elem in party_elements:
                party = self._parse_party_element(party_elem, opinion.proceeding_type)
                if party and party.name:
                    opinion.parties.append(party)
    
    def _parse_party_element(self, party_elem, proceeding_type) -> Optional[Party]:
        """Parse individual party element."""
        
        party = Party()
        
        # Extract party name from the direct <name>/<party-name>/<entity-name>
        # child of the party element.  We search only direct children (not the
        # full subtree) because <proceeding-address> also contains a <name>
        # element (the attorney name) and an iter()-based deep search would
        # return that instead when the party's own <name> comes later in the
        # element order.
        name_fields = ['name', 'party-name', 'entity-name']
        for field in name_fields:
            name_elem = next(
                (c for c in party_elem if c.tag.lower() == field), None
            )
            if name_elem is not None:
                party.name = extract_text_from_element(name_elem)
                break

        if not party.name:
            return None
        
        # Clean party name
        party.name = clean_text(party.name)
        
        # Determine party type using official DTD role-code mapping
        party_type_str = extract_party_type(party_elem, proceeding_type.value if proceeding_type else '')
        if party_type_str:
            try:
                party.party_type = PartyType(party_type_str.upper())
            except ValueError:
                # Try common mappings
                type_mappings = {
                    'applicant': PartyType.APPLICANT,
                    'registrant': PartyType.REGISTRANT,
                    'opposer': PartyType.OPPOSER,
                    'petitioner': PartyType.PETITIONER,
                    'plaintiff': PartyType.PLAINTIFF,
                    'defendant': PartyType.DEFENDANT
                }
                if party_type_str.lower() in type_mappings:
                    party.party_type = type_mappings[party_type_str.lower()]
                else:
                    logger.debug(f"Unknown party type: {party_type_str}")
        
        # Extract address
        address_fields = ['address', 'party-address']
        for field in address_fields:
            addr_elem = find_element_by_tag(party_elem, field)
            if addr_elem is not None:
                party.address = extract_text_from_element(addr_elem)
                break

        # Extract country
        country_fields = ['country', 'country-code']
        for field in country_fields:
            country_elem = find_element_by_tag(party_elem, field)
            if country_elem is not None:
                party.country = extract_text_from_element(country_elem)
                break
        
        # Extract attorneys
        attorney_elements = find_elements_by_tag(party_elem, 'attorney')
        for attorney_elem in attorney_elements:
            attorney = self._parse_attorney_element(attorney_elem)
            if attorney:
                party.attorneys.append(attorney)
        
        return party
    
    def _parse_attorney_element(self, attorney_elem) -> Optional[Attorney]:
        """Parse attorney element."""
        
        attorney = Attorney()
        
        # Extract attorney name
        name_fields = ['name', 'attorney-name']
        for field in name_fields:
            name_elem = find_element_by_tag(attorney_elem, field)
            if name_elem is not None:
                attorney.name = extract_text_from_element(name_elem)
                break

        if not attorney.name:
            return None

        # Extract registration number
        reg_fields = ['registration-number', 'reg-number', 'bar-number']
        for field in reg_fields:
            reg_elem = find_element_by_tag(attorney_elem, field)
            if reg_elem is not None:
                attorney.registration_number = extract_text_from_element(reg_elem)
                break

        # Extract firm
        firm_fields = ['firm', 'law-firm', 'firm-name']
        for field in firm_fields:
            firm_elem = find_element_by_tag(attorney_elem, field)
            if firm_elem is not None:
                attorney.firm = extract_text_from_element(firm_elem)
                break
        
        # Extract contact info
        attorney.address = extract_text_from_element(find_element_by_tag(attorney_elem, 'address'))
        attorney.phone = extract_text_from_element(find_element_by_tag(attorney_elem, 'phone'))
        attorney.email = extract_text_from_element(find_element_by_tag(attorney_elem, 'email'))
        
        return attorney
    
    def _extract_judges(self, elem, opinion: TTABOpinion):
        """Extract judge information."""
        
        # Find judges section
        judge_sections = find_elements_by_tag(elem, 'judges')
        if not judge_sections:
            judge_sections = find_elements_by_tag(elem, 'panel')
        
        if not judge_sections:
            # Look for individual judge elements
            judge_elements = find_elements_by_tag(elem, 'judge')
        else:
            judge_elements = []
            for section in judge_sections:
                judge_elements.extend(find_elements_by_tag(section, 'judge'))
        
        for judge_elem in judge_elements:
            judge = self._parse_judge_element(judge_elem)
            if judge:
                opinion.judges.append(judge)
        
        # If no structured judges found, try to extract from text
        if not opinion.judges:
            self._extract_judges_from_text(elem, opinion)
    
    def _parse_judge_element(self, judge_elem) -> Optional[Judge]:
        """Parse judge element."""
        
        judge = Judge()
        
        # Extract judge name
        name_fields = ['name', 'judge-name']
        for field in name_fields:
            name_elem = find_element_by_tag(judge_elem, field)
            if name_elem is not None:
                judge.name = extract_text_from_element(name_elem)
                break

        if not judge.name:
            return None
        
        # Clean judge name
        judge.name = clean_text(judge.name)
        
        # Extract title and role
        judge.title = extract_text_from_element(find_element_by_tag(judge_elem, 'title'))
        judge.role = extract_text_from_element(find_element_by_tag(judge_elem, 'role'))
        
        return judge
    
    def _extract_judges_from_text(self, elem, opinion: TTABOpinion):
        """Extract judge names from decision text."""
        
        content = extract_text_from_element(elem)
        
        # Common patterns for judge names in TTAB opinions
        judge_patterns = [
            r'Administrative Trademark Judge\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'Judge\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'Before\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*)',
        ]
        
        for pattern in judge_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Split multiple judges if separated by commas
                judge_names = [name.strip() for name in match.split(',')]
                for judge_name in judge_names:
                    if judge_name and len(judge_name) > 3:
                        judge = Judge()
                        judge.name = clean_text(judge_name)
                        judge.title = "Administrative Trademark Judge"
                        opinion.judges.append(judge)
    
    def _extract_outcome(self, elem, opinion: TTABOpinion):
        """Extract case outcome."""
        
        # Look for structured outcome
        outcome_fields = ['outcome', 'decision', 'ruling', 'judgment', 'disposition']
        for field in outcome_fields:
            outcome_elem = find_element_by_tag(elem, field)
            if outcome_elem is not None:
                outcome_text = extract_text_from_element(outcome_elem).lower()
                opinion.outcome = self._parse_outcome_text(outcome_text)
                opinion.outcome_description = outcome_text
                break
        
        # Extract from decision text if not found
        if not opinion.outcome:
            content = extract_text_from_element(elem).lower()
            opinion.outcome = self._parse_outcome_text(content)
            
            # Extract outcome description from key sentences
            outcome_sentences = []
            sentences = content.split('.')
            for sentence in sentences:
                if any(word in sentence for word in ['granted', 'denied', 'dismissed', 'sustained']):
                    outcome_sentences.append(sentence.strip())
            
            if outcome_sentences:
                opinion.outcome_description = '. '.join(outcome_sentences[:3])  # Take first 3 relevant sentences
    
    def _parse_outcome_text(self, text: str) -> Optional[OutcomeType]:
        """Parse outcome from text."""
        
        text = text.lower()
        
        # Opposition outcomes
        if 'opposition is sustained' in text or 'sustain the opposition' in text:
            return OutcomeType.SUSTAINED
        elif 'opposition is denied' in text or 'deny the opposition' in text:
            return OutcomeType.DENIED
        elif 'opposition is dismissed' in text or 'dismiss the opposition' in text:
            return OutcomeType.DISMISSED
        
        # Cancellation outcomes
        elif 'cancellation is granted' in text or 'grant the petition' in text:
            return OutcomeType.GRANTED
        elif 'cancellation is denied' in text or 'deny the petition' in text:
            return OutcomeType.DENIED
        elif 'cancellation is dismissed' in text or 'dismiss the petition' in text:
            return OutcomeType.DISMISSED
        
        # Appeal outcomes
        elif 'reversed' in text:
            return OutcomeType.REVERSED
        elif 'affirmed' in text:
            return OutcomeType.AFFIRMED
        elif 'remanded' in text:
            return OutcomeType.REMANDED
        
        # Settlement
        elif 'settled' in text or 'settlement' in text:
            return OutcomeType.SETTLED
        elif 'withdrawn' in text:
            return OutcomeType.WITHDRAWN
        
        # General outcomes
        elif 'granted' in text:
            return OutcomeType.GRANTED
        elif 'denied' in text:
            return OutcomeType.DENIED
        elif 'dismissed' in text:
            return OutcomeType.DISMISSED
        
        return None
    
    def _extract_trademark_info(self, elem, opinion: TTABOpinion):
        """Extract trademark mark information."""
        
        # Find trademark/mark elements
        mark_sections = find_elements_by_tag(elem, 'trademarks')
        if not mark_sections:
            mark_sections = find_elements_by_tag(elem, 'marks')
        
        if not mark_sections:
            mark_elements = find_elements_by_tag(elem, 'trademark')
            mark_elements.extend(find_elements_by_tag(elem, 'mark'))
        else:
            mark_elements = []
            for section in mark_sections:
                mark_elements.extend(find_elements_by_tag(section, 'trademark'))
                mark_elements.extend(find_elements_by_tag(section, 'mark'))
        
        for mark_elem in mark_elements:
            mark = self._parse_trademark_element(mark_elem)
            if mark:
                opinion.subject_marks.append(mark)
    
    def _parse_trademark_element(self, mark_elem) -> Optional[TrademarkMark]:
        """Parse trademark element."""
        
        mark = TrademarkMark()
        
        # Extract mark text
        text_fields = ['mark-text', 'text', 'mark']
        for field in text_fields:
            text_elem = find_element_by_tag(mark_elem, field)
            if text_elem is not None:
                mark.mark_text = extract_text_from_element(text_elem)
                break
        
        if not mark.mark_text:
            mark.mark_text = extract_text_from_element(mark_elem)
        
        # Extract registration/application numbers
        mark.registration_number = extract_text_from_element(find_element_by_tag(mark_elem, 'registration-number'))
        mark.application_number = extract_text_from_element(find_element_by_tag(mark_elem, 'application-number'))
        
        # Extract description and other info
        mark.mark_description = extract_text_from_element(find_element_by_tag(mark_elem, 'description'))
        mark.mark_type = extract_text_from_element(find_element_by_tag(mark_elem, 'type'))
        mark.goods_services = extract_text_from_element(find_element_by_tag(mark_elem, 'goods-services'))
        
        # Extract classes
        class_elements = find_elements_by_tag(mark_elem, 'class')
        for class_elem in class_elements:
            class_text = extract_text_from_element(class_elem)
            if class_text:
                mark.classes.append(class_text)
        
        return mark if mark.mark_text or mark.registration_number or mark.application_number else None
    
    def _extract_legal_representation(self, elem, opinion: TTABOpinion):
        """Extract legal representation summary."""
        
        # Collect all attorneys from parties
        all_attorneys = []
        law_firms = set()
        
        for party in opinion.parties:
            for attorney in party.attorneys:
                all_attorneys.append(attorney)
                if attorney.firm:
                    law_firms.add(attorney.firm)
        
        opinion.all_attorneys = all_attorneys
        opinion.law_firms = list(law_firms)
    
    def _check_appeal_indicators(self, elem, opinion: TTABOpinion):
        """Check for Federal Circuit appeal indicators."""
        
        content = extract_text_from_element(elem).lower()
        
        appeal_indicators = [
            'federal circuit',
            'court of appeals',
            'appeal to the federal circuit',
            'notice of appeal',
            'appeal filed',
            'appealed to'
        ]
        
        for indicator in appeal_indicators:
            if indicator in content:
                opinion.appeal_indicated = True
                break


def export_to_csv(opinions: List[TTABOpinion], output_file: Path):
    """
    Export opinions to CSV file.
    
    Args:
        opinions (list): List of TTABOpinion objects
        output_file (Path): Output CSV file path
    """
    if not opinions:
        logger.warning("No opinions to export")
        return
    
    logger.info(f"Exporting {len(opinions)} opinions to CSV: {output_file}")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        headers = TTABOpinion.get_csv_headers()
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        
        writer.writeheader()
        
        for opinion in opinions:
            try:
                row = opinion.to_csv_row()
                writer.writerow(row)
            except Exception as e:
                logger.error(f"Error writing CSV row for case {opinion.case_number}: {e}")


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Parse TTAB XML files and extract opinion data"
    )
    
    parser.add_argument(
        "input_dir",
        nargs='?',
        default="ttab_data",
        help="Directory containing TTAB XML files (default: ttab_data)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="ttab_opinions.csv",
        help="Output CSV file (default: ttab_opinions.csv)"
    )
    
    parser.add_argument(
        "--no-courtlistener",
        action="store_true",
        help="Disable Federal Circuit appeal lookup via CourtListener"
    )
    
    parser.add_argument(
        "--log-file",
        help="Path to log file (default: log to console only)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of opinions to process (for testing)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level, log_file=args.log_file)
    
    try:
        input_dir = Path(args.input_dir)
        output_file = Path(args.output)
        
        # Create parser
        enable_courtlistener = not args.no_courtlistener
        parser = TTABParser(enable_courtlistener=enable_courtlistener)
        
        # Process files
        logger.info(f"Starting TTAB XML parsing from: {input_dir}")
        if enable_courtlistener:
            logger.info("Federal Circuit appeal lookup enabled")
        else:
            logger.info("Federal Circuit appeal lookup disabled")
        
        opinions = []
        opinion_count = 0
        
        for opinion in parser.parse_directory(input_dir):
            opinions.append(opinion)
            opinion_count += 1
            
            # Show progress
            if opinion_count % 10 == 0:
                logger.info(f"Processed {opinion_count} opinions...")
            
            # Check limit
            if args.limit and opinion_count >= args.limit:
                logger.info(f"Reached limit of {args.limit} opinions")
                break
        
        # Export results
        if opinions:
            export_to_csv(opinions, output_file)
            logger.info(f"Export completed: {output_file}")
        else:
            logger.warning("No opinions found to export")

        # DB persistence (skipped if no database URL is configured)
        import src.settings as _settings_mod
        db_url = _settings_mod.get("database", "url")
        if db_url:
            from src.database import get_session, init_db
            from src.persist import upsert_opinion
            try:
                init_db()
                session = get_session()
                upserted = 0
                try:
                    for opinion in opinions:
                        upsert_opinion(session, opinion)
                        upserted += 1
                        if upserted % 100 == 0:
                            session.commit()
                    session.commit()
                    logger.info(f"Upserted {upserted} opinion(s) to database")
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"Database write failed (CSV output unaffected): {e}")
        else:
            logger.debug("No database URL configured — skipping DB write")

        # Print statistics
        logger.info("=== Processing Statistics ===")
        logger.info(parser.stats.summary())
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
