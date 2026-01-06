"""
Florida Court Holidays - State and Federal
Updated calendar for accurate deadline calculations
"""
from datetime import date
from typing import List


def get_federal_holidays(year: int) -> List[date]:
    """
    Get federal holidays that Florida courts observe

    Federal holidays when courts are closed:
    - New Year's Day (January 1)
    - Martin Luther King Jr. Day (3rd Monday in January)
    - Presidents' Day (3rd Monday in February)
    - Memorial Day (last Monday in May)
    - Juneteenth (June 19) - NEW since 2021
    - Independence Day (July 4)
    - Labor Day (1st Monday in September)
    - Columbus Day (2nd Monday in October) - Federal courts only
    - Veterans Day (November 11)
    - Thanksgiving (4th Thursday in November)
    - Christmas Day (December 25)
    """

    from datetime import datetime

    holidays = []

    # New Year's Day (January 1)
    holidays.append(date(year, 1, 1))

    # Martin Luther King Jr. Day (3rd Monday in January)
    holidays.append(get_nth_weekday(year, 1, 0, 3))  # 0=Monday, 3rd occurrence

    # Presidents' Day (3rd Monday in February)
    holidays.append(get_nth_weekday(year, 2, 0, 3))

    # Memorial Day (last Monday in May)
    holidays.append(get_last_weekday(year, 5, 0))  # Last Monday in May

    # Juneteenth (June 19) - Added as federal holiday in 2021
    if year >= 2021:
        holidays.append(date(year, 6, 19))

    # Independence Day (July 4)
    holidays.append(date(year, 7, 4))

    # Labor Day (1st Monday in September)
    holidays.append(get_nth_weekday(year, 9, 0, 1))

    # Columbus Day (2nd Monday in October) - Federal courts observe
    holidays.append(get_nth_weekday(year, 10, 0, 2))

    # Veterans Day (November 11)
    holidays.append(date(year, 11, 11))

    # Thanksgiving (4th Thursday in November)
    holidays.append(get_nth_weekday(year, 11, 3, 4))  # 3=Thursday, 4th occurrence

    # Christmas Day (December 25)
    holidays.append(date(year, 12, 25))

    # If holiday falls on weekend, observe on adjacent weekday
    # CRITICAL: Use timedelta to avoid month boundary crashes (Jan 1, Dec 31, etc.)
    from datetime import timedelta
    adjusted_holidays = []
    for holiday in holidays:
        if holiday.weekday() == 5:  # Saturday -> observe on Friday
            adjusted = holiday - timedelta(days=1)
            adjusted_holidays.append(adjusted)
        elif holiday.weekday() == 6:  # Sunday -> observe on Monday
            adjusted = holiday + timedelta(days=1)
            adjusted_holidays.append(adjusted)
        else:
            adjusted_holidays.append(holiday)

    return adjusted_holidays


def get_florida_state_holidays(year: int) -> List[date]:
    """
    Florida state holidays (in addition to federal holidays)

    Florida state courts also close for:
    - Good Friday (Friday before Easter)
    - Day after Thanksgiving (sometimes)
    """

    holidays = []

    # Good Friday (calculate Easter, then subtract 2 days)
    easter = calculate_easter(year)
    from datetime import timedelta
    good_friday = easter - timedelta(days=2)
    holidays.append(good_friday)

    # Day after Thanksgiving (4th Thursday in November + 1 day)
    thanksgiving = get_nth_weekday(year, 11, 3, 4)
    from datetime import timedelta
    day_after_thanksgiving = thanksgiving + timedelta(days=1)
    holidays.append(day_after_thanksgiving)

    return holidays


def get_all_court_holidays(year: int) -> List[date]:
    """Get all holidays when Florida courts are closed (federal + state)"""
    federal = get_federal_holidays(year)
    state = get_florida_state_holidays(year)
    all_holidays = list(set(federal + state))  # Remove duplicates
    return sorted(all_holidays)


def is_court_holiday(check_date: date) -> bool:
    """Check if a specific date is a court holiday"""
    holidays = get_all_court_holidays(check_date.year)
    return check_date in holidays


def is_business_day(check_date: date) -> bool:
    """Check if a date is a business day (not weekend or holiday)"""
    if check_date.weekday() >= 5:  # Saturday or Sunday
        return False
    if is_court_holiday(check_date):
        return False
    return True


def get_next_business_day(start_date: date) -> date:
    """Get the next business day after the given date"""
    from datetime import timedelta
    current = start_date + timedelta(days=1)
    while not is_business_day(current):
        current += timedelta(days=1)
    return current


def adjust_to_business_day(target_date: date) -> date:
    """
    If date falls on weekend/holiday, adjust to next business day

    This implements Florida Rule 2.514(a):
    'When a deadline falls on a weekend or legal holiday,
    it is extended to the next business day.'
    """
    if is_business_day(target_date):
        return target_date
    return get_next_business_day(target_date)


def add_court_days(start_date: date, court_days: int) -> date:
    """
    Add a specified number of COURT DAYS (business days) to a date

    Court days skip weekends and holidays. This is critical for legal deadlines
    specified as "X court days" vs "X calendar days".

    Examples:
        - Add 5 court days starting Friday → Next Friday (skips weekend)
        - Add 30 court days from May 1 → June 10 (skips Memorial Day, weekends)

    Args:
        start_date: Starting date
        court_days: Number of court/business days to add (positive integer)

    Returns:
        Date that is court_days business days after start_date

    Note: Florida Rule 2.514 - Court days exclude weekends and legal holidays
    """
    from datetime import timedelta

    if court_days < 0:
        raise ValueError("court_days must be positive. Use subtract_court_days for negative.")

    current = start_date
    days_added = 0

    while days_added < court_days:
        current += timedelta(days=1)
        if is_business_day(current):
            days_added += 1

    return current


def subtract_court_days(start_date: date, court_days: int) -> date:
    """
    Subtract a specified number of COURT DAYS (business days) from a date

    This is used for calculating deadlines that are "X days BEFORE" a trigger event.

    Examples:
        - Trial date is June 15, MSJ due 30 court days before
        - Subtract 30 court days from June 15 → May 5 (skips weekends/holidays)

    Args:
        start_date: Starting date (e.g., trial date)
        court_days: Number of court days to go back (positive integer)

    Returns:
        Date that is court_days business days before start_date
    """
    from datetime import timedelta

    if court_days < 0:
        raise ValueError("court_days must be positive")

    current = start_date
    days_subtracted = 0

    while days_subtracted < court_days:
        current -= timedelta(days=1)
        if is_business_day(current):
            days_subtracted += 1

    return current


def count_court_days_between(start_date: date, end_date: date) -> int:
    """
    Count the number of court days (business days) between two dates

    Useful for reporting: "You have 15 court days until the deadline"

    Args:
        start_date: Beginning date
        end_date: Ending date

    Returns:
        Number of business days between the dates (exclusive of start, inclusive of end)
    """
    from datetime import timedelta

    if start_date >= end_date:
        return 0

    current = start_date
    court_days = 0

    while current < end_date:
        current += timedelta(days=1)
        if is_business_day(current):
            court_days += 1

    return court_days


def add_calendar_days_with_service_extension(
    trigger_date: date,
    base_days: int,
    service_method: str = "electronic",
    jurisdiction: str = "state"
) -> date:
    """
    Calculate deadline with service method extensions (Phase 3 - Service Math)

    Uses authoritative legal rules for service extensions:
    - Florida State: Mail adds 5 days (FL R. Jud. Admin. 2.514(b))
    - Federal: Mail/Electronic adds 3 days (FRCP 6(d))

    CRITICAL: This function now uses jurisdiction-specific rules from legal_rules.py
    to ensure accurate deadline calculations for both state and federal courts.

    This is THE critical function for accurate deadline calculation.

    Examples:
        - Document filed on June 1, 20 days to respond, e-service, Florida state:
          → June 1 + 20 calendar days = June 21 (no extension for email since 2019)

        - Document filed on June 1, 20 days to respond, mail service, Florida state:
          → June 1 + 20 + 5 = June 26 (then adjust for weekends/holidays)

        - Document filed on June 1, 21 days to respond, mail service, Federal:
          → June 1 + 21 + 3 = June 25 (then adjust for weekends/holidays)

    Args:
        trigger_date: Date of service/filing
        base_days: Base response period (e.g., 20 days per FRCP)
        service_method: "electronic", "mail", or "hand_delivery"
        jurisdiction: "state" for Florida state courts, "federal" for federal courts

    Returns:
        Final deadline date (adjusted for business days if needed)
    """
    from datetime import timedelta
    from app.constants.legal_rules import get_service_extension_days

    # Start with base calculation
    total_days = base_days

    # Add service method extension using authoritative legal rules
    try:
        service_extension = get_service_extension_days(jurisdiction, service_method)
        total_days += service_extension
    except ValueError:
        # Unknown service method - default to 0 days (no extension)
        total_days += 0

    # Calculate deadline (calendar days, not court days)
    deadline = trigger_date + timedelta(days=total_days)

    # Apply Florida Rule 2.514(a) - if deadline falls on weekend/holiday, roll to next business day
    deadline_adjusted = adjust_to_business_day(deadline)

    return deadline_adjusted


# Helper functions for calculating floating holidays

def get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """
    Get the nth occurrence of a weekday in a month

    Args:
        year: Year
        month: Month (1-12)
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        n: Which occurrence (1=first, 2=second, etc.)
    """
    from datetime import datetime, timedelta

    # First day of the month
    first_day = date(year, month, 1)

    # Find first occurrence of target weekday
    days_ahead = (weekday - first_day.weekday()) % 7
    first_occurrence = first_day + timedelta(days=days_ahead)

    # Add weeks to get nth occurrence
    nth_occurrence = first_occurrence + timedelta(weeks=n-1)

    return nth_occurrence


def get_last_weekday(year: int, month: int, weekday: int) -> date:
    """Get the last occurrence of a weekday in a month"""
    from datetime import timedelta

    # Start with last day of month
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    # Work backwards to find last occurrence of target weekday
    days_back = (last_day.weekday() - weekday) % 7
    last_occurrence = last_day - timedelta(days=days_back)

    return last_occurrence


def calculate_easter(year: int) -> date:
    """
    Calculate Easter Sunday using Computus algorithm
    (Gregorian calendar, valid for years 1583-4099)
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1

    return date(year, month, day)


# Utility function to print holidays for a year
def print_holidays_for_year(year: int):
    """Print all court holidays for a given year (for testing/reference)"""
    holidays = get_all_court_holidays(year)

    print(f"\nFlorida Court Holidays for {year}:")
    print("=" * 50)
    for holiday in holidays:
        day_name = holiday.strftime("%A")
        date_str = holiday.strftime("%B %d, %Y")
        print(f"{date_str} ({day_name})")


# Example usage
if __name__ == "__main__":
    # Test for 2025
    print_holidays_for_year(2025)

    # Test specific dates
    test_dates = [
        date(2025, 7, 4),   # July 4 (Independence Day)
        date(2025, 7, 5),   # Day after (Saturday)
        date(2025, 12, 25), # Christmas
        date(2025, 1, 20),  # MLK Day
    ]

    print("\n\nTesting specific dates:")
    print("=" * 50)
    for test_date in test_dates:
        is_holiday = is_court_holiday(test_date)
        is_biz_day = is_business_day(test_date)
        print(f"{test_date.strftime('%Y-%m-%d (%A)')}: Holiday={is_holiday}, Business Day={is_biz_day}")
