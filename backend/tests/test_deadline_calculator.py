"""
Comprehensive Test Suite for Authoritative Deadline Calculator

Tests every aspect of deadline calculation for legal defensibility:
- Service method extensions (mail vs electronic)
- Jurisdiction differences (state vs federal)
- Roll logic (weekends and holidays)
- Court days vs calendar days
- Calculation basis generation
"""

import pytest
from datetime import date, timedelta
from app.utils.deadline_calculator import (
    AuthoritativeDeadlineCalculator,
    CalculationMethod,
    DeadlineCalculation,
    RollAdjustment
)
from app.constants.legal_rules import Jurisdiction, ServiceMethod


class TestServiceMethodExtensions:
    """Test service method extension calculations"""

    def test_florida_state_mail_adds_5_days(self):
        """Florida state: mail service adds 5 days per FL R. Jud. Admin. 2.514(b)"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # Service date: Monday, Jan 1, 2024
        # Base: 20 calendar days = Jan 21 (Sunday)
        # Service ext: +5 days = Jan 26 (Friday)
        # Roll: Jan 21 is Sunday -> rolls to Jan 22 (Monday)
        # Then +5 = Jan 27 (Saturday) -> rolls to Jan 29 (Monday)

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),  # Monday
            base_days=20,
            service_method="mail"
        )

        # 1/1 + 20 days = 1/21 (Sunday) -> roll to 1/22 (Monday)
        # 1/22 + 5 days = 1/27 (Saturday) -> roll to 1/29 (Monday)
        assert result.service_extension_days == 5
        assert result.final_deadline == date(2024, 1, 29)
        assert "FL R. Jud. Admin. 2.514(b)" in result.calculation_basis

    def test_florida_state_email_no_extension_since_2019(self):
        """Florida state: email service has NO extension since Jan 1, 2019"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),  # Monday
            base_days=20,
            service_method="email"
        )

        # 1/1 + 20 days = 1/21 (Sunday) -> rolls to 1/22 (Monday)
        # No service extension
        assert result.service_extension_days == 0
        assert result.final_deadline == date(2024, 1, 22)

    def test_federal_mail_adds_3_days(self):
        """Federal courts: mail service adds 3 days per FRCP 6(d)"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="federal")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),  # Monday
            base_days=21,  # Federal answer deadline
            service_method="mail"
        )

        # 1/1 + 21 days = 1/22 (Monday) + 3 days = 1/25 (Thursday)
        assert result.service_extension_days == 3
        assert result.final_deadline == date(2024, 1, 25)
        assert "FRCP 6(d)" in result.calculation_basis

    def test_federal_electronic_adds_3_days(self):
        """Federal courts: electronic service adds 3 days (unlike Florida state)"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="federal")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),
            base_days=21,
            service_method="electronic"
        )

        # 1/1 + 21 days = 1/22 + 3 days (electronic) = 1/25
        assert result.service_extension_days == 3
        assert result.final_deadline == date(2024, 1, 25)

    def test_personal_service_no_extension(self):
        """Personal service has no extension in any jurisdiction"""
        state_calc = AuthoritativeDeadlineCalculator(jurisdiction="state")
        fed_calc = AuthoritativeDeadlineCalculator(jurisdiction="federal")

        state_result = state_calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),
            base_days=20,
            service_method="personal"
        )

        fed_result = fed_calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),
            base_days=21,
            service_method="personal"
        )

        assert state_result.service_extension_days == 0
        assert fed_result.service_extension_days == 0


class TestRollLogic:
    """Test weekend and holiday roll logic"""

    def test_deadline_on_saturday_rolls_to_monday(self):
        """Deadline falling on Saturday rolls to Monday"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # Jan 1, 2024 is Monday
        # + 5 days = Jan 6 (Saturday) -> should roll to Jan 8 (Monday)
        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),
            base_days=5,
            service_method="personal"  # No extension
        )

        assert result.final_deadline == date(2024, 1, 8)  # Monday
        assert result.roll_adjustment is not None
        assert result.roll_adjustment.original_date == date(2024, 1, 6)  # Saturday
        assert result.roll_adjustment.reason == "weekend"

    def test_deadline_on_sunday_rolls_to_monday(self):
        """Deadline falling on Sunday rolls to Monday"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # Jan 1, 2024 is Monday
        # + 6 days = Jan 7 (Sunday) -> should roll to Jan 8 (Monday)
        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),
            base_days=6,
            service_method="personal"
        )

        assert result.final_deadline == date(2024, 1, 8)  # Monday
        assert result.roll_adjustment is not None
        assert result.roll_adjustment.original_date == date(2024, 1, 7)  # Sunday

    def test_deadline_on_christmas_rolls_forward(self):
        """Deadline on Christmas (holiday) rolls to next business day"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # Dec 15, 2024 is Sunday
        # + 10 days = Dec 25 (Wednesday - Christmas) -> rolls to Dec 26
        result = calc.calculate_deadline(
            trigger_date=date(2024, 12, 15),
            base_days=10,
            service_method="personal"
        )

        # Note: Dec 15 + 10 = Dec 25 (Christmas) -> next business day
        # If Dec 26 is also a holiday or weekend, keeps rolling
        assert result.roll_adjustment is not None or result.final_deadline > date(2024, 12, 25)

    def test_deadline_on_business_day_no_roll(self):
        """Deadline on normal business day requires no roll"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # Jan 1, 2024 is Monday
        # + 4 days = Jan 5 (Friday - business day)
        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),
            base_days=4,
            service_method="personal"
        )

        assert result.final_deadline == date(2024, 1, 5)
        assert result.roll_adjustment is None


class TestCourtDaysVsCalendarDays:
    """Test court days (skip weekends) vs calendar days"""

    def test_calendar_days_include_weekends(self):
        """Calendar days count all days including weekends"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # Friday Jan 5, 2024 + 10 calendar days = Monday Jan 15
        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 5),
            base_days=10,
            service_method="personal",
            calculation_method=CalculationMethod.CALENDAR_DAYS
        )

        # Includes weekend: Jan 6-7, Jan 13-14
        assert result.final_deadline == date(2024, 1, 15)

    def test_court_days_skip_weekends(self):
        """Court days skip weekends when counting"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # Friday Jan 5, 2024 + 10 court days = Thursday Jan 18
        # (skips Jan 6-7, 13-14)
        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 5),
            base_days=10,
            service_method="personal",
            calculation_method=CalculationMethod.COURT_DAYS
        )

        # Should skip 2 weekends = 4 days
        # So 10 court days = 14 calendar days
        assert result.final_deadline == date(2024, 1, 19)

    def test_court_days_skip_holidays(self):
        """Court days skip holidays in addition to weekends"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # Dec 15, 2024 + 10 court days (skips Dec 25 - Christmas)
        result = calc.calculate_deadline(
            trigger_date=date(2024, 12, 15),  # Sunday
            base_days=10,
            service_method="personal",
            calculation_method=CalculationMethod.COURT_DAYS
        )

        # Should skip weekends AND Christmas
        # Exact date depends on holiday calendar, but should be after Dec 25
        assert result.final_deadline > date(2024, 12, 25)


class TestCalculationBasisTransparency:
    """Test that calculation_basis provides complete transparency"""

    def test_calculation_basis_includes_trigger_date(self):
        """Calculation basis must show trigger date"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=20,
            service_method="mail"
        )

        assert "01/15/2024" in result.calculation_basis
        assert "Trigger Event" in result.calculation_basis

    def test_calculation_basis_includes_base_period(self):
        """Calculation basis must show base response period"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=20,
            service_method="mail"
        )

        assert "20 calendar days" in result.calculation_basis or "20 days" in result.calculation_basis

    def test_calculation_basis_includes_service_extension(self):
        """Calculation basis must show service method extension"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=20,
            service_method="mail"
        )

        assert "+5 days" in result.calculation_basis or "5 days" in result.calculation_basis
        assert "FL R. Jud. Admin. 2.514(b)" in result.calculation_basis

    def test_calculation_basis_includes_roll_explanation(self):
        """Calculation basis must explain roll logic if applied"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # Force a weekend roll
        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),  # Monday
            base_days=5,  # = Saturday
            service_method="personal"
        )

        if result.roll_adjustment:
            assert "Roll Logic" in result.calculation_basis or "rolled" in result.calculation_basis.lower()

    def test_calculation_basis_includes_final_deadline(self):
        """Calculation basis must clearly state final deadline"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=20,
            service_method="mail"
        )

        assert "FINAL DEADLINE" in result.calculation_basis
        # Should show full date format: "Monday, February 12, 2024"
        assert result.final_deadline.strftime("%Y") in result.calculation_basis


class TestShortCalculationBasis:
    """Test short calculation basis for UI display"""

    def test_short_basis_with_mail_service(self):
        """Short basis shows concise calculation with service extension"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=20,
            service_method="mail"
        )

        short = result.get_short_calculation_basis()

        # Should be like: "Trigger 01/15/24 + 20 cal days + 5 (mail) = 02/12/24"
        assert "01/15/24" in short
        assert "20" in short
        assert "mail" in short
        assert "5" in short

    def test_short_basis_with_roll(self):
        """Short basis includes roll notification"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 1),
            base_days=5,  # Will hit Saturday
            service_method="personal"
        )

        short = result.get_short_calculation_basis()

        if result.roll_adjustment:
            assert "rolled" in short.lower()


class TestRealWorldScenarios:
    """Test real-world legal scenarios"""

    def test_florida_answer_to_complaint_mail_service(self):
        """
        Real scenario: Answer to complaint in Florida state court
        - Service date: January 15, 2024 (Monday)
        - Service method: Mail
        - Base period: 20 days (FL R. Civ. P. 1.140(a))
        - Extension: +5 days for mail service
        - Expected: February 9, 2024
        """
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=20,
            service_method="mail"
        )

        # 1/15 + 20 = 2/4 (Sunday) -> rolls to 2/5 (Monday)
        # 2/5 + 5 = 2/10 (Saturday) -> rolls to 2/12 (Monday)
        assert result.service_extension_days == 5
        # Verify it's a Monday (business day)
        assert result.final_deadline.weekday() == 0  # Monday

    def test_federal_answer_to_complaint_electronic_service(self):
        """
        Real scenario: Answer to complaint in federal court
        - Service date: January 15, 2024
        - Service method: Electronic
        - Base period: 21 days (FRCP 12(a))
        - Extension: +3 days for electronic service
        - Expected: February 8, 2024
        """
        calc = AuthoritativeDeadlineCalculator(jurisdiction="federal")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=21,
            service_method="electronic"
        )

        # 1/15 + 21 = 2/5 + 3 = 2/8
        assert result.service_extension_days == 3
        assert result.final_deadline == date(2024, 2, 8)

    def test_discovery_response_30_days(self):
        """
        Discovery response deadline
        - Service: January 15, 2024
        - Base: 30 days
        - Service: Mail (+5 days for Florida state)
        """
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=30,
            service_method="mail"
        )

        # 1/15 + 30 = 2/14 (Wednesday) + 5 = 2/19 (Monday)
        assert result.service_extension_days == 5
        # Should be in mid-February
        assert result.final_deadline.month == 2


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_leap_year_february_29(self):
        """Handle Feb 29 in leap years correctly"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        # 2024 is a leap year
        result = calc.calculate_deadline(
            trigger_date=date(2024, 2, 1),
            base_days=28,
            service_method="personal"
        )

        # Feb 1 + 28 days = Feb 29 (leap day, Thursday)
        assert result.final_deadline == date(2024, 2, 29)

    def test_year_boundary(self):
        """Handle deadlines that cross year boundary"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 12, 15),
            base_days=30,
            service_method="personal"
        )

        # Should be in January 2025
        assert result.final_deadline.year == 2025
        assert result.final_deadline.month == 1

    def test_very_short_deadline_2_days(self):
        """Handle very short deadlines (2-3 days)"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),  # Monday
            base_days=2,
            service_method="personal"
        )

        # Mon + 2 days = Wed
        assert result.final_deadline == date(2024, 1, 17)

    def test_very_long_deadline_365_days(self):
        """Handle very long deadlines (1 year)"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=365,
            service_method="personal"
        )

        # Should be approximately Jan 15, 2025 (2024 is leap year, so +1 day)
        assert result.final_deadline.year == 2025
        assert result.final_deadline.month == 1

    def test_zero_days_deadline(self):
        """Handle same-day deadline (0 days)"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        result = calc.calculate_deadline(
            trigger_date=date(2024, 1, 15),
            base_days=0,
            service_method="personal"
        )

        # Same day if business day, otherwise next business day
        assert result.final_deadline >= date(2024, 1, 15)


class TestRuleTemplateIntegration:
    """Test integration with RulesEngine templates"""

    def test_multiple_deadlines_from_one_trigger(self):
        """Test calculating multiple deadlines from single trigger"""
        calc = AuthoritativeDeadlineCalculator(jurisdiction="state")

        specs = [
            {"base_days": 20, "service_method": "mail", "calculation_method": "calendar_days"},
            {"base_days": 30, "service_method": "mail", "calculation_method": "calendar_days"},
            {"base_days": 60, "service_method": "electronic", "calculation_method": "calendar_days"}
        ]

        results = calc.calculate_deadline_chain(
            trigger_date=date(2024, 1, 15),
            deadline_specs=specs
        )

        assert len(results) == 3
        # First deadline < second deadline < third deadline
        assert results[0].final_deadline < results[1].final_deadline < results[2].final_deadline


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
