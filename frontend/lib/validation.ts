/**
 * Validation utilities for form inputs and data
 */

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

/**
 * Validate chat message input
 */
export function validateChatMessage(message: string): ValidationResult {
  const trimmed = message.trim();

  if (!trimmed) {
    return { isValid: false, error: 'Message cannot be empty' };
  }

  if (trimmed.length > 5000) {
    return { isValid: false, error: 'Message is too long (max 5000 characters)' };
  }

  return { isValid: true };
}

/**
 * Validate deadline bulk edit inputs
 */
export function validateBulkEdit(priority: string, status: string): ValidationResult {
  if (!priority && !status) {
    return { isValid: false, error: 'Please select at least one field to update' };
  }

  const validPriorities = ['informational', 'standard', 'important', 'critical', 'fatal'];
  const validStatuses = ['pending', 'completed', 'cancelled'];

  if (priority && !validPriorities.includes(priority)) {
    return { isValid: false, error: 'Invalid priority value' };
  }

  if (status && !validStatuses.includes(status)) {
    return { isValid: false, error: 'Invalid status value' };
  }

  return { isValid: true };
}

/**
 * Validate snooze days input
 */
export function validateSnoozeDays(days: number): ValidationResult {
  if (!days || days < 1) {
    return { isValid: false, error: 'Please enter at least 1 day' };
  }

  if (days > 365) {
    return { isValid: false, error: 'Cannot snooze more than 365 days' };
  }

  if (!Number.isInteger(days)) {
    return { isValid: false, error: 'Days must be a whole number' };
  }

  return { isValid: true };
}

/**
 * Validate selection count for bulk operations
 */
export function validateBulkSelection(count: number): ValidationResult {
  if (count === 0) {
    return { isValid: false, error: 'Please select at least one deadline' };
  }

  return { isValid: true };
}

/**
 * Format validation error for display
 */
export function formatValidationError(result: ValidationResult): string {
  return result.error || 'Invalid input';
}
