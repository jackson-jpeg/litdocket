/**
 * Formatting utilities for dates, text, and other display values
 */

/**
 * CRITICAL FIX: Parse date string as local date, not UTC
 *
 * Problem: new Date("2026-01-12") interprets as UTC midnight (2026-01-12T00:00:00.000Z)
 * In EST (UTC-5), this becomes 2026-01-11 19:00:00 (previous day!)
 *
 * Solution: Manually parse YYYY-MM-DD and create date at local noon
 * to avoid timezone rollback issues.
 *
 * EXPORTED: Use this anywhere you need to parse deadline dates!
 * Example: parseLocalDate(deadline.deadline_date)
 */
export function parseLocalDate(dateString: string | Date): Date {
  if (!dateString) return new Date();

  // If already a Date object, use it
  if (dateString instanceof Date) return dateString;

  // Handle ISO format with time (e.g., "2026-01-12T14:30:00")
  if (typeof dateString === 'string' && dateString.includes('T')) {
    return new Date(dateString);
  }

  // Parse YYYY-MM-DD as local date at noon to avoid timezone issues
  const parts = String(dateString).split('-');
  if (parts.length === 3) {
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1; // Month is 0-indexed
    const day = parseInt(parts[2], 10);

    // Create date at 12:00 PM local time to avoid midnight rollback
    return new Date(year, month, day, 12, 0, 0);
  }

  // Fallback to default parsing (should rarely happen)
  return new Date(dateString);
}

/**
 * Format date for deadline display (MM/DD/YYYY)
 */
export function formatDeadlineDate(dateString: string | null | undefined): string {
  if (!dateString) return 'TBD';

  const date = parseLocalDate(dateString);
  return date.toLocaleDateString('en-US', {
    month: '2-digit',
    day: '2-digit',
    year: 'numeric',
  });
}

/**
 * Format date with time
 * Note: If dateString has time component, it will be preserved
 */
export function formatDateTime(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  const date = parseLocalDate(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Format time only
 */
export function formatTime(dateString: string): string {
  const date = parseLocalDate(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Format date for display (short format)
 * Example: "Jan 12, 2026"
 */
export function formatDateShort(dateString: string): string {
  const date = parseLocalDate(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format full datetime
 */
export function formatFullDateTime(dateString: string): string {
  const date = parseLocalDate(dateString);
  return date.toLocaleString();
}

/**
 * Pluralize a word based on count
 */
export function pluralize(count: number, singular: string, plural?: string): string {
  if (count === 1) return singular;
  return plural || `${singular}s`;
}

/**
 * Format file size in human-readable format
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Truncate text to specified length
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

/**
 * Capitalize first letter
 */
export function capitalize(text: string): string {
  if (!text) return '';
  return text.charAt(0).toUpperCase() + text.slice(1);
}
