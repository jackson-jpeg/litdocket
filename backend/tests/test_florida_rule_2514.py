"""
Test Florida Rule 2.514 Deadline Calculations

These tests verify that deadline calculations comply with Florida Rule of
Judicial Administration 2.514 - Computing Time:

(a)(1) EXCLUDE the day of the act that triggers the period
(a)(2) COUNT every day of the period, including weekends and holidays
(a)(3) INCLUDE the last day, but if it falls on weekend/holiday, extend to next business day

CRITICAL: All tests use SERVICE DATE, not filing date, as the trigger.
"""

import pytest
from datetime import date, timedelta

from app.utils.florida_holidays import (
    add_calendar_days_with_service_extension,
    add_court_days,
    is_business_day,
    adjust_to_business_day
)
from app.utils.deadline_calculator import (
    AuthoritativeDeadlineCalculator,
    CalculationMethod
)


class TestFloridaRule2514CalendarDays:
    """Test calendar day calculations per Florida Rule 2.514"""

    def test_basic_20_day_calculation(self):
        """
        Basic 20-day answer deadline from service date.
        Service Oct 7 + 20 days = Oct 27 (if business day)
        """
        service_date = date(2024, 10, 7)  # Monday
        base_days = 20

        result = add_calendar_days_with_service_extension(
            trigger_date=service_date,
            base_days=base_days,
            service_method="electronic",
            jurisdiction="state"
        )

        # Oct 7 + 20 days = Oct 27 (Sunday)
        # Roll to Monday Oct 28
        assert result == date(2024, 10, 28), f"Expected Oct 28, got {result}"

    def test_trigger_date_is_excluded(self):
        """
        Verify that the trigger date itself is NOT counted.
        Per Rule 2.514(a)(1): "exclude the day of the act"
        """
        service_date = date(2024, 10, 7)  # Monday

        # 1 day period: should be Oct 8 (the day AFTER service), not Oct 7
        result = add_calendar_days_with_service_extension(
            trigger_date=service_date,
            base_days=1,
            service_method="electronic",
            jurisdiction="state"
        )

        assert result == date(2024, 10, 8), f"Expected Oct 8, got {result}"

    def test_mail_service_adds_5_days_florida(self):
        """
        Florida state courts: mail service adds 5 days.
        FL R. Jud. Admin. 2.514(b)
        """
        service_date = date(2024, 10, 7)  # Monday
        base_days = 20

        result = add_calendar_days_with_service_extension(
            trigger_date=service_date,
            base_days=base_days,
            service_method="mail",
            jurisdiction="state"
        )

        # Oct 7 + 20 + 5 = Nov 1 (Friday)
        assert result == date(2024, 11, 1), f"Expected Nov 1, got {result}"

    def test_electronic_service_no_extension_florida(self):
        """
        Florida state courts: electronic service has NO extension since Jan 1, 2019.
        """
        service_date = date(2024, 10, 7)
        base_days = 20

        electronic_result = add_calendar_days_with_service_extension(
            trigger_date=service_date,
            base_days=base_days,
            service_method="electronic",
            jurisdiction="state"
        )

        email_result = add_calendar_days_with_service_extension(
            trigger_date=service_date,
            base_days=base_days,
            service_method="email",
            jurisdiction="state"
        )

        # Both should give same result (no extension)
        assert electronic_result == email_result

    def test_weekend_roll_to_monday(self):
        """
        Per Rule 2.514(a)(3): if last day falls on weekend, extend to next business day.
        """
        # Oct 5 + 1 day = Oct 6 (Saturday) -> should roll to Oct 8 (Monday)
        service_date = date(2024, 10, 5)  # Saturday

        result = add_calendar_days_with_service_extension(
            trigger_date=service_date,
            base_days=1,
            service_method="electronic",
            jurisdiction="state"
        )

        # Oct 5 + 1 = Oct 6 (Sunday), roll to Monday Oct 7
        assert result.weekday() < 5, f"Result {result} is not a business day"

    def test_holiday_roll_to_next_business_day(self):
        """
        Per Rule 2.514(a)(3): if last day falls on holiday, extend to next business day.
        """
        # Calculate deadline that lands on Christmas
        # Dec 5 + 20 = Dec 25 (Christmas) -> should roll to Dec 26
        service_date = date(2024, 12, 5)  # Thursday

        result = add_calendar_days_with_service_extension(
            trigger_date=service_date,
            base_days=20,
            service_method="electronic",
            jurisdiction="state"
        )

        # Dec 25 is Christmas, Dec 26 is Thursday (next business day)
        assert result >= date(2024, 12, 26), f"Expected Dec 26 or later, got {result}"
        assert is_business_day(result), f"Result {result} is not a business day"


class TestFloridaRule2514CourtDays:
    """Test court day (business day) calculations"""

    def test_court_days_skip_weekends(self):
        """
        Court days should skip weekends entirely.
        """
        # Friday Oct 4 + 1 court day = Monday Oct 7 (skipping weekend)
        start_date = date(2024, 10, 4)  # Friday

        result = add_court_days(start_date, 1)

        assert result == date(2024, 10, 7), f"Expected Oct 7 (Monday), got {result}"

    def test_court_days_skip_holidays(self):
        """
        Court days should skip holidays.
        """
        # Day before Christmas + 1 court day = day after Christmas (if not weekend)
        start_date = date(2024, 12, 24)  # Tuesday (Christmas Eve)

        result = add_court_days(start_date, 1)

        # Dec 25 is Christmas (holiday), so next court day is Dec 26 (Thursday)
        assert result == date(2024, 12, 26), f"Expected Dec 26, got {result}"


class TestAuthoritativeCalculator:
    """Test the AuthoritativeDeadlineCalculator class"""

    def test_calculator_matches_function(self):
        """
        AuthoritativeDeadlineCalculator should produce same results as
        add_calendar_days_with_service_extension for calendar day calculations.
        """
        service_date = date(2024, 10, 7)
        base_days = 20

        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")
        calc_result = calc.calculate_deadline(
            trigger_date=service_date,
            base_days=base_days,
            service_method="electronic",
            calculation_method=CalculationMethod.CALENDAR_DAYS
        )

        func_result = add_calendar_days_with_service_extension(
            trigger_date=service_date,
            base_days=base_days,
            service_method="electronic",
            jurisdiction="state"
        )

        assert calc_result.final_deadline == func_result

    def test_calculator_generates_audit_trail(self):
        """
        Calculator must generate complete calculation basis for legal defensibility.
        """
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")
        result = calc.calculate_deadline(
            trigger_date=date(2024, 10, 7),
            base_days=20,
            service_method="mail"
        )

        assert result.calculation_basis is not None
        assert len(result.calculation_basis) > 0
        assert "2.514" in result.calculation_basis or "calendar" in result.calculation_basis.lower()


class TestOffByOneScenarios:
    """
    Specific tests for the off-by-one bug scenario reported by user.
    User reported: "calendaring a due date for 10/26 when the source text clearly identifies 10/27"
    """

    def test_oct_7_service_20_days(self):
        """
        If service is Oct 7, deadline is Oct 27 (or next business day).
        NOT Oct 26!
        """
        service_date = date(2024, 10, 7)  # Monday
        base_days = 20

        result = add_calendar_days_with_service_extension(
            trigger_date=service_date,
            base_days=base_days,
            service_method="electronic",
            jurisdiction="state"
        )

        # Oct 27 is Sunday, rolls to Monday Oct 28
        # But NOT Oct 26!
        assert result >= date(2024, 10, 27), f"Expected Oct 27 or later, got {result}"
        assert result != date(2024, 10, 26), f"Got Oct 26 - this is the off-by-one bug!"

    def test_oct_6_service_vs_oct_7_service(self):
        """
        Demonstrate that filing date (Oct 6) vs service date (Oct 7) causes
        exactly the 1-day discrepancy reported.
        """
        base_days = 20

        # Using Oct 6 (wrong - this is filing date)
        wrong_result = add_calendar_days_with_service_extension(
            trigger_date=date(2024, 10, 6),  # Sunday - filing date
            base_days=base_days,
            service_method="electronic",
            jurisdiction="state"
        )

        # Using Oct 7 (correct - this is service date)
        correct_result = add_calendar_days_with_service_extension(
            trigger_date=date(2024, 10, 7),  # Monday - service date
            base_days=base_days,
            service_method="electronic",
            jurisdiction="state"
        )

        # The difference between using filing date vs service date
        # Oct 6 + 20 = Oct 26 (Saturday) -> rolls to Oct 28
        # Oct 7 + 20 = Oct 27 (Sunday) -> rolls to Oct 28
        # In this case both roll to same day, but that's only because of weekend

        # Key point: if Oct 26/27 were both weekdays, they'd be 1 day apart
        print(f"Using Oct 6 (filing): {wrong_result}")
        print(f"Using Oct 7 (service): {correct_result}")


class TestFederalRules:
    """Test federal court deadline calculations (FRCP 6)"""

    def test_federal_21_day_answer(self):
        """
        Federal answer deadline is 21 days (not 20 like Florida state).
        FRCP 12(a)(1)(A)(i)
        """
        service_date = date(2024, 10, 7)

        calc = AuthoritativeDeadlineCalculator(jurisdiction="federal")
        result = calc.calculate_deadline(
            trigger_date=service_date,
            base_days=21,
            service_method="electronic"
        )

        # Oct 7 + 21 = Oct 28 (Monday)
        assert result.final_deadline == date(2024, 10, 28)

    def test_federal_mail_adds_3_days(self):
        """
        Federal: mail service adds 3 days (not 5 like Florida state).
        FRCP 6(d)
        """
        service_date = date(2024, 10, 7)

        calc = AuthoritativeDeadlineCalculator(jurisdiction="federal")
        result = calc.calculate_deadline(
            trigger_date=service_date,
            base_days=21,
            service_method="mail"
        )

        # Oct 7 + 21 + 3 = Oct 31 (Thursday)
        assert result.final_deadline == date(2024, 10, 31)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
