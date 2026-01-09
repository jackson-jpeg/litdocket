/**
 * SovereignCalculator Test Suite
 *
 * Production-grade tests for deadline calculations.
 * Tests edge cases like:
 * - Holiday boundaries
 * - Weekend roll-overs
 * - Mail rule (+3 days)
 * - Retrograde calculations
 */

import {
  SovereignCalculator,
  HolidayManager,
  calculateFederalDeadline,
  calculateStateDeadline,
  isValidFilingDate,
  applyMailRule,
} from '../sovereign-calculator';

describe('HolidayManager', () => {
  describe('Federal Holidays 2025', () => {
    const manager = new HolidayManager({
      year: 2025,
      jurisdictionLevel: 'FEDERAL',
    });

    it('should generate all federal holidays', () => {
      const holidays = manager.getAllHolidays();
      expect(holidays.length).toBeGreaterThanOrEqual(11);
    });

    it('should recognize New Year\'s Day', () => {
      const newYears = new Date(2025, 0, 1);
      expect(manager.isHoliday(newYears)).toBe(true);
    });

    it('should recognize MLK Day (3rd Monday of January)', () => {
      // 2025: January 20
      const mlkDay = new Date(2025, 0, 20);
      expect(manager.isHoliday(mlkDay)).toBe(true);
    });

    it('should recognize Presidents Day (3rd Monday of February)', () => {
      // 2025: February 17
      const presidentsDay = new Date(2025, 1, 17);
      expect(manager.isHoliday(presidentsDay)).toBe(true);
    });

    it('should recognize Memorial Day (last Monday of May)', () => {
      // 2025: May 26
      const memorialDay = new Date(2025, 4, 26);
      expect(manager.isHoliday(memorialDay)).toBe(true);
    });

    it('should recognize Independence Day', () => {
      const july4 = new Date(2025, 6, 4);
      expect(manager.isHoliday(july4)).toBe(true);
    });

    it('should recognize Labor Day (1st Monday of September)', () => {
      // 2025: September 1
      const laborDay = new Date(2025, 8, 1);
      expect(manager.isHoliday(laborDay)).toBe(true);
    });

    it('should recognize Thanksgiving (4th Thursday of November)', () => {
      // 2025: November 27
      const thanksgiving = new Date(2025, 10, 27);
      expect(manager.isHoliday(thanksgiving)).toBe(true);
    });

    it('should recognize Christmas Day', () => {
      const christmas = new Date(2025, 11, 25);
      expect(manager.isHoliday(christmas)).toBe(true);
    });

    it('should NOT mark random weekday as holiday', () => {
      const randomDay = new Date(2025, 3, 15); // April 15
      expect(manager.isHoliday(randomDay)).toBe(false);
    });
  });

  describe('Weekend Observance', () => {
    it('should observe Saturday holidays on Friday (July 4, 2026)', () => {
      const manager = new HolidayManager({
        year: 2026,
        jurisdictionLevel: 'FEDERAL',
      });
      // July 4, 2026 is Saturday, observed on Friday July 3
      const observed = new Date(2026, 6, 3);
      expect(manager.isHoliday(observed)).toBe(true);
    });
  });
});

describe('SovereignCalculator', () => {
  describe('Basic Calendar Day Calculations', () => {
    const calculator = new SovereignCalculator({
      year: 2025,
      jurisdictionLevel: 'FEDERAL',
    });

    it('should add 21 days (FRCP Answer deadline)', () => {
      const triggerDate = new Date(2025, 0, 6); // Monday, Jan 6
      const result = calculator.calculate(triggerDate, 21, 'CALENDAR');

      // Jan 6 + 21 = Jan 27, 2025 (Monday)
      expect(result.deadlineDate.getDate()).toBe(27);
      expect(result.deadlineDate.getMonth()).toBe(0);
      expect(result.baseDays).toBe(21);
      expect(result.serviceDaysAdded).toBe(0);
    });

    it('should roll forward when landing on Saturday', () => {
      // Find a case where +21 days lands on Saturday
      const triggerDate = new Date(2025, 0, 3); // Friday, Jan 3
      const result = calculator.calculate(triggerDate, 21, 'CALENDAR');

      // Jan 3 + 21 = Jan 24, 2025 (Friday) - no roll needed
      // Let's use a different date
      const triggerDate2 = new Date(2025, 0, 4); // Saturday, Jan 4
      const result2 = calculator.calculate(triggerDate2, 21, 'CALENDAR');

      // Jan 4 + 21 = Jan 25 (Saturday) -> rolled to Jan 27 (Monday)
      expect(result2.deadlineDate.getDay()).not.toBe(0); // Not Sunday
      expect(result2.deadlineDate.getDay()).not.toBe(6); // Not Saturday
    });

    it('should roll forward when landing on Sunday', () => {
      const triggerDate = new Date(2025, 0, 5); // Sunday, Jan 5
      const result = calculator.calculate(triggerDate, 21, 'CALENDAR');

      // Jan 5 + 21 = Jan 26 (Sunday) -> rolled to Jan 27 (Monday)
      expect(result.deadlineDate.getDay()).toBe(1); // Monday
    });

    it('should roll forward when landing on holiday', () => {
      // Find trigger where +days lands on MLK Day (Jan 20, 2025)
      const triggerDate = new Date(2024, 11, 30); // Dec 30, 2024
      const result = calculator.calculate(triggerDate, 21, 'CALENDAR');

      // Dec 30 + 21 = Jan 20 (MLK Day) -> rolled to Jan 21
      expect(result.deadlineDate.getDate()).toBe(21);
      expect(result.holidaysSkipped).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Business Day Calculations', () => {
    const calculator = new SovereignCalculator({
      year: 2025,
      jurisdictionLevel: 'FEDERAL',
    });

    it('should count only business days', () => {
      const triggerDate = new Date(2025, 0, 6); // Monday, Jan 6
      const result = calculator.calculate(triggerDate, 10, 'BUSINESS');

      // 10 business days from Jan 6:
      // Jan 7, 8, 9, 10, (skip 11-12 weekend), 13, 14, 15, 16, 17
      // Should be Jan 17 + MLK Day consideration
      expect(result.weekendsSkipped).toBeGreaterThan(0);
      expect(result.deadlineDate.getDay()).not.toBe(0); // Not Sunday
      expect(result.deadlineDate.getDay()).not.toBe(6); // Not Saturday
    });

    it('should skip weekends when counting', () => {
      const triggerDate = new Date(2025, 0, 10); // Friday
      const result = calculator.calculate(triggerDate, 5, 'BUSINESS');

      // 5 business days: skip Sat (11), Sun (12), count Mon-Fri
      // Should skip 2 weekend days
      expect(result.weekendsSkipped).toBe(2);
    });
  });

  describe('Mail Rule (+3 Days)', () => {
    const calculator = new SovereignCalculator({
      year: 2025,
      jurisdictionLevel: 'FEDERAL',
    });

    it('should add 3 days for certified mail (Federal)', () => {
      const triggerDate = new Date(2025, 0, 6); // Monday
      const result = calculator.calculate(
        triggerDate,
        21,
        'CALENDAR',
        'CERTIFIED_MAIL'
      );

      expect(result.serviceDaysAdded).toBe(3);
      // 21 + 3 = 24 days from Jan 6 = Jan 30
      expect(result.deadlineDate.getDate()).toBe(30);
    });

    it('should add 3 days for first class mail (Federal)', () => {
      const triggerDate = new Date(2025, 0, 6);
      const result = calculator.calculate(
        triggerDate,
        21,
        'CALENDAR',
        'FIRST_CLASS_MAIL'
      );

      expect(result.serviceDaysAdded).toBe(3);
    });

    it('should NOT add days for personal service', () => {
      const triggerDate = new Date(2025, 0, 6);
      const result = calculator.calculate(triggerDate, 21, 'CALENDAR', 'PERSONAL');

      expect(result.serviceDaysAdded).toBe(0);
    });
  });

  describe('State Rules (Florida)', () => {
    const calculator = new SovereignCalculator({
      year: 2025,
      jurisdictionLevel: 'STATE',
      stateCode: 'FL',
    });

    it('should add 5 days for mail service (Florida)', () => {
      const triggerDate = new Date(2025, 0, 6);
      const result = calculator.calculate(
        triggerDate,
        20, // Florida answer deadline is 20 days
        'CALENDAR',
        'CERTIFIED_MAIL'
      );

      expect(result.serviceDaysAdded).toBe(5);
    });

    it('should NOT add days for electronic service (Florida)', () => {
      const triggerDate = new Date(2025, 0, 6);
      const result = calculator.calculate(
        triggerDate,
        20,
        'CALENDAR',
        'ELECTRONIC'
      );

      expect(result.serviceDaysAdded).toBe(0);
    });
  });

  describe('Retrograde Calculations', () => {
    const calculator = new SovereignCalculator({
      year: 2025,
      jurisdictionLevel: 'FEDERAL',
    });

    it('should count backwards for pretrial deadlines', () => {
      // Trial date: March 15, 2025 (Saturday - but let's use Monday March 17)
      const trialDate = new Date(2025, 2, 17); // Monday
      const result = calculator.calculate(trialDate, -14, 'RETROGRADE');

      // 14 business days before March 17
      expect(result.deadlineDate.getTime()).toBeLessThan(trialDate.getTime());
      expect(result.countingMethod).toBe('RETROGRADE');
    });

    it('should skip weekends when counting backwards', () => {
      const trialDate = new Date(2025, 2, 14); // Friday, March 14
      const result = calculator.calculate(trialDate, -5, 'RETROGRADE');

      // 5 business days before Friday March 14
      // Skip Sat 8, Sun 9 -> should land around March 7 (Friday)
      expect(result.weekendsSkipped).toBeGreaterThanOrEqual(2);
      expect(result.deadlineDate.getDay()).not.toBe(0);
      expect(result.deadlineDate.getDay()).not.toBe(6);
    });
  });

  describe('Edge Cases', () => {
    const calculator = new SovereignCalculator({
      year: 2025,
      jurisdictionLevel: 'FEDERAL',
    });

    it('should handle trigger date on weekend', () => {
      const saturdayTrigger = new Date(2025, 0, 4); // Saturday
      const result = calculator.calculate(saturdayTrigger, 21, 'CALENDAR');

      // Should still calculate from the weekend date
      expect(result.triggerDate.getDay()).toBe(6); // Saturday
      expect(result.deadlineDate.getDay()).not.toBe(0);
      expect(result.deadlineDate.getDay()).not.toBe(6);
    });

    it('should handle 0 days (same day deadline)', () => {
      const triggerDate = new Date(2025, 0, 6); // Monday
      const result = calculator.calculate(triggerDate, 0, 'CALENDAR');

      expect(result.deadlineDate.getDate()).toBe(6);
      expect(result.baseDays).toBe(0);
    });

    it('should handle negative days (before trigger)', () => {
      const triggerDate = new Date(2025, 0, 20); // Monday, Jan 20
      const result = calculator.calculate(triggerDate, -10, 'CALENDAR');

      // Should be 10 days before = Jan 10
      expect(result.deadlineDate.getDate()).toBe(10);
    });

    it('should handle year boundary', () => {
      const triggerDate = new Date(2024, 11, 20); // Dec 20, 2024
      const result = calculator.calculate(triggerDate, 21, 'CALENDAR');

      // Should cross into January 2025
      expect(result.deadlineDate.getMonth()).toBe(0); // January
      expect(result.deadlineDate.getFullYear()).toBe(2025);
    });

    it('should create detailed audit log', () => {
      const triggerDate = new Date(2025, 0, 6);
      const result = calculator.calculate(
        triggerDate,
        21,
        'CALENDAR',
        'CERTIFIED_MAIL'
      );

      expect(result.auditLog.length).toBeGreaterThanOrEqual(3);
      expect(result.auditLog[0].action).toBe('START');
      expect(result.auditLog[result.auditLog.length - 1].action).toBe('FINAL');
    });
  });

  describe('Christmas Eve Deadline (Common Edge Case)', () => {
    it('should handle deadline landing on Christmas', () => {
      const calculator = new SovereignCalculator({
        year: 2025,
        jurisdictionLevel: 'FEDERAL',
      });

      // Dec 4, 2025 + 21 days = Dec 25 (Christmas) -> rolls to Dec 26
      const triggerDate = new Date(2025, 11, 4); // Thursday, Dec 4
      const result = calculator.calculate(triggerDate, 21, 'CALENDAR');

      // Should NOT be Christmas Day
      expect(result.deadlineDate.getDate()).not.toBe(25);
      expect(result.holidaysSkipped).toBeGreaterThanOrEqual(1);
    });
  });
});

describe('Convenience Functions', () => {
  describe('calculateFederalDeadline', () => {
    it('should calculate federal deadline with defaults', () => {
      const result = calculateFederalDeadline(new Date(2025, 0, 6), 21);

      expect(result.deadlineDate).toBeDefined();
      expect(result.countingMethod).toBe('CALENDAR');
    });
  });

  describe('calculateStateDeadline', () => {
    it('should calculate Florida deadline', () => {
      const result = calculateStateDeadline(new Date(2025, 0, 6), 20, 'FL');

      expect(result.deadlineDate).toBeDefined();
    });
  });

  describe('isValidFilingDate', () => {
    it('should return false for weekends', () => {
      const saturday = new Date(2025, 0, 4);
      expect(isValidFilingDate(saturday)).toBe(false);
    });

    it('should return true for business days', () => {
      const monday = new Date(2025, 0, 6);
      expect(isValidFilingDate(monday)).toBe(true);
    });
  });

  describe('applyMailRule', () => {
    it('should add 3 days and return valid business day', () => {
      const baseDeadline = new Date(2025, 0, 6); // Monday
      const result = applyMailRule(baseDeadline);

      // Jan 6 + 3 = Jan 9 (Thursday)
      expect(result.getDate()).toBe(9);
    });
  });
});
