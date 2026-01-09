"""
Jurisdiction Detection Service

Analyzes document text to automatically detect:
- Court type (Federal, State, Bankruptcy, Appellate)
- Jurisdiction (Florida, Federal Districts)
- Applicable rule sets (with dependencies)

Uses pattern matching and AI analysis for accurate detection.
"""
import re
import logging
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.jurisdiction import (
    Jurisdiction, RuleSet, RuleSetDependency, CourtLocation,
    JurisdictionType, CourtType, DependencyType
)

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Result of jurisdiction detection"""
    detected: bool
    confidence: float  # 0.0 to 1.0

    jurisdiction: Optional[Jurisdiction] = None
    court_location: Optional[CourtLocation] = None

    # All applicable rule sets (including dependencies)
    applicable_rule_sets: List[RuleSet] = None

    # Detection details
    detected_court_name: Optional[str] = None
    detected_district: Optional[str] = None
    detected_case_number: Optional[str] = None
    detected_court_type: Optional[CourtType] = None

    # Patterns that matched
    matched_patterns: List[str] = None

    def __post_init__(self):
        if self.applicable_rule_sets is None:
            self.applicable_rule_sets = []
        if self.matched_patterns is None:
            self.matched_patterns = []


class JurisdictionDetector:
    """
    Detects jurisdiction from document text and returns applicable rule sets

    Example usage:
        detector = JurisdictionDetector(db)
        result = detector.detect_from_text(document_text)

        if result.detected:
            print(f"Detected: {result.jurisdiction.name}")
            print(f"Rule sets: {[rs.code for rs in result.applicable_rule_sets]}")
    """

    # Common court name patterns
    FEDERAL_DISTRICT_PATTERNS = [
        (r"UNITED\s+STATES\s+DISTRICT\s+COURT\s*[,\-\s]*\s*(SOUTHERN|MIDDLE|NORTHERN)\s+DISTRICT\s+OF\s+FLORIDA", "federal_district"),
        (r"(SOUTHERN|MIDDLE|NORTHERN)\s+DISTRICT\s+OF\s+FLORIDA", "federal_district"),
        (r"U\.?S\.?\s+DISTRICT\s+COURT\s*[,\-\s]*\s*(S\.?D\.?|M\.?D\.?|N\.?D\.?)\s*FLA", "federal_district"),
        (r"(S\.?D\.?|M\.?D\.?|N\.?D\.?)\s+FLA\.?", "federal_district"),
    ]

    BANKRUPTCY_PATTERNS = [
        (r"UNITED\s+STATES\s+BANKRUPTCY\s+COURT", "bankruptcy"),
        (r"BANKRUPTCY\s+COURT\s*[,\-\s]*\s*(SOUTHERN|MIDDLE|NORTHERN)\s+DISTRICT", "bankruptcy"),
        (r"IN\s+RE:.*DEBTOR", "bankruptcy"),
        (r"CHAPTER\s+(7|11|13|12|15)\s+CASE", "bankruptcy"),
    ]

    FLORIDA_STATE_PATTERNS = [
        (r"IN\s+THE\s+CIRCUIT\s+COURT\s+OF\s+THE\s+(\d+)(?:ST|ND|RD|TH)\s+JUDICIAL\s+CIRCUIT", "florida_circuit"),
        (r"CIRCUIT\s+COURT\s+OF\s+THE\s+(\d+)(?:ST|ND|RD|TH)\s+JUDICIAL\s+CIRCUIT", "florida_circuit"),
        (r"(\d+)(?:ST|ND|RD|TH)\s+JUDICIAL\s+CIRCUIT.*FLORIDA", "florida_circuit"),
        (r"IN\s+THE\s+COUNTY\s+COURT.*FLORIDA", "florida_county"),
        (r"COUNTY\s+COURT\s+IN\s+AND\s+FOR\s+(\w+)\s+COUNTY,?\s+FLORIDA", "florida_county"),
    ]

    FLORIDA_APPELLATE_PATTERNS = [
        (r"DISTRICT\s+COURT\s+OF\s+APPEAL\s+OF\s+FLORIDA\s*[,\-\s]*\s*(\d+)(?:ST|ND|RD|TH)\s+DISTRICT", "florida_dca"),
        (r"(\d+)(?:ST|ND|RD|TH)\s+DISTRICT\s+COURT\s+OF\s+APPEAL", "florida_dca"),
        (r"FLORIDA\s+SUPREME\s+COURT", "florida_supreme"),
        (r"SUPREME\s+COURT\s+OF\s+FLORIDA", "florida_supreme"),
    ]

    FEDERAL_APPELLATE_PATTERNS = [
        (r"UNITED\s+STATES\s+COURT\s+OF\s+APPEALS\s*[,\-\s]*\s*(\d+)(?:ST|ND|RD|TH)\s+CIRCUIT", "federal_circuit"),
        (r"(\d+)(?:ST|ND|RD|TH)\s+CIRCUIT\s+COURT\s+OF\s+APPEALS", "federal_circuit"),
        (r"ELEVENTH\s+CIRCUIT", "federal_circuit_11"),
    ]

    # Case number patterns
    CASE_NUMBER_PATTERNS = [
        (r"\d{1,2}:\d{2}-cv-\d+", "federal_civil"),  # Federal civil: 1:23-cv-12345
        (r"\d{1,2}:\d{2}-cr-\d+", "federal_criminal"),  # Federal criminal
        (r"\d{2}-\d+-[A-Z]{3}", "bankruptcy"),  # Bankruptcy: 23-12345-ABC
        (r"\d{4}-\d+-CA-\d+", "florida_circuit"),  # Florida Circuit: 2024-001234-CA-01
        (r"\d{4}CF\d+", "florida_criminal"),  # Florida Criminal
        (r"\d{4}SC\d+", "florida_small_claims"),  # Florida Small Claims
        (r"\d{2}-\d+", "florida_appellate"),  # Florida DCA: SC23-1234
    ]

    def __init__(self, db: Session):
        self.db = db

    def detect_from_text(
        self,
        text: str,
        case_number: Optional[str] = None,
        court_name: Optional[str] = None
    ) -> DetectionResult:
        """
        Detect jurisdiction from document text

        Args:
            text: Full text of the document
            case_number: Optional case number (if already extracted)
            court_name: Optional court name (if already extracted)

        Returns:
            DetectionResult with jurisdiction, court location, and applicable rule sets
        """
        # Normalize text for matching
        normalized_text = text.upper()

        # Initialize result
        result = DetectionResult(detected=False, confidence=0.0)
        matched_patterns = []

        # Try to detect court type and district
        court_type, district, pattern_matches = self._detect_court_type(normalized_text)

        if court_type:
            result.detected_court_type = court_type
            matched_patterns.extend(pattern_matches)

        if district:
            result.detected_district = district

        # Try to detect case number
        detected_case_num = case_number or self._detect_case_number(normalized_text)
        if detected_case_num:
            result.detected_case_number = detected_case_num

        # Find matching court location
        court_location = self._find_court_location(court_type, district, pattern_matches)
        if court_location:
            result.court_location = court_location
            result.jurisdiction = court_location.jurisdiction
            result.detected_court_name = court_location.name
            result.detected = True
            result.confidence = 0.9 if len(matched_patterns) > 1 else 0.7
        elif court_type:
            # Found court type but no specific location - use default jurisdiction
            result.jurisdiction = self._get_default_jurisdiction(court_type, district)
            result.detected = result.jurisdiction is not None
            result.confidence = 0.6

        # Get applicable rule sets with dependencies
        if result.detected:
            result.applicable_rule_sets = self._get_applicable_rule_sets(
                result.jurisdiction,
                result.court_location,
                court_type
            )

        result.matched_patterns = matched_patterns
        return result

    def _detect_court_type(self, text: str) -> Tuple[Optional[CourtType], Optional[str], List[str]]:
        """Detect court type and district from text"""

        matched_patterns = []

        # Check Federal District Court
        for pattern, pattern_type in self.FEDERAL_DISTRICT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matched_patterns.append(pattern_type)
                district = None
                if match.groups():
                    district_match = match.group(1) if match.lastindex >= 1 else None
                    if district_match:
                        if "SOUTHERN" in district_match.upper() or "S.D" in district_match.upper() or "SD" in district_match.upper():
                            district = "Southern"
                        elif "MIDDLE" in district_match.upper() or "M.D" in district_match.upper() or "MD" in district_match.upper():
                            district = "Middle"
                        elif "NORTHERN" in district_match.upper() or "N.D" in district_match.upper() or "ND" in district_match.upper():
                            district = "Northern"
                return CourtType.DISTRICT, district, matched_patterns

        # Check Bankruptcy
        for pattern, pattern_type in self.BANKRUPTCY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matched_patterns.append(pattern_type)
                # Try to determine district
                district = None
                for d_pattern, _ in self.FEDERAL_DISTRICT_PATTERNS:
                    d_match = re.search(d_pattern, text, re.IGNORECASE)
                    if d_match and d_match.groups():
                        district_match = d_match.group(1)
                        if "SOUTHERN" in district_match.upper():
                            district = "Southern"
                        elif "MIDDLE" in district_match.upper():
                            district = "Middle"
                        elif "NORTHERN" in district_match.upper():
                            district = "Northern"
                        break
                return CourtType.BANKRUPTCY, district, matched_patterns

        # Check Florida State Courts
        for pattern, pattern_type in self.FLORIDA_STATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matched_patterns.append(pattern_type)
                circuit = None
                if match.groups():
                    try:
                        circuit = int(match.group(1))
                    except (ValueError, IndexError):
                        pass
                court_type = CourtType.CIRCUIT if pattern_type == "florida_circuit" else CourtType.COUNTY
                return court_type, str(circuit) if circuit else None, matched_patterns

        # Check Florida Appellate
        for pattern, pattern_type in self.FLORIDA_APPELLATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matched_patterns.append(pattern_type)
                dca_num = None
                if pattern_type == "florida_dca" and match.groups():
                    try:
                        dca_num = int(match.group(1))
                    except (ValueError, IndexError):
                        pass
                court_type = CourtType.SUPREME_STATE if pattern_type == "florida_supreme" else CourtType.APPELLATE_STATE
                return court_type, str(dca_num) if dca_num else None, matched_patterns

        # Check Federal Appellate
        for pattern, pattern_type in self.FEDERAL_APPELLATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matched_patterns.append(pattern_type)
                return CourtType.APPELLATE_FEDERAL, "11", matched_patterns

        return None, None, matched_patterns

    def _detect_case_number(self, text: str) -> Optional[str]:
        """Extract case number from text"""
        for pattern, case_type in self.CASE_NUMBER_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    def _find_court_location(
        self,
        court_type: Optional[CourtType],
        district: Optional[str],
        pattern_matches: List[str]
    ) -> Optional[CourtLocation]:
        """Find matching court location in database"""

        if not court_type:
            return None

        query = self.db.query(CourtLocation).filter(
            CourtLocation.court_type == court_type,
            CourtLocation.is_active == True
        )

        if district:
            query = query.filter(CourtLocation.district == district)

        return query.first()

    def _get_default_jurisdiction(
        self,
        court_type: Optional[CourtType],
        district: Optional[str]
    ) -> Optional[Jurisdiction]:
        """Get default jurisdiction when no court location found"""

        if not court_type:
            return None

        # Map court type to jurisdiction type
        if court_type in [CourtType.DISTRICT, CourtType.APPELLATE_FEDERAL, CourtType.SUPREME_FEDERAL]:
            jur_type = JurisdictionType.FEDERAL
        elif court_type == CourtType.BANKRUPTCY:
            jur_type = JurisdictionType.BANKRUPTCY
        else:
            jur_type = JurisdictionType.STATE

        # Try to find matching jurisdiction
        query = self.db.query(Jurisdiction).filter(
            Jurisdiction.jurisdiction_type == jur_type,
            Jurisdiction.is_active == True
        )

        if jur_type == JurisdictionType.STATE:
            query = query.filter(Jurisdiction.code == "FL")

        return query.first()

    def _get_applicable_rule_sets(
        self,
        jurisdiction: Optional[Jurisdiction],
        court_location: Optional[CourtLocation],
        court_type: Optional[CourtType]
    ) -> List[RuleSet]:
        """
        Get all applicable rule sets including dependencies

        This implements CompuLaw's concurrent rule loading:
        - When a local rule set is selected, also load all required parent rules
        - For example, selecting FL:BRMD-7 also loads FRCP and FRBP
        """

        rule_sets = []
        seen_ids: Set[str] = set()

        # Start with default rule set from court location
        if court_location and court_location.default_rule_set_id:
            default_rs = self.db.query(RuleSet).get(court_location.default_rule_set_id)
            if default_rs and default_rs.id not in seen_ids:
                rule_sets.append(default_rs)
                seen_ids.add(default_rs.id)

        # Add local rule set from court location
        if court_location and court_location.local_rule_set_id:
            local_rs = self.db.query(RuleSet).get(court_location.local_rule_set_id)
            if local_rs and local_rs.id not in seen_ids:
                rule_sets.append(local_rs)
                seen_ids.add(local_rs.id)

        # If no court location, find rule sets by jurisdiction and court type
        if not rule_sets and jurisdiction:
            base_rule_sets = self.db.query(RuleSet).filter(
                RuleSet.jurisdiction_id == jurisdiction.id,
                RuleSet.is_active == True
            )
            if court_type:
                base_rule_sets = base_rule_sets.filter(RuleSet.court_type == court_type)

            for rs in base_rule_sets.all():
                if rs.id not in seen_ids:
                    rule_sets.append(rs)
                    seen_ids.add(rs.id)

        # Resolve dependencies (concurrent rules)
        all_rule_sets = list(rule_sets)
        for rs in rule_sets:
            dependencies = self._get_rule_set_dependencies(rs.id)
            for dep_rs in dependencies:
                if dep_rs.id not in seen_ids:
                    all_rule_sets.append(dep_rs)
                    seen_ids.add(dep_rs.id)

        # Sort by priority (local rules first, then base rules)
        all_rule_sets.sort(key=lambda x: (not x.is_local, x.code))

        return all_rule_sets

    def _get_rule_set_dependencies(self, rule_set_id: str) -> List[RuleSet]:
        """Get all rule sets that this rule set depends on (recursive)"""

        dependencies = []
        seen_ids: Set[str] = set()

        def collect_deps(rs_id: str):
            deps = self.db.query(RuleSetDependency).filter(
                RuleSetDependency.rule_set_id == rs_id
            ).all()

            for dep in deps:
                if dep.required_rule_set_id not in seen_ids:
                    seen_ids.add(dep.required_rule_set_id)
                    required_rs = self.db.query(RuleSet).get(dep.required_rule_set_id)
                    if required_rs:
                        dependencies.append(required_rs)
                        # Recursive - get dependencies of dependencies
                        collect_deps(required_rs.id)

        collect_deps(rule_set_id)
        return dependencies

    def get_rule_sets_for_case(
        self,
        case_id: str
    ) -> List[RuleSet]:
        """
        Get all rule sets applicable to a specific case

        Uses the case's jurisdiction and any manually assigned rule sets
        """
        from app.models.jurisdiction import CaseRuleSet
        from app.models.case import Case

        # Get case
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return []

        # Get manually assigned rule sets
        manual_assignments = self.db.query(CaseRuleSet).filter(
            CaseRuleSet.case_id == case_id,
            CaseRuleSet.is_active == True
        ).all()

        rule_sets = []
        seen_ids: Set[str] = set()

        # Add manually assigned rule sets
        for assignment in manual_assignments:
            rs = self.db.query(RuleSet).get(assignment.rule_set_id)
            if rs and rs.id not in seen_ids:
                rule_sets.append(rs)
                seen_ids.add(rs.id)

        # If no manual assignments, detect from case metadata
        if not rule_sets and case.court:
            result = self.detect_from_text(case.court)
            rule_sets = result.applicable_rule_sets

        return rule_sets


# Convenience function
def detect_jurisdiction(db: Session, text: str) -> DetectionResult:
    """Quick function to detect jurisdiction from text"""
    detector = JurisdictionDetector(db)
    return detector.detect_from_text(text)
