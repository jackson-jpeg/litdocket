'use client';

import { forwardRef } from 'react';
import { AlertCircle, Check } from 'lucide-react';

interface FormFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string | null;
  hint?: string;
  showValidIcon?: boolean;
  isValid?: boolean;
}

/**
 * FormField - Input with integrated validation display
 */
export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  ({ label, error, hint, showValidIcon = false, isValid = false, className = '', ...props }, ref) => {
    const hasError = !!error;
    const showValid = showValidIcon && isValid && !hasError;

    return (
      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-slate-700">
          {label}
          {props.required && <span className="text-red-500 ml-1">*</span>}
        </label>

        <div className="relative">
          <input
            ref={ref}
            className={`
              w-full px-4 py-2.5 text-sm rounded-lg border transition-all
              ${hasError
                ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-100 bg-red-50'
                : showValid
                  ? 'border-green-300 focus:border-green-500 focus:ring-2 focus:ring-green-100'
                  : 'border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100'
              }
              placeholder-slate-400
              disabled:bg-slate-100 disabled:cursor-not-allowed
              ${className}
            `}
            aria-invalid={hasError}
            aria-describedby={hasError ? `${props.id}-error` : hint ? `${props.id}-hint` : undefined}
            {...props}
          />

          {/* Status icon */}
          {(hasError || showValid) && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {hasError ? (
                <AlertCircle className="w-5 h-5 text-red-500" />
              ) : (
                <Check className="w-5 h-5 text-green-500" />
              )}
            </div>
          )}
        </div>

        {/* Error message */}
        {hasError && (
          <p id={`${props.id}-error`} className="text-sm text-red-600 flex items-center gap-1">
            <AlertCircle className="w-3.5 h-3.5" />
            {error}
          </p>
        )}

        {/* Hint text */}
        {hint && !hasError && (
          <p id={`${props.id}-hint`} className="text-sm text-slate-500">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

FormField.displayName = 'FormField';

interface PasswordStrengthProps {
  score: number;
  label: string;
  color: string;
  suggestions?: string[];
}

/**
 * PasswordStrength - Visual password strength indicator
 */
export function PasswordStrength({ score, label, color, suggestions = [] }: PasswordStrengthProps) {
  return (
    <div className="space-y-2">
      {/* Strength bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 flex gap-1">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                i < score ? color : 'bg-slate-200'
              }`}
            />
          ))}
        </div>
        <span className={`text-xs font-medium ${
          score >= 4 ? 'text-green-600' :
          score >= 3 ? 'text-blue-600' :
          score >= 2 ? 'text-yellow-600' :
          'text-red-600'
        }`}>
          {label}
        </span>
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && score < 4 && (
        <ul className="text-xs text-slate-500 space-y-0.5">
          {suggestions.slice(0, 2).map((suggestion, i) => (
            <li key={i} className="flex items-center gap-1">
              <span className="w-1 h-1 rounded-full bg-slate-400" />
              {suggestion}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default FormField;
