"""
Legal rule constants for Florida and Federal court calculations.

This module provides authoritative constants for deadline calculations
based on Florida Rules of Judicial Administration and Federal Rules of Civil Procedure.

CRITICAL: These constants must match the actual court rules. Any changes must be
verified against the official rule citations provided.

Sources:
- Florida Rules of Judicial Administration 2.514(b) - Service methods and extensions
- Federal Rules of Civil Procedure (FRCP) 6(d) - Time computation
"""

from enum import Enum
from typing import Dict


class Jurisdiction(str, Enum):
    """Court jurisdiction types"""
    FLORIDA_STATE = "state"
    FLORIDA_FEDERAL = "federal"


class ServiceMethod(str, Enum):
    """
    Service method types as recognized by Florida courts
    
    Note: Service method names must match exactly as they appear in court documents
    """
    ELECTRONIC = "electronic"
    EMAIL = "email"
    MAIL = "mail"
    US_MAIL = "u.s. mail"
    USPS = "usps"
    PERSONAL = "personal"
    HAND_DELIVERY = "hand delivery"


# ============================================================================
# SERVICE METHOD EXTENSIONS
# ============================================================================
# Florida R. Jud. Admin. 2.514(b): "When a party may or must act within a specified 
# time after service, 5 days are added after the period would otherwise expire under 
# Rule 2.514(a), if service was by mail or e-mail."
#
# IMPORTANT: As of January 1, 2019, Florida eliminated the 5-day extension for 
# electronic service (email). Only mail service now gets the 5-day extension.
#
# Federal: FRCP 6(d) provides 3 days for both mail and electronic service.
# ============================================================================

SERVICE_EXTENSIONS: Dict[Jurisdiction, Dict[ServiceMethod, int]] = {
    Jurisdiction.FLORIDA_STATE: {
        # Mail service: 5 days extension (FL R. Jud. Admin. 2.514(b))
        ServiceMethod.MAIL: 5,
        ServiceMethod.US_MAIL: 5,
        ServiceMethod.USPS: 5,
        
        # Electronic service: NO extension since January 1, 2019
        # Prior to 2019, email had 5-day extension - now removed
        ServiceMethod.ELECTRONIC: 0,
        ServiceMethod.EMAIL: 0,
        
        # Personal service: No extension
        ServiceMethod.PERSONAL: 0,
        ServiceMethod.HAND_DELIVERY: 0,
    },
    Jurisdiction.FLORIDA_FEDERAL: {
        # Mail service: 3 days extension (FRCP 6(d))
        ServiceMethod.MAIL: 3,
        ServiceMethod.US_MAIL: 3,
        ServiceMethod.USPS: 3,
        
        # Electronic service: 3 days extension (FRCP 6(d))
        # Federal courts treat electronic same as mail
        ServiceMethod.ELECTRONIC: 3,
        ServiceMethod.EMAIL: 3,
        
        # Personal service: No extension
        ServiceMethod.PERSONAL: 0,
        ServiceMethod.HAND_DELIVERY: 0,
    }
}


def get_service_extension_days(jurisdiction: str, service_method: str) -> int:
    """
    Get service method extension days for a given jurisdiction.
    
    This is the authoritative function for determining service extensions.
    All deadline calculations MUST use this function.
    
    Args:
        jurisdiction: Court jurisdiction ('state' or 'federal')
        service_method: Method of service ('mail', 'email', 'personal', etc.)
    
    Returns:
        int: Number of days to add (0, 3, or 5)
    
    Raises:
        ValueError: If jurisdiction or service method is invalid/unknown
    
    Example:
        >>> get_service_extension_days('state', 'mail')
        5
        >>> get_service_extension_days('federal', 'mail')
        3
        >>> get_service_extension_days('state', 'email')
        0  # No extension since 2019
    """
    # Normalize inputs to lowercase
    jurisdiction_lower = jurisdiction.lower().strip()
    service_method_lower = service_method.lower().strip()

    # Normalize jurisdiction to match enum values
    # Accept both "florida_state" and "state" for Florida state courts
    if jurisdiction_lower in ['florida_state', 'florida']:
        jurisdiction_lower = 'state'
    elif jurisdiction_lower in ['florida_federal']:
        jurisdiction_lower = 'federal'

    # Validate jurisdiction
    try:
        jurisdiction_enum = Jurisdiction(jurisdiction_lower)
    except ValueError:
        raise ValueError(
            f"Invalid jurisdiction '{jurisdiction}'. "
            f"Must be one of: state, florida_state, federal"
        )
    
    # Validate service method
    try:
        service_enum = ServiceMethod(service_method_lower)
    except ValueError:
        # Try to find close matches
        valid_methods = [m.value for m in ServiceMethod]
        raise ValueError(
            f"Invalid service method '{service_method}'. "
            f"Must be one of: {', '.join(valid_methods)}"
        )
    
    # Return extension days
    return SERVICE_EXTENSIONS[jurisdiction_enum][service_enum]


def get_rule_citation(jurisdiction: str, service_method: str) -> str:
    """
    Get the official court rule citation for a service extension.
    
    Useful for populating calculation_basis field with legal authority.
    
    Args:
        jurisdiction: Court jurisdiction ('state' or 'federal')
        service_method: Method of service
    
    Returns:
        str: Official rule citation
    
    Example:
        >>> get_rule_citation('state', 'mail')
        'FL R. Jud. Admin. 2.514(b) - Mail service adds 5 days'
    """
    jurisdiction_lower = jurisdiction.lower().strip()
    service_method_lower = service_method.lower().strip()
    
    extension_days = get_service_extension_days(jurisdiction, service_method)
    
    if jurisdiction_lower == 'state':
        if extension_days > 0:
            return f"FL R. Jud. Admin. 2.514(b) - {service_method.title()} service adds {extension_days} days"
        else:
            return f"FL R. Jud. Admin. 2.514(b) - {service_method.title()} service, no extension"
    else:  # federal
        if extension_days > 0:
            return f"FRCP 6(d) - {service_method.title()} service adds {extension_days} days"
        else:
            return f"FRCP 6(d) - {service_method.title()} service, no extension"


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def is_valid_jurisdiction(jurisdiction: str) -> bool:
    """Check if jurisdiction string is valid"""
    try:
        Jurisdiction(jurisdiction.lower().strip())
        return True
    except ValueError:
        return False


def is_valid_service_method(service_method: str) -> bool:
    """Check if service method string is valid"""
    try:
        ServiceMethod(service_method.lower().strip())
        return True
    except ValueError:
        return False


def normalize_service_method(service_method: str) -> str:
    """
    Normalize service method string to canonical form.
    
    Handles common variations:
    - "U.S. Mail" -> "u.s. mail"
    - "USPS" -> "usps"
    - "E-mail" -> "email"
    
    Args:
        service_method: Raw service method string
    
    Returns:
        str: Normalized service method
    
    Raises:
        ValueError: If service method cannot be normalized
    """
    normalized = service_method.lower().strip()
    
    # Handle common variations
    if normalized in ['u.s. mail', 'usps', 'us mail']:
        return ServiceMethod.MAIL.value
    elif normalized in ['e-mail', 'e mail']:
        return ServiceMethod.EMAIL.value
    elif normalized in ['hand delivery', 'hand-delivery']:
        return ServiceMethod.HAND_DELIVERY.value
    
    # Validate it's a known method
    if not is_valid_service_method(normalized):
        raise ValueError(f"Cannot normalize unknown service method: {service_method}")
    
    return normalized
