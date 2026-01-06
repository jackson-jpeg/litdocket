"""
Florida Jurisdictions - Complete mapping of all Florida courts
Includes 20 Judicial Circuits, 67 Counties, and 3 Federal Districts
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class County:
    """Florida County Information"""
    name: str
    circuit: int
    population: int
    county_seat: str
    federal_district: str


@dataclass
class Circuit:
    """Florida Judicial Circuit Information"""
    number: int
    name: str
    counties: List[str]
    chief_judge: Optional[str] = None
    administrative_orders_url: Optional[str] = None


@dataclass
class FederalDistrict:
    """Federal District Court Information"""
    name: str
    abbrev: str
    divisions: List[str]
    chief_judge: Optional[str] = None
    local_rules_url: Optional[str] = None


# All 20 Florida Judicial Circuits
FLORIDA_CIRCUITS = {
    1: Circuit(
        number=1,
        name="First Judicial Circuit",
        counties=["Escambia", "Okaloosa", "Santa Rosa", "Walton"],
        administrative_orders_url="https://www.firstjudicialcircuit.org"
    ),
    2: Circuit(
        number=2,
        name="Second Judicial Circuit",
        counties=["Franklin", "Gadsden", "Jefferson", "Leon", "Liberty", "Wakulla"],
        administrative_orders_url="https://www.leon.clerk.com"
    ),
    3: Circuit(
        number=3,
        name="Third Judicial Circuit",
        counties=["Columbia", "Dixie", "Hamilton", "Lafayette", "Madison", "Suwannee", "Taylor"],
        administrative_orders_url="https://www.3rdcircuit.org"
    ),
    4: Circuit(
        number=4,
        name="Fourth Judicial Circuit",
        counties=["Clay", "Duval", "Nassau"],
        administrative_orders_url="https://www.jud4.org"
    ),
    5: Circuit(
        number=5,
        name="Fifth Judicial Circuit",
        counties=["Citrus", "Hernando", "Lake", "Marion", "Sumter"],
        administrative_orders_url="https://www.circuit5.org"
    ),
    6: Circuit(
        number=6,
        name="Sixth Judicial Circuit",
        counties=["Pasco", "Pinellas"],
        administrative_orders_url="https://www.jud6.org"
    ),
    7: Circuit(
        number=7,
        name="Seventh Judicial Circuit",
        counties=["Flagler", "Putnam", "St. Johns", "Volusia"],
        administrative_orders_url="https://www.circuit7.org"
    ),
    8: Circuit(
        number=8,
        name="Eighth Judicial Circuit",
        counties=["Alachua", "Baker", "Bradford", "Gilchrist", "Levy", "Union"],
        administrative_orders_url="https://www.circuit8.org"
    ),
    9: Circuit(
        number=9,
        name="Ninth Judicial Circuit",
        counties=["Orange", "Osceola"],
        administrative_orders_url="https://ninthcircuit.org"
    ),
    10: Circuit(
        number=10,
        name="Tenth Judicial Circuit",
        counties=["Hardee", "Highlands", "Polk"],
        administrative_orders_url="https://www.polk.courts.state.fl.us"
    ),
    11: Circuit(
        number=11,
        name="Eleventh Judicial Circuit",
        counties=["Miami-Dade"],
        administrative_orders_url="https://www.jud11.flcourts.org"
    ),
    12: Circuit(
        number=12,
        name="Twelfth Judicial Circuit",
        counties=["DeSoto", "Manatee", "Sarasota"],
        administrative_orders_url="https://www.jud12.flcourts.org"
    ),
    13: Circuit(
        number=13,
        name="Thirteenth Judicial Circuit",
        counties=["Hillsborough"],
        administrative_orders_url="https://www.fljud13.org"
    ),
    14: Circuit(
        number=14,
        name="Fourteenth Judicial Circuit",
        counties=["Bay", "Calhoun", "Gulf", "Holmes", "Jackson", "Washington"],
        administrative_orders_url="https://www.14thcircuit.org"
    ),
    15: Circuit(
        number=15,
        name="Fifteenth Judicial Circuit",
        counties=["Palm Beach"],
        administrative_orders_url="https://www.15thcircuit.co.palm-beach.fl.us"
    ),
    16: Circuit(
        number=16,
        name="Sixteenth Judicial Circuit",
        counties=["Monroe"],
        administrative_orders_url="https://www.keysso.net/circuit_court"
    ),
    17: Circuit(
        number=17,
        name="Seventeenth Judicial Circuit",
        counties=["Broward"],
        administrative_orders_url="https://www.17th.flcourts.org"
    ),
    18: Circuit(
        number=18,
        name="Eighteenth Judicial Circuit",
        counties=["Brevard", "Seminole"],
        administrative_orders_url="https://www.flcourts18.org"
    ),
    19: Circuit(
        number=19,
        name="Nineteenth Judicial Circuit",
        counties=["Indian River", "Martin", "Okeechobee", "St. Lucie"],
        administrative_orders_url="https://www.circuit19.org"
    ),
    20: Circuit(
        number=20,
        name="Twentieth Judicial Circuit",
        counties=["Charlotte", "Collier", "Glades", "Hendry", "Lee"],
        administrative_orders_url="https://www.ca.cjis20.org"
    ),
}


# All 67 Florida Counties with Circuit Mapping
FLORIDA_COUNTIES = {
    # Circuit 1
    "Escambia": County("Escambia", 1, 321905, "Pensacola", "Northern"),
    "Okaloosa": County("Okaloosa", 1, 211668, "Crestview", "Northern"),
    "Santa Rosa": County("Santa Rosa", 1, 188000, "Milton", "Northern"),
    "Walton": County("Walton", 1, 75305, "DeFuniak Springs", "Northern"),

    # Circuit 2
    "Franklin": County("Franklin", 2, 12451, "Apalachicola", "Northern"),
    "Gadsden": County("Gadsden", 2, 43826, "Quincy", "Northern"),
    "Jefferson": County("Jefferson", 2, 14246, "Monticello", "Northern"),
    "Leon": County("Leon", 2, 293582, "Tallahassee", "Northern"),
    "Liberty": County("Liberty", 2, 8353, "Bristol", "Northern"),
    "Wakulla": County("Wakulla", 2, 33764, "Crawfordville", "Northern"),

    # Circuit 3
    "Columbia": County("Columbia", 3, 71686, "Lake City", "Middle"),
    "Dixie": County("Dixie", 3, 16759, "Cross City", "Middle"),
    "Hamilton": County("Hamilton", 3, 14004, "Jasper", "Middle"),
    "Lafayette": County("Lafayette", 3, 8330, "Mayo", "Middle"),
    "Madison": County("Madison", 3, 18108, "Madison", "Middle"),
    "Suwannee": County("Suwannee", 3, 44329, "Live Oak", "Middle"),
    "Taylor": County("Taylor", 3, 21796, "Perry", "Middle"),

    # Circuit 4
    "Clay": County("Clay", 4, 218245, "Green Cove Springs", "Middle"),
    "Duval": County("Duval", 4, 995567, "Jacksonville", "Middle"),
    "Nassau": County("Nassau", 4, 88625, "Fernandina Beach", "Middle"),

    # Circuit 5
    "Citrus": County("Citrus", 5, 153843, "Inverness", "Middle"),
    "Hernando": County("Hernando", 5, 194515, "Brooksville", "Middle"),
    "Lake": County("Lake", 5, 383956, "Tavares", "Middle"),
    "Marion": County("Marion", 5, 375908, "Ocala", "Middle"),
    "Sumter": County("Sumter", 5, 129752, "Bushnell", "Middle"),

    # Circuit 6
    "Pasco": County("Pasco", 6, 553947, "Dade City", "Middle"),
    "Pinellas": County("Pinellas", 6, 959107, "Clearwater", "Middle"),

    # Circuit 7
    "Flagler": County("Flagler", 7, 115378, "Bunnell", "Middle"),
    "Putnam": County("Putnam", 7, 73321, "Palatka", "Middle"),
    "St. Johns": County("St. Johns", 7, 273425, "St. Augustine", "Middle"),
    "Volusia": County("Volusia", 7, 553084, "DeLand", "Middle"),

    # Circuit 8
    "Alachua": County("Alachua", 8, 278468, "Gainesville", "Middle"),
    "Baker": County("Baker", 8, 28259, "Macclenny", "Middle"),
    "Bradford": County("Bradford", 8, 27440, "Starke", "Middle"),
    "Gilchrist": County("Gilchrist", 8, 18008, "Trenton", "Middle"),
    "Levy": County("Levy", 8, 42915, "Bronson", "Middle"),
    "Union": County("Union", 8, 15535, "Lake Butler", "Middle"),

    # Circuit 9
    "Orange": County("Orange", 9, 1429908, "Orlando", "Middle"),
    "Osceola": County("Osceola", 9, 375751, "Kissimmee", "Middle"),

    # Circuit 10
    "Hardee": County("Hardee", 10, 27731, "Wauchula", "Middle"),
    "Highlands": County("Highlands", 10, 105755, "Sebring", "Middle"),
    "Polk": County("Polk", 10, 724777, "Bartow", "Middle"),

    # Circuit 11
    "Miami-Dade": County("Miami-Dade", 11, 2701767, "Miami", "Southern"),

    # Circuit 12
    "DeSoto": County("DeSoto", 12, 37492, "Arcadia", "Middle"),
    "Manatee": County("Manatee", 12, 403253, "Bradenton", "Middle"),
    "Sarasota": County("Sarasota", 12, 434263, "Sarasota", "Middle"),

    # Circuit 13
    "Hillsborough": County("Hillsborough", 13, 1459762, "Tampa", "Middle"),

    # Circuit 14
    "Bay": County("Bay", 14, 175216, "Panama City", "Northern"),
    "Calhoun": County("Calhoun", 14, 13648, "Blountstown", "Northern"),
    "Gulf": County("Gulf", 14, 15863, "Port St. Joe", "Northern"),
    "Holmes": County("Holmes", 14, 19653, "Bonifay", "Northern"),
    "Jackson": County("Jackson", 14, 46765, "Marianna", "Northern"),
    "Washington": County("Washington", 14, 25318, "Chipley", "Northern"),

    # Circuit 15
    "Palm Beach": County("Palm Beach", 15, 1496770, "West Palm Beach", "Southern"),

    # Circuit 16
    "Monroe": County("Monroe", 16, 82874, "Key West", "Southern"),

    # Circuit 17
    "Broward": County("Broward", 17, 1944375, "Fort Lauderdale", "Southern"),

    # Circuit 18
    "Brevard": County("Brevard", 18, 606612, "Titusville", "Middle"),
    "Seminole": County("Seminole", 18, 471826, "Sanford", "Middle"),

    # Circuit 19
    "Indian River": County("Indian River", 19, 159788, "Vero Beach", "Southern"),
    "Martin": County("Martin", 19, 161000, "Stuart", "Southern"),
    "Okeechobee": County("Okeechobee", 19, 41607, "Okeechobee", "Southern"),
    "St. Lucie": County("St. Lucie", 19, 328297, "Fort Pierce", "Southern"),

    # Circuit 20
    "Charlotte": County("Charlotte", 20, 186847, "Punta Gorda", "Middle"),
    "Collier": County("Collier", 20, 384902, "Naples", "Middle"),
    "Glades": County("Glades", 20, 13159, "Moore Haven", "Middle"),
    "Hendry": County("Hendry", 20, 41252, "LaBelle", "Middle"),
    "Lee": County("Lee", 20, 760822, "Fort Myers", "Middle"),
}


# 3 Federal Districts in Florida
FEDERAL_DISTRICTS = {
    "Northern": FederalDistrict(
        name="United States District Court for the Northern District of Florida",
        abbrev="N.D. Fla.",
        divisions=["Pensacola", "Tallahassee", "Gainesville", "Panama City"],
        local_rules_url="https://www.flnd.uscourts.gov/local-rules"
    ),
    "Middle": FederalDistrict(
        name="United States District Court for the Middle District of Florida",
        abbrev="M.D. Fla.",
        divisions=["Jacksonville", "Orlando", "Tampa", "Ocala", "Fort Myers"],
        local_rules_url="https://www.flmd.uscourts.gov/rules"
    ),
    "Southern": FederalDistrict(
        name="United States District Court for the Southern District of Florida",
        abbrev="S.D. Fla.",
        divisions=["Miami", "Fort Lauderdale", "West Palm Beach", "Key West", "Fort Pierce"],
        local_rules_url="https://www.flsd.uscourts.gov/local-rules"
    ),
}


# Utility Functions

def get_circuit_by_county(county_name: str) -> Optional[int]:
    """Get circuit number for a given county"""
    county = FLORIDA_COUNTIES.get(county_name)
    return county.circuit if county else None


def get_federal_district_by_county(county_name: str) -> Optional[str]:
    """Get federal district for a given county"""
    county = FLORIDA_COUNTIES.get(county_name)
    return county.federal_district if county else None


def get_counties_in_circuit(circuit_number: int) -> List[str]:
    """Get all counties in a given circuit"""
    circuit = FLORIDA_CIRCUITS.get(circuit_number)
    return circuit.counties if circuit else []


def identify_jurisdiction(court_string: str) -> Dict[str, any]:
    """
    Identify jurisdiction from court name string

    Examples:
    - "Circuit Court of the Eleventh Judicial Circuit in and for Miami-Dade County"
    - "United States District Court for the Southern District of Florida"
    - "County Court in and for Broward County"
    """
    court_lower = court_string.lower()

    # Check for Federal District Courts
    if "united states district court" in court_lower or "u.s. district court" in court_lower:
        if "northern district" in court_lower:
            return {
                "type": "federal",
                "district": "Northern",
                "district_name": FEDERAL_DISTRICTS["Northern"].name,
                "abbrev": "N.D. Fla."
            }
        elif "middle district" in court_lower:
            return {
                "type": "federal",
                "district": "Middle",
                "district_name": FEDERAL_DISTRICTS["Middle"].name,
                "abbrev": "M.D. Fla."
            }
        elif "southern district" in court_lower:
            return {
                "type": "federal",
                "district": "Southern",
                "district_name": FEDERAL_DISTRICTS["Southern"].name,
                "abbrev": "S.D. Fla."
            }

    # Check for State Circuit Courts
    if "circuit court" in court_lower:
        # Try to find county name
        for county_name, county in FLORIDA_COUNTIES.items():
            if county_name.lower() in court_lower:
                return {
                    "type": "state_circuit",
                    "county": county_name,
                    "circuit": county.circuit,
                    "circuit_name": FLORIDA_CIRCUITS[county.circuit].name
                }

        # Try to find circuit number
        import re
        circuit_match = re.search(r'(\w+)\s+judicial\s+circuit', court_lower)
        if circuit_match:
            circuit_word = circuit_match.group(1)
            circuit_map = {
                "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
                "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
                "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
                "nineteenth": 19, "twentieth": 20
            }
            circuit_num = circuit_map.get(circuit_word)
            if circuit_num:
                return {
                    "type": "state_circuit",
                    "circuit": circuit_num,
                    "circuit_name": FLORIDA_CIRCUITS[circuit_num].name,
                    "counties": FLORIDA_CIRCUITS[circuit_num].counties
                }

    # Check for County Courts
    if "county court" in court_lower:
        for county_name in FLORIDA_COUNTIES.keys():
            if county_name.lower() in court_lower:
                county = FLORIDA_COUNTIES[county_name]
                return {
                    "type": "state_county",
                    "county": county_name,
                    "circuit": county.circuit
                }

    return {"type": "unknown", "raw": court_string}


def get_applicable_rules(jurisdiction_info: Dict) -> List[str]:
    """
    Get list of applicable rules based on jurisdiction

    Returns prioritized list of rule sources to consult
    """
    rules = []

    if jurisdiction_info.get("type") == "federal":
        rules.extend([
            "Federal Rules of Civil Procedure (FRCP)",
            "Federal Rules of Evidence (FRE)",
            f"{jurisdiction_info['district']} District Local Rules",
        ])
    elif jurisdiction_info.get("type") in ["state_circuit", "state_county"]:
        rules.extend([
            "Florida Rules of Civil Procedure",
            "Florida Rules of Judicial Administration",
            "Florida Rules of Evidence",
        ])

        if jurisdiction_info.get("circuit"):
            circuit_num = jurisdiction_info["circuit"]
            rules.append(f"Circuit {circuit_num} Local Administrative Orders")

    return rules


# Example usage and testing
if __name__ == "__main__":
    # Test jurisdiction identification
    test_courts = [
        "Circuit Court of the Eleventh Judicial Circuit in and for Miami-Dade County, Florida",
        "United States District Court for the Southern District of Florida",
        "County Court in and for Broward County, Florida",
        "Circuit Court, Sixth Judicial Circuit, Pinellas County",
    ]

    print("=== Florida Jurisdiction Mapping System ===\n")

    for court in test_courts:
        print(f"Court: {court}")
        jurisdiction = identify_jurisdiction(court)
        print(f"Jurisdiction: {jurisdiction}")
        print(f"Applicable Rules: {get_applicable_rules(jurisdiction)}")
        print()

    # Test county lookup
    print("\n=== Circuit Lookup Examples ===")
    test_counties = ["Miami-Dade", "Broward", "Orange", "Hillsborough"]
    for county in test_counties:
        circuit = get_circuit_by_county(county)
        federal = get_federal_district_by_county(county)
        print(f"{county} County: Circuit {circuit}, Federal District: {federal}")
