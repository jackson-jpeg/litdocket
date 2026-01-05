"""
Calendar Service - Handles holidays, weekends, and business day calculations
CompuLaw-inspired: "Court holidays vary by county/state"
"""
from datetime import date, timedelta
from typing import List, Set


class CalendarService:
    """Service for calendar operations, holiday logic, and business day calculations"""

    def __init__(self):
        # Load holiday calendars
        self.federal_holidays = self._load_federal_holidays()
        self.florida_state_holidays = self._load_florida_state_holidays()

    def _load_federal_holidays(self) -> Set[date]:
        """Load federal court holidays for current and next year"""
        holidays = set()

        # 2026 Federal Holidays
        holidays.add(date(2026, 1, 1))   # New Year's Day
        holidays.add(date(2026, 1, 19))  # Martin Luther King Jr. Day
        holidays.add(date(2026, 2, 16))  # Presidents' Day
        holidays.add(date(2026, 5, 25))  # Memorial Day
        holidays.add(date(2026, 6, 19))  # Juneteenth
        holidays.add(date(2026, 7, 3))   # Independence Day (observed)
        holidays.add(date(2026, 9, 7))   # Labor Day
        holidays.add(date(2026, 10, 12)) # Columbus Day
        holidays.add(date(2026, 11, 11)) # Veterans Day
        holidays.add(date(2026, 11, 26)) # Thanksgiving
        holidays.add(date(2026, 12, 25)) # Christmas

        # 2027 Federal Holidays
        holidays.add(date(2027, 1, 1))   # New Year's Day
        holidays.add(date(2027, 1, 18))  # Martin Luther King Jr. Day
        holidays.add(date(2027, 2, 15))  # Presidents' Day
        holidays.add(date(2027, 5, 31))  # Memorial Day
        holidays.add(date(2027, 6, 18))  # Juneteenth (observed)
        holidays.add(date(2027, 7, 5))   # Independence Day (observed)
        holidays.add(date(2027, 9, 6))   # Labor Day
        holidays.add(date(2027, 10, 11)) # Columbus Day
        holidays.add(date(2027, 11, 11)) # Veterans Day
        holidays.add(date(2027, 11, 25)) # Thanksgiving
        holidays.add(date(2027, 12, 24)) # Christmas (observed)

        return holidays

    def _load_florida_state_holidays(self) -> Set[date]:
        """Load Florida state court holidays"""
        holidays = set()

        # Florida has same federal holidays plus:
        holidays.update(self.federal_holidays)

        # Add Florida-specific holidays if any
        # (Florida generally follows federal holiday schedule)

        return holidays

    def is_weekend(self, check_date: date) -> bool:
        """Check if date is a weekend (Saturday=5, Sunday=6)"""
        return check_date.weekday() >= 5

    def is_holiday(self, check_date: date, jurisdiction: str = "florida_state") -> bool:
        """Check if date is a court holiday"""
        if jurisdiction == "federal":
            return check_date in self.federal_holidays
        elif jurisdiction == "florida_state":
            return check_date in self.florida_state_holidays
        return False

    def is_court_day(self, check_date: date, jurisdiction: str = "florida_state") -> bool:
        """Check if date is a valid court day (not weekend or holiday)"""
        return not (self.is_weekend(check_date) or self.is_holiday(check_date, jurisdiction))

    def next_court_day(self, start_date: date, jurisdiction: str = "florida_state") -> date:
        """Get next valid court day after given date"""
        next_day = start_date
        while not self.is_court_day(next_day, jurisdiction):
            next_day += timedelta(days=1)
        return next_day

    def adjust_for_holidays_and_weekends(
        self,
        target_date: date,
        jurisdiction: str = "florida_state"
    ) -> date:
        """
        Adjust date forward if it falls on weekend or holiday
        If deadline falls on Saturday, Sunday, or holiday, move to next court day
        """
        adjusted_date = target_date

        # Keep moving forward until we find a valid court day
        while not self.is_court_day(adjusted_date, jurisdiction):
            adjusted_date += timedelta(days=1)

        return adjusted_date

    def add_business_days(
        self,
        start_date: date,
        num_days: int,
        jurisdiction: str = "florida_state"
    ) -> date:
        """
        Add business days (court days) to a date
        Skips weekends and holidays
        """
        current_date = start_date
        days_added = 0

        while days_added < num_days:
            current_date += timedelta(days=1)
            if self.is_court_day(current_date, jurisdiction):
                days_added += 1

        return current_date

    def subtract_business_days(
        self,
        start_date: date,
        num_days: int,
        jurisdiction: str = "florida_state"
    ) -> date:
        """
        Subtract business days (court days) from a date
        Skips weekends and holidays
        """
        current_date = start_date
        days_subtracted = 0

        while days_subtracted < num_days:
            current_date -= timedelta(days=1)
            if self.is_court_day(current_date, jurisdiction):
                days_subtracted += 1

        return current_date

    def count_business_days_between(
        self,
        start_date: date,
        end_date: date,
        jurisdiction: str = "florida_state"
    ) -> int:
        """Count business days between two dates"""
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        count = 0
        current_date = start_date

        while current_date < end_date:
            if self.is_court_day(current_date, jurisdiction):
                count += 1
            current_date += timedelta(days=1)

        return count

    def get_holidays_in_range(
        self,
        start_date: date,
        end_date: date,
        jurisdiction: str = "florida_state"
    ) -> List[date]:
        """Get all holidays within a date range"""
        holiday_set = (
            self.federal_holidays if jurisdiction == "federal"
            else self.florida_state_holidays
        )

        holidays_in_range = [
            holiday for holiday in holiday_set
            if start_date <= holiday <= end_date
        ]

        return sorted(holidays_in_range)


# Singleton instance
calendar_service = CalendarService()
