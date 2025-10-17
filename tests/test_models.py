"""Unit tests for data models."""

import pytest
from datetime import datetime
from src.models import (
    OutcomeType,
    PartyType,
    ProceedingType,
    TrademarkMark,
    Attorney,
    Party,
    Judge,
    FederalCircuitAppeal,
    TTABOpinion
)


class TestEnums:
    """Tests for enum classes."""
    
    def test_outcome_type_values(self):
        """Test OutcomeType enum has expected values."""
        assert OutcomeType.GRANTED.value == "granted"
        assert OutcomeType.DENIED.value == "denied"
        assert OutcomeType.DISMISSED.value == "dismissed"
        assert OutcomeType.SUSTAINED.value == "sustained"
        assert OutcomeType.REVERSED.value == "reversed"
        assert OutcomeType.AFFIRMED.value == "affirmed"
        assert OutcomeType.REMANDED.value == "remanded"
        assert OutcomeType.SETTLED.value == "settled"
        assert OutcomeType.WITHDRAWN.value == "withdrawn"
        assert OutcomeType.UNKNOWN.value == "unknown"
    
    def test_party_type_values(self):
        """Test PartyType enum has expected values."""
        assert PartyType.APPLICANT.value == "applicant"
        assert PartyType.REGISTRANT.value == "registrant"
        assert PartyType.OPPOSER.value == "opposer"
        assert PartyType.PETITIONER.value == "petitioner"
        assert PartyType.PLAINTIFF.value == "plaintiff"
        assert PartyType.DEFENDANT.value == "defendant"
    
    def test_proceeding_type_values(self):
        """Test ProceedingType enum has expected values."""
        assert ProceedingType.OPPOSITION.value == "opposition"
        assert ProceedingType.CANCELLATION.value == "cancellation"
        assert ProceedingType.APPEAL.value == "appeal"
        assert ProceedingType.EXPUNGEMENT.value == "expungement"
        assert ProceedingType.REEXAMINATION.value == "reexamination"


class TestTrademarkMark:
    """Tests for TrademarkMark dataclass."""
    
    def test_trademark_mark_initialization(self):
        """Test TrademarkMark can be initialized with defaults."""
        mark = TrademarkMark()
        assert mark.mark_text is None
        assert mark.mark_description is None
        assert mark.registration_number is None
        assert mark.application_number is None
        assert mark.mark_type is None
        assert mark.goods_services is None
        assert mark.classes == []
    
    def test_trademark_mark_with_values(self):
        """Test TrademarkMark with specific values."""
        mark = TrademarkMark(
            mark_text="TEST MARK",
            registration_number="1234567",
            application_number="87/654321",
            mark_type="word",
            goods_services="Computer software",
            classes=["9", "42"]
        )
        assert mark.mark_text == "TEST MARK"
        assert mark.registration_number == "1234567"
        assert mark.application_number == "87/654321"
        assert mark.mark_type == "word"
        assert mark.goods_services == "Computer software"
        assert mark.classes == ["9", "42"]


class TestAttorney:
    """Tests for Attorney dataclass."""
    
    def test_attorney_initialization(self):
        """Test Attorney can be initialized with defaults."""
        attorney = Attorney()
        assert attorney.name is None
        assert attorney.registration_number is None
        assert attorney.firm is None
        assert attorney.address is None
        assert attorney.phone is None
        assert attorney.email is None
    
    def test_attorney_with_values(self):
        """Test Attorney with specific values."""
        attorney = Attorney(
            name="Jane Smith",
            registration_number="54321",
            firm="Smith & Associates",
            email="jane@example.com"
        )
        assert attorney.name == "Jane Smith"
        assert attorney.registration_number == "54321"
        assert attorney.firm == "Smith & Associates"
        assert attorney.email == "jane@example.com"


class TestParty:
    """Tests for Party dataclass."""
    
    def test_party_initialization(self):
        """Test Party can be initialized with defaults."""
        party = Party()
        assert party.name is None
        assert party.party_type is None
        assert party.address is None
        assert party.country is None
        assert party.attorneys == []
        assert party.trademark_marks == []
    
    def test_party_with_attorney(self):
        """Test Party can include attorneys."""
        attorney = Attorney(name="John Doe")
        party = Party(
            name="Test Company Inc",
            party_type=PartyType.APPLICANT,
            attorneys=[attorney]
        )
        assert party.name == "Test Company Inc"
        assert party.party_type == PartyType.APPLICANT
        assert len(party.attorneys) == 1
        assert party.attorneys[0].name == "John Doe"


class TestJudge:
    """Tests for Judge dataclass."""
    
    def test_judge_initialization(self):
        """Test Judge can be initialized with defaults."""
        judge = Judge()
        assert judge.name is None
        assert judge.title is None
        assert judge.role is None
    
    def test_judge_with_values(self):
        """Test Judge with specific values."""
        judge = Judge(
            name="Administrative Trademark Judge Smith",
            title="Administrative Trademark Judge",
            role="presiding"
        )
        assert judge.name == "Administrative Trademark Judge Smith"
        assert judge.title == "Administrative Trademark Judge"
        assert judge.role == "presiding"


class TestFederalCircuitAppeal:
    """Tests for FederalCircuitAppeal dataclass."""
    
    def test_appeal_initialization(self):
        """Test FederalCircuitAppeal can be initialized with defaults."""
        appeal = FederalCircuitAppeal()
        assert appeal.case_number is None
        assert appeal.case_name is None
        assert appeal.filing_date is None
        assert appeal.decision_date is None
        assert appeal.outcome is None
        assert appeal.judges == []
        assert appeal.citation is None
        assert appeal.courtlistener_url is None
        assert appeal.courtlistener_id is None
        assert appeal.docket_number is None
        assert appeal.appeal_outcome is None
    
    def test_appeal_with_values(self):
        """Test FederalCircuitAppeal with specific values."""
        filing_date = datetime(2024, 1, 15)
        decision_date = datetime(2024, 6, 30)
        
        appeal = FederalCircuitAppeal(
            case_number="2024-1234",
            case_name="Appellant v. USPTO",
            filing_date=filing_date,
            decision_date=decision_date,
            outcome="Affirmed",
            judges=["Circuit Judge Smith", "Circuit Judge Jones"],
            appeal_outcome=OutcomeType.AFFIRMED
        )
        assert appeal.case_number == "2024-1234"
        assert appeal.case_name == "Appellant v. USPTO"
        assert appeal.filing_date == filing_date
        assert appeal.decision_date == decision_date
        assert appeal.outcome == "Affirmed"
        assert len(appeal.judges) == 2
        assert appeal.appeal_outcome == OutcomeType.AFFIRMED


class TestTTABOpinion:
    """Tests for TTABOpinion dataclass."""
    
    def test_opinion_initialization(self):
        """Test TTABOpinion can be initialized with defaults."""
        opinion = TTABOpinion()
        assert opinion.case_number is None
        assert opinion.proceeding_number is None
        assert opinion.proceeding_type is None
        assert opinion.case_title is None
        assert opinion.filing_date is None
        assert opinion.decision_date is None
        assert opinion.parties == []
        assert opinion.judges == []
    
    def test_opinion_with_complete_data(self):
        """Test TTABOpinion with complete case data."""
        filing_date = datetime(2024, 1, 15)
        decision_date = datetime(2024, 12, 1)
        
        applicant = Party(name="Applicant Corp", party_type=PartyType.APPLICANT)
        opposer = Party(name="Opposer Inc", party_type=PartyType.OPPOSER)
        judge = Judge(name="Judge Smith", role="presiding")
        
        opinion = TTABOpinion(
            case_number="91234567",
            proceeding_number="91234567",
            proceeding_type=ProceedingType.OPPOSITION,
            case_title="Opposer Inc v. Applicant Corp",
            filing_date=filing_date,
            decision_date=decision_date,
            parties=[applicant, opposer],
            judges=[judge]
        )
        
        assert opinion.case_number == "91234567"
        assert opinion.proceeding_number == "91234567"
        assert opinion.proceeding_type == ProceedingType.OPPOSITION
        assert opinion.case_title == "Opposer Inc v. Applicant Corp"
        assert opinion.filing_date == filing_date
        assert opinion.decision_date == decision_date
        assert len(opinion.parties) == 2
        assert len(opinion.judges) == 1
        assert opinion.parties[0].name == "Applicant Corp"
        assert opinion.parties[1].name == "Opposer Inc"
        assert opinion.judges[0].name == "Judge Smith"
