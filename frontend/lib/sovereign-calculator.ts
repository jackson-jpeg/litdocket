/**
 * SovereignCalculator - Production-Grade Date Math Engine
 *
 * "The Calculator" - Handles all deadline computations with:
 * - Federal/State holiday awareness
 * - Business day vs calendar day counting
 * - Service method rules (+3 days for mail, etc.)
 * - Retrograde counting (X days BEFORE trigger)
 * - Jurisdiction-specific rules
 *
 * This is the mathematical brain of the Sovereign system.
 */

// ============================================
// TYPE DEFINITIONS
// ============================================

export type CountingMethod = 'CALENDAR' | 'BUSINESS' | 'COURT' | 'RETROGRADE';

export type ServiceMethod =
  | 'PERSONAL'
  | 'CERTIFIED_MAIL'
  | 'FIRST_CLASS_MAIL'
  | 'ELECTRONIC'
  | 'PUBLICATION'
  | 'SECRETARY_OF_STATE'
  | 'POSTING';

export type JurisdictionLevel = 'FEDERAL' | 'STATE' | 'LOCAL';

export interface Holiday {
  date: Date;
  name: string;
  type: 'FEDERAL' | 'STATE' | 'COURT' | 'JUDICIAL';
  jurisdictionId?: string;
}

export interface ServiceMethodRule {
  method: ServiceMethod;
  additionalDays: number;
  citation: string;
  notes?: string;
}

export interface RuleLogic {
  baseDays: number;
  countingMethod: CountingMethod;
  includeWeekends: boolean;
  excludeHolidays: boolean;
  triggerEvent: string;
  serviceMethodApplies: boolean;
}

export interface CalculationResult {
  deadlineDate: Date;
  triggerDate: Date;
  baseDays: number;
  serviceDaysAdded: number;
  holidaysSkipped: number;
  weekendsSkipped: number;
  countingMethod: CountingMethod;
  auditLog: AuditLogEntry[];
  finalAdjustment: string | null;
}

export interface AuditLogEntry {
  step: number;
  action: string;
  date: Date;
  notes: string;
}

export interface HolidayManagerConfig {
  year: number;
  jurisdictionLevel: JurisdictionLevel;
  stateCode?: string;
  customHolidays?: Holiday[];
}

// ============================================
// FEDERAL HOLIDAYS DATABASE
// ============================================

/**
 * Federal holiday rules (recurring patterns)
 * These are computed for any year.
 */
interface FederalHolidayRule {
  name: string;
  // Fixed date holidays
  month?: number; // 0-indexed (0 = January)
  day?: number;
  // Floating holidays (nth weekday of month)
  weekday?: number; // 0 = Sunday, 1 = Monday, etc.
  week?: number; // 1 = first, 2 = second, etc., -1 = last
  // Special cases
  special?: 'MEMORIAL_DAY' | 'THANKSGIVING' | 'ELECTION_DAY';
}

const FEDERAL_HOLIDAY_RULES: FederalHolidayRule[] = [
  // Fixed date holidays
  { name: "New Year's Day", month: 0, day: 1 },
  { name: 'Juneteenth', month: 5, day: 19 },
  { name: 'Independence Day', month: 6, day: 4 },
  { name: "Veterans Day", month: 10, day: 11 },
  { name: 'Christmas Day', month: 11, day: 25 },

  // Floating holidays
  { name: 'Martin Luther King Jr. Day', month: 0, weekday: 1, week: 3 },
  { name: "Presidents' Day", month: 1, weekday: 1, week: 3 },
  { name: 'Columbus Day', month: 9, weekday: 1, week: 2 },
  { name: 'Labor Day', month: 8, weekday: 1, week: 1 },

  // Special calculations
  { name: 'Memorial Day', special: 'MEMORIAL_DAY' },
  { name: 'Thanksgiving Day', special: 'THANKSGIVING' },
];

/**
 * Service method additional days by jurisdiction
 */
const SERVICE_METHOD_RULES: Record<JurisdictionLevel, ServiceMethodRule[]> = {
  FEDERAL: [
    { method: 'PERSONAL', additionalDays: 0, citation: 'Fed. R. Civ. P. 6(d)' },
    { method: 'CERTIFIED_MAIL', additionalDays: 3, citation: 'Fed. R. Civ. P. 6(d)' },
    { method: 'FIRST_CLASS_MAIL', additionalDays: 3, citation: 'Fed. R. Civ. P. 6(d)' },
    { method: 'ELECTRONIC', additionalDays: 3, citation: 'Fed. R. Civ. P. 6(d)' },
    { method: 'SECRETARY_OF_STATE', additionalDays: 10, citation: 'Varies by state' },
  ],
  STATE: [
    // Florida defaults (can be overridden per state)
    { method: 'PERSONAL', additionalDays: 0, citation: 'Fla. R. Civ. P. 1.090(e)' },
    { method: 'CERTIFIED_MAIL', additionalDays: 5, citation: 'Fla. R. Civ. P. 1.090(e)' },
    { method: 'FIRST_CLASS_MAIL', additionalDays: 5, citation: 'Fla. R. Civ. P. 1.090(e)' },
    { method: 'ELECTRONIC', additionalDays: 0, citation: 'Fla. R. Jud. Admin. 2.516' },
  ],
  LOCAL: [
    // Inherit from parent jurisdiction by default
    { method: 'PERSONAL', additionalDays: 0, citation: 'Local rules' },
    { method: 'CERTIFIED_MAIL', additionalDays: 3, citation: 'Local rules' },
    { method: 'FIRST_CLASS_MAIL', additionalDays: 3, citation: 'Local rules' },
    { method: 'ELECTRONIC', additionalDays: 0, citation: 'Local rules' },
  ],
};

// ============================================
// HOLIDAY MANAGER CLASS
// ============================================

export class HolidayManager {
  private holidays: Map<string, Holiday> = new Map();
  private year: number;
  private jurisdictionLevel: JurisdictionLevel;
  private stateCode?: string;

  constructor(config: HolidayManagerConfig) {
    this.year = config.year;
    this.jurisdictionLevel = config.jurisdictionLevel;
    this.stateCode = config.stateCode;

    // Generate federal holidays for the year
    this.generateFederalHolidays();

    // Add custom holidays if provided
    if (config.customHolidays) {
      config.customHolidays.forEach((h) => this.addHoliday(h));
    }
  }

  /**
   * Generate all federal holidays for the configured year
   */
  private generateFederalHolidays(): void {
    FEDERAL_HOLIDAY_RULES.forEach((rule) => {
      let date: Date;

      if (rule.special) {
        date = this.calculateSpecialHoliday(rule.special);
      } else if (rule.month !== undefined && rule.day !== undefined) {
        // Fixed date holiday
        date = new Date(this.year, rule.month, rule.day);
        // Adjust for weekends (observed on Friday or Monday)
        date = this.adjustForWeekendObservance(date);
      } else if (
        rule.month !== undefined &&
        rule.weekday !== undefined &&
        rule.week !== undefined
      ) {
        // Floating holiday (nth weekday of month)
        date = this.getNthWeekdayOfMonth(
          this.year,
          rule.month,
          rule.weekday,
          rule.week
        );
      } else {
        return; // Invalid rule
      }

      this.addHoliday({
        date,
        name: rule.name,
        type: 'FEDERAL',
      });
    });
  }

  /**
   * Calculate special holidays that have unique rules
   */
  private calculateSpecialHoliday(
    special: 'MEMORIAL_DAY' | 'THANKSGIVING' | 'ELECTION_DAY'
  ): Date {
    switch (special) {
      case 'MEMORIAL_DAY':
        // Last Monday of May
        return this.getLastWeekdayOfMonth(this.year, 4, 1);

      case 'THANKSGIVING':
        // Fourth Thursday of November
        return this.getNthWeekdayOfMonth(this.year, 10, 4, 4);

      case 'ELECTION_DAY':
        // Tuesday after first Monday of November
        const firstMonday = this.getNthWeekdayOfMonth(this.year, 10, 1, 1);
        return new Date(
          firstMonday.getFullYear(),
          firstMonday.getMonth(),
          firstMonday.getDate() + 1
        );

      default:
        throw new Error(`Unknown special holiday: ${special}`);
    }
  }

  /**
   * Get the nth weekday of a month
   */
  private getNthWeekdayOfMonth(
    year: number,
    month: number,
    weekday: number,
    n: number
  ): Date {
    const firstDay = new Date(year, month, 1);
    let dayOffset = weekday - firstDay.getDay();
    if (dayOffset < 0) dayOffset += 7;

    const firstOccurrence = 1 + dayOffset;
    const nthOccurrence = firstOccurrence + (n - 1) * 7;

    return new Date(year, month, nthOccurrence);
  }

  /**
   * Get the last weekday of a month
   */
  private getLastWeekdayOfMonth(
    year: number,
    month: number,
    weekday: number
  ): Date {
    const lastDay = new Date(year, month + 1, 0);
    let dayOffset = lastDay.getDay() - weekday;
    if (dayOffset < 0) dayOffset += 7;

    return new Date(year, month, lastDay.getDate() - dayOffset);
  }

  /**
   * Adjust a date if it falls on a weekend (federal observance rules)
   * - Saturday -> Friday
   * - Sunday -> Monday
   */
  private adjustForWeekendObservance(date: Date): Date {
    const dayOfWeek = date.getDay();
    if (dayOfWeek === 0) {
      // Sunday -> observe on Monday
      return new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1);
    } else if (dayOfWeek === 6) {
      // Saturday -> observe on Friday
      return new Date(date.getFullYear(), date.getMonth(), date.getDate() - 1);
    }
    return date;
  }

  /**
   * Add a holiday to the manager
   */
  public addHoliday(holiday: Holiday): void {
    const key = this.dateToKey(holiday.date);
    this.holidays.set(key, holiday);
  }

  /**
   * Check if a date is a holiday
   */
  public isHoliday(date: Date): boolean {
    const key = this.dateToKey(date);
    return this.holidays.has(key);
  }

  /**
   * Get holiday for a date (if any)
   */
  public getHoliday(date: Date): Holiday | undefined {
    const key = this.dateToKey(date);
    return this.holidays.get(key);
  }

  /**
   * Get all holidays for the year
   */
  public getAllHolidays(): Holiday[] {
    return Array.from(this.holidays.values()).sort(
      (a, b) => a.date.getTime() - b.date.getTime()
    );
  }

  /**
   * Convert date to string key for map
   */
  private dateToKey(date: Date): string {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }
}

// ============================================
// SOVEREIGN CALCULATOR CLASS
// ============================================

export class SovereignCalculator {
  private holidayManager: HolidayManager;
  private jurisdictionLevel: JurisdictionLevel;
  private stateCode?: string;

  constructor(config: {
    year?: number;
    jurisdictionLevel?: JurisdictionLevel;
    stateCode?: string;
    customHolidays?: Holiday[];
  } = {}) {
    const year = config.year || new Date().getFullYear();
    this.jurisdictionLevel = config.jurisdictionLevel || 'FEDERAL';
    this.stateCode = config.stateCode;

    this.holidayManager = new HolidayManager({
      year,
      jurisdictionLevel: this.jurisdictionLevel,
      stateCode: this.stateCode,
      customHolidays: config.customHolidays,
    });
  }

  /**
   * Check if a date is a weekend (Saturday or Sunday)
   */
  private isWeekend(date: Date): boolean {
    const day = date.getDay();
    return day === 0 || day === 6;
  }

  /**
   * Check if a date is a court holiday (weekend or official holiday)
   */
  public isCourtClosed(date: Date): boolean {
    return this.isWeekend(date) || this.holidayManager.isHoliday(date);
  }

  /**
   * Get the next business day after a date
   */
  public getNextBusinessDay(date: Date): Date {
    const result = new Date(date);
    while (this.isCourtClosed(result)) {
      result.setDate(result.getDate() + 1);
    }
    return result;
  }

  /**
   * Get the previous business day before a date
   */
  public getPreviousBusinessDay(date: Date): Date {
    const result = new Date(date);
    while (this.isCourtClosed(result)) {
      result.setDate(result.getDate() - 1);
    }
    return result;
  }

  /**
   * Get service method additional days
   */
  public getServiceDays(method: ServiceMethod): ServiceMethodRule {
    const rules = SERVICE_METHOD_RULES[this.jurisdictionLevel];
    const rule = rules.find((r) => r.method === method);
    return rule || { method, additionalDays: 0, citation: 'Unknown' };
  }

  /**
   * The main calculation method
   *
   * @param triggerDate - The date the triggering event occurred
   * @param days - Number of days (positive = after trigger, negative = before trigger)
   * @param method - Counting method (CALENDAR, BUSINESS, COURT, RETROGRADE)
   * @param serviceMethod - Service method for additional days (optional)
   * @returns Full calculation result with audit log
   */
  public calculate(
    triggerDate: Date,
    days: number,
    method: CountingMethod,
    serviceMethod: ServiceMethod = 'PERSONAL'
  ): CalculationResult {
    const auditLog: AuditLogEntry[] = [];
    let step = 1;

    // Normalize trigger date to midnight
    const normalizedTrigger = new Date(triggerDate);
    normalizedTrigger.setHours(0, 0, 0, 0);

    auditLog.push({
      step: step++,
      action: 'START',
      date: normalizedTrigger,
      notes: `Trigger date: ${this.formatDate(normalizedTrigger)}`,
    });

    // Get service days
    const serviceRule = this.getServiceDays(serviceMethod);
    const serviceDays = serviceRule.additionalDays;

    auditLog.push({
      step: step++,
      action: 'SERVICE_DAYS',
      date: normalizedTrigger,
      notes: `Service method: ${serviceMethod}, Additional days: ${serviceDays} (${serviceRule.citation})`,
    });

    // Determine direction
    const direction = days >= 0 ? 1 : -1;
    const absDays = Math.abs(days);

    let currentDate = new Date(normalizedTrigger);
    let daysRemaining = absDays;
    let holidaysSkipped = 0;
    let weekendsSkipped = 0;

    // Calculate based on method
    switch (method) {
      case 'CALENDAR':
        // Simple calendar day calculation
        currentDate.setDate(currentDate.getDate() + days);

        auditLog.push({
          step: step++,
          action: 'CALENDAR_DAYS',
          date: new Date(currentDate),
          notes: `Added ${days} calendar days`,
        });

        // Add service days
        if (serviceDays > 0) {
          currentDate.setDate(currentDate.getDate() + serviceDays);
          auditLog.push({
            step: step++,
            action: 'ADD_SERVICE_DAYS',
            date: new Date(currentDate),
            notes: `Added ${serviceDays} service days`,
          });
        }

        // If lands on weekend/holiday, roll to next business day
        if (this.isCourtClosed(currentDate)) {
          const originalDate = new Date(currentDate);
          currentDate = this.getNextBusinessDay(currentDate);

          if (this.isWeekend(originalDate)) weekendsSkipped++;
          if (this.holidayManager.isHoliday(originalDate)) holidaysSkipped++;

          auditLog.push({
            step: step++,
            action: 'ROLL_FORWARD',
            date: new Date(currentDate),
            notes: `Deadline fell on non-business day, rolled forward to ${this.formatDate(currentDate)}`,
          });
        }
        break;

      case 'BUSINESS':
      case 'COURT':
        // Count only business days
        while (daysRemaining > 0) {
          currentDate.setDate(currentDate.getDate() + direction);

          if (!this.isCourtClosed(currentDate)) {
            daysRemaining--;
          } else {
            if (this.isWeekend(currentDate)) weekendsSkipped++;
            if (this.holidayManager.isHoliday(currentDate)) holidaysSkipped++;
          }
        }

        auditLog.push({
          step: step++,
          action: 'BUSINESS_DAYS',
          date: new Date(currentDate),
          notes: `Counted ${absDays} business days ${direction > 0 ? 'forward' : 'backward'}, skipped ${weekendsSkipped} weekends and ${holidaysSkipped} holidays`,
        });

        // Add service days (as calendar days, then adjust)
        if (serviceDays > 0) {
          currentDate.setDate(currentDate.getDate() + serviceDays);

          if (this.isCourtClosed(currentDate)) {
            currentDate = this.getNextBusinessDay(currentDate);
          }

          auditLog.push({
            step: step++,
            action: 'ADD_SERVICE_DAYS',
            date: new Date(currentDate),
            notes: `Added ${serviceDays} service days and adjusted for business day`,
          });
        }
        break;

      case 'RETROGRADE':
        // Retrograde is always counting BACKWARD from the trigger
        // Used for "X days BEFORE trial"
        daysRemaining = absDays;

        while (daysRemaining > 0) {
          currentDate.setDate(currentDate.getDate() - 1);

          if (!this.isCourtClosed(currentDate)) {
            daysRemaining--;
          } else {
            if (this.isWeekend(currentDate)) weekendsSkipped++;
            if (this.holidayManager.isHoliday(currentDate)) holidaysSkipped++;
          }
        }

        auditLog.push({
          step: step++,
          action: 'RETROGRADE',
          date: new Date(currentDate),
          notes: `Counted ${absDays} business days backward from trigger, skipped ${weekendsSkipped} weekends and ${holidaysSkipped} holidays`,
        });
        break;
    }

    auditLog.push({
      step: step++,
      action: 'FINAL',
      date: new Date(currentDate),
      notes: `Final deadline: ${this.formatDate(currentDate)}`,
    });

    return {
      deadlineDate: currentDate,
      triggerDate: normalizedTrigger,
      baseDays: days,
      serviceDaysAdded: serviceDays,
      holidaysSkipped,
      weekendsSkipped,
      countingMethod: method,
      auditLog,
      finalAdjustment: null,
    };
  }

  /**
   * Calculate deadline for a specific rule logic definition
   */
  public calculateFromRule(
    triggerDate: Date,
    rule: RuleLogic,
    serviceMethod: ServiceMethod = 'PERSONAL'
  ): CalculationResult {
    // Determine counting method
    let method: CountingMethod;
    if (rule.countingMethod === 'RETROGRADE' || rule.baseDays < 0) {
      method = 'RETROGRADE';
    } else if (rule.includeWeekends === false || rule.excludeHolidays) {
      method = 'BUSINESS';
    } else {
      method = 'CALENDAR';
    }

    return this.calculate(
      triggerDate,
      rule.baseDays,
      method,
      rule.serviceMethodApplies ? serviceMethod : 'PERSONAL'
    );
  }

  /**
   * Format date for display
   */
  private formatDate(date: Date): string {
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  /**
   * Get all holidays for the configured year
   */
  public getHolidays(): Holiday[] {
    return this.holidayManager.getAllHolidays();
  }
}

// ============================================
// CONVENIENCE FUNCTIONS
// ============================================

/**
 * Quick calculation for federal deadlines
 */
export function calculateFederalDeadline(
  triggerDate: Date,
  days: number,
  method: CountingMethod = 'CALENDAR',
  serviceMethod: ServiceMethod = 'PERSONAL'
): CalculationResult {
  const calculator = new SovereignCalculator({
    jurisdictionLevel: 'FEDERAL',
  });
  return calculator.calculate(triggerDate, days, method, serviceMethod);
}

/**
 * Quick calculation for state deadlines
 */
export function calculateStateDeadline(
  triggerDate: Date,
  days: number,
  stateCode: string,
  method: CountingMethod = 'CALENDAR',
  serviceMethod: ServiceMethod = 'PERSONAL'
): CalculationResult {
  const calculator = new SovereignCalculator({
    jurisdictionLevel: 'STATE',
    stateCode,
  });
  return calculator.calculate(triggerDate, days, method, serviceMethod);
}

/**
 * Validate a deadline date against court closures
 */
export function isValidFilingDate(
  date: Date,
  jurisdictionLevel: JurisdictionLevel = 'FEDERAL'
): boolean {
  const calculator = new SovereignCalculator({ jurisdictionLevel });
  return !calculator.isCourtClosed(date);
}

/**
 * Get the deadline date considering the "mail rule" (+3 days)
 */
export function applyMailRule(
  baseDeadline: Date,
  jurisdictionLevel: JurisdictionLevel = 'FEDERAL'
): Date {
  const calculator = new SovereignCalculator({ jurisdictionLevel });
  const result = calculator.calculate(
    baseDeadline,
    0,
    'CALENDAR',
    'FIRST_CLASS_MAIL'
  );
  return result.deadlineDate;
}

// Export default calculator instance
export const defaultCalculator = new SovereignCalculator();

export default SovereignCalculator;
