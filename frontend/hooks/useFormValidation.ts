import { useState, useCallback } from 'react';

export interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  custom?: (value: string) => string | null;
}

export interface FieldValidation {
  rules: ValidationRule;
  errorMessage?: string;
}

export interface FormValidationConfig {
  [fieldName: string]: FieldValidation;
}

export interface FieldState {
  value: string;
  error: string | null;
  touched: boolean;
}

export interface FormState {
  [fieldName: string]: FieldState;
}

/**
 * Custom hook for form validation with inline error display
 */
export function useFormValidation(config: FormValidationConfig) {
  const initialState: FormState = {};
  Object.keys(config).forEach((fieldName) => {
    initialState[fieldName] = { value: '', error: null, touched: false };
  });

  const [formState, setFormState] = useState<FormState>(initialState);

  const validateField = useCallback(
    (fieldName: string, value: string): string | null => {
      const fieldConfig = config[fieldName];
      if (!fieldConfig) return null;

      const { rules, errorMessage } = fieldConfig;

      // Required check
      if (rules.required && !value.trim()) {
        return errorMessage || 'This field is required';
      }

      // Min length check
      if (rules.minLength && value.length < rules.minLength) {
        return errorMessage || `Must be at least ${rules.minLength} characters`;
      }

      // Max length check
      if (rules.maxLength && value.length > rules.maxLength) {
        return errorMessage || `Must be no more than ${rules.maxLength} characters`;
      }

      // Pattern check
      if (rules.pattern && !rules.pattern.test(value)) {
        return errorMessage || 'Invalid format';
      }

      // Custom validation
      if (rules.custom) {
        const customError = rules.custom(value);
        if (customError) return customError;
      }

      return null;
    },
    [config]
  );

  const setValue = useCallback(
    (fieldName: string, value: string) => {
      setFormState((prev) => ({
        ...prev,
        [fieldName]: {
          ...prev[fieldName],
          value,
          // Clear error when user starts typing (will re-validate on blur)
          error: prev[fieldName].touched ? validateField(fieldName, value) : null,
        },
      }));
    },
    [validateField]
  );

  const setTouched = useCallback(
    (fieldName: string) => {
      setFormState((prev) => {
        const error = validateField(fieldName, prev[fieldName]?.value || '');
        return {
          ...prev,
          [fieldName]: {
            ...prev[fieldName],
            touched: true,
            error,
          },
        };
      });
    },
    [validateField]
  );

  const validateAll = useCallback((): boolean => {
    let isValid = true;
    const newState: FormState = {};

    Object.keys(config).forEach((fieldName) => {
      const value = formState[fieldName]?.value || '';
      const error = validateField(fieldName, value);
      newState[fieldName] = {
        value,
        error,
        touched: true,
      };
      if (error) isValid = false;
    });

    setFormState(newState);
    return isValid;
  }, [config, formState, validateField]);

  const reset = useCallback(() => {
    setFormState(initialState);
  }, [initialState]);

  const getFieldProps = useCallback(
    (fieldName: string) => ({
      value: formState[fieldName]?.value || '',
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
        setValue(fieldName, e.target.value),
      onBlur: () => setTouched(fieldName),
    }),
    [formState, setValue, setTouched]
  );

  const getFieldError = useCallback(
    (fieldName: string): string | null => {
      const field = formState[fieldName];
      return field?.touched ? field.error : null;
    },
    [formState]
  );

  const isFieldValid = useCallback(
    (fieldName: string): boolean => {
      const field = formState[fieldName];
      return field?.touched && !field.error;
    },
    [formState]
  );

  return {
    formState,
    setValue,
    setTouched,
    validateAll,
    reset,
    getFieldProps,
    getFieldError,
    isFieldValid,
  };
}

/**
 * Email validation pattern
 */
export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Password strength validator
 */
export function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
  suggestions: string[];
} {
  let score = 0;
  const suggestions: string[] = [];

  if (password.length >= 8) score++;
  else suggestions.push('Use at least 8 characters');

  if (password.length >= 12) score++;

  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  else suggestions.push('Mix uppercase and lowercase letters');

  if (/\d/.test(password)) score++;
  else suggestions.push('Include at least one number');

  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
  else suggestions.push('Add a special character');

  const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
  const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500'];

  return {
    score,
    label: labels[Math.min(score, 4)],
    color: colors[Math.min(score, 4)],
    suggestions,
  };
}
