"""
Data models for TTAB opinion analysis.

Defines the structure for extracted data including opinions, parties, judges,
outcomes, trademark marks, legal representation, and Federal Circuit appeals.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class OutcomeType(Enum):
    """Possible case outcomes."""
    GRANTED = "granted"
    DENIED = "denied"
    DISMISSED = "dismissed"
    SUSTAINED = "sustained"
    REVERSED = "reversed"
    AFFIRMED = "affirmed"
    REMANDED = "remanded"
    SETTLED = "settled"
    WITHDRAWN = "withdrawn"
    UNKNOWN = "unknown"


class PartyType(Enum):
    """Types of parties in TTAB proceedings."""
    APPLICANT = "applicant"
    REGISTRANT = "registrant"
    OPPOSER = "opposer"
    PETITIONER = "petitioner"
    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"


class ProceedingType(Enum):
    """Types of TTAB proceedings."""
    OPPOSITION = "opposition"
    CANCELLATION = "cancellation"
    APPEAL = "appeal"
    EXPUNGEMENT = "expungement"
    REEXAMINATION = "reexamination"


@dataclass
class TrademarkMark:
    """Represents a trademark mark mentioned in the case."""
    mark_text: Optional[str] = None
    mark_description: Optional[str] = None
    registration_number: Optional[str] = None
    application_number: Optional[str] = None
    mark_type: Optional[str] = None  # word, design, composite, etc.
    goods_services: Optional[str] = None
    classes: List[str] = field(default_factory=list)


@dataclass
class Attorney:
    """Represents an attorney in the case."""
    name: Optional[str] = None
    registration_number: Optional[str] = None
    firm: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class Party:
    """Represents a party in the TTAB proceeding."""
    name: Optional[str] = None
    party_type: Optional[PartyType] = None
    address: Optional[str] = None
    country: Optional[str] = None
    attorneys: List[Attorney] = field(default_factory=list)
    trademark_marks: List[TrademarkMark] = field(default_factory=list)


@dataclass
class Judge:
    """Represents a TTAB judge."""
    name: Optional[str] = None
    title: Optional[str] = None
    role: Optional[str] = None  # presiding, panel member, etc.


@dataclass
class FederalCircuitAppeal:
    """Represents a Federal Circuit appeal of a TTAB case."""
    case_number: Optional[str] = None
    case_name: Optional[str] = None
    filing_date: Optional[datetime] = None
    decision_date: Optional[datetime] = None
    outcome: Optional[str] = None
    judges: List[str] = field(default_factory=list)
    citation: Optional[str] = None
    courtlistener_url: Optional[str] = None
    courtlistener_id: Optional[str] = None
    docket_number: Optional[str] = None
    appeal_outcome: Optional[OutcomeType] = None


@dataclass
class TTABOpinion:
    """Represents a TTAB opinion with all extracted data."""
    
    # Case identification
    case_number: Optional[str] = None
    proceeding_number: Optional[str] = None
    proceeding_type: Optional[ProceedingType] = None
    case_title: Optional[str] = None
    
    # Dates
    filing_date: Optional[datetime] = None
    decision_date: Optional[datetime] = None
    
    # Parties
    parties: List[Party] = field(default_factory=list)
    
    # Judges
    judges: List[Judge] = field(default_factory=list)
    
    # Case outcome
    outcome: Optional[OutcomeType] = None
    outcome_description: Optional[str] = None
    winner: Optional[str] = None
    
    # Trademark information
    subject_marks: List[TrademarkMark] = field(default_factory=list)
    
    # Legal representation summary
    all_attorneys: List[Attorney] = field(default_factory=list)
    law_firms: List[str] = field(default_factory=list)
    
    # Federal Circuit appeal information
    federal_circuit_appeal: Optional[FederalCircuitAppeal] = None
    appeal_indicated: bool = False
    
    # Source information
    source_file: Optional[str] = None
    xml_source: Optional[str] = None
    
    # Raw extracted data for debugging
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def get_applicant_registrant(self) -> Optional[Party]:
        """Get the applicant or registrant party."""
        for party in self.parties:
            if party.party_type in [PartyType.APPLICANT, PartyType.REGISTRANT]:
                return party
        return None
    
    def get_opposer_petitioner(self) -> Optional[Party]:
        """Get the opposer or petitioner party."""
        for party in self.parties:
            if party.party_type in [PartyType.OPPOSER, PartyType.PETITIONER]:
                return party
        return None
    
    def get_all_party_names(self) -> List[str]:
        """Get all party names for appeal matching."""
        return [party.name for party in self.parties if party.name]
    
    def get_case_identifiers(self) -> List[str]:
        """Get case identifiers for appeal matching."""
        identifiers = []
        if self.case_number:
            identifiers.append(self.case_number)
        if self.proceeding_number:
            identifiers.append(self.proceeding_number)
        return identifiers
    
    def has_federal_circuit_appeal(self) -> bool:
        """Check if case has Federal Circuit appeal information."""
        return self.federal_circuit_appeal is not None or self.appeal_indicated
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert opinion to CSV row format."""
        row = {
            'case_number': self.case_number or '',
            'proceeding_number': self.proceeding_number or '',
            'proceeding_type': self.proceeding_type.value if self.proceeding_type else '',
            'case_title': self.case_title or '',
            'filing_date': self.filing_date.isoformat() if self.filing_date else '',
            'decision_date': self.decision_date.isoformat() if self.decision_date else '',
            'outcome': self.outcome.value if self.outcome else '',
            'outcome_description': self.outcome_description or '',
            'winner': self.winner or '',
            'source_file': self.source_file or '',
        }
        
        # Add party information
        applicant = self.get_applicant_registrant()
        opposer = self.get_opposer_petitioner()
        
        row['applicant_registrant'] = applicant.name if applicant else ''
        row['applicant_address'] = applicant.address if applicant else ''
        row['opposer_petitioner'] = opposer.name if opposer else ''
        row['opposer_address'] = opposer.address if opposer else ''
        
        # Add judges
        row['judges'] = '; '.join([judge.name for judge in self.judges if judge.name])
        
        # Add trademark information
        if self.subject_marks:
            row['trademark_marks'] = '; '.join([
                mark.mark_text for mark in self.subject_marks if mark.mark_text
            ])
            row['registration_numbers'] = '; '.join([
                mark.registration_number for mark in self.subject_marks 
                if mark.registration_number
            ])
            row['application_numbers'] = '; '.join([
                mark.application_number for mark in self.subject_marks 
                if mark.application_number
            ])
        else:
            row['trademark_marks'] = ''
            row['registration_numbers'] = ''
            row['application_numbers'] = ''
        
        # Add legal representation
        row['law_firms'] = '; '.join(self.law_firms)
        row['attorneys'] = '; '.join([
            attorney.name for attorney in self.all_attorneys if attorney.name
        ])
        
        # Add Federal Circuit appeal information
        if self.federal_circuit_appeal:
            fc_appeal = self.federal_circuit_appeal
            row['federal_circuit_case_number'] = fc_appeal.case_number or ''
            row['federal_circuit_case_name'] = fc_appeal.case_name or ''
            row['federal_circuit_filing_date'] = fc_appeal.filing_date.isoformat() if fc_appeal.filing_date else ''
            row['federal_circuit_decision_date'] = fc_appeal.decision_date.isoformat() if fc_appeal.decision_date else ''
            row['federal_circuit_outcome'] = fc_appeal.outcome or ''
            row['federal_circuit_judges'] = '; '.join(fc_appeal.judges)
            row['federal_circuit_citation'] = fc_appeal.citation or ''
            row['federal_circuit_url'] = fc_appeal.courtlistener_url or ''
            row['appeal_indicated'] = str(self.appeal_indicated)
        else:
            row['federal_circuit_case_number'] = ''
            row['federal_circuit_case_name'] = ''
            row['federal_circuit_filing_date'] = ''
            row['federal_circuit_decision_date'] = ''
            row['federal_circuit_outcome'] = ''
            row['federal_circuit_judges'] = ''
            row['federal_circuit_citation'] = ''
            row['federal_circuit_url'] = ''
            row['appeal_indicated'] = str(self.appeal_indicated)
        
        return row
    
    @classmethod
    def get_csv_headers(cls) -> List[str]:
        """Get CSV column headers."""
        return [
            'case_number',
            'proceeding_number',
            'proceeding_type',
            'case_title',
            'filing_date',
            'decision_date',
            'outcome',
            'outcome_description',
            'winner',
            'applicant_registrant',
            'applicant_address',
            'opposer_petitioner',
            'opposer_address',
            'judges',
            'trademark_marks',
            'registration_numbers',
            'application_numbers',
            'law_firms',
            'attorneys',
            'federal_circuit_case_number',
            'federal_circuit_case_name',
            'federal_circuit_filing_date',
            'federal_circuit_decision_date',
            'federal_circuit_outcome',
            'federal_circuit_judges',
            'federal_circuit_citation',
            'federal_circuit_url',
            'appeal_indicated',
            'source_file'
        ]


@dataclass
class ProcessingStats:
    """Statistics for processing run."""
    total_files_processed: int = 0
    total_documents_processed: int = 0
    opinions_found: int = 0
    opinions_parsed: int = 0
    federal_circuit_appeals_found: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def duration_seconds(self) -> float:
        """Get processing duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def summary(self) -> str:
        """Get processing summary."""
        duration = self.duration_seconds()
        return (
            f"Processing completed in {duration:.1f} seconds\n"
            f"Files processed: {self.total_files_processed}\n"
            f"Documents processed: {self.total_documents_processed}\n"
            f"Opinions found: {self.opinions_found}\n"
            f"Opinions successfully parsed: {self.opinions_parsed}\n"
            f"Federal Circuit appeals found: {self.federal_circuit_appeals_found}\n"
            f"Errors: {self.errors}"
        )
