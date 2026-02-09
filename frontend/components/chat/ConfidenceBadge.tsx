/**
 * ConfidenceBadge - Visual confidence score display for Authority Core rules
 *
 * Phase 4: Chat Integration Component
 *
 * Displays confidence scores with color-coded visual indicators:
 * - High (≥90%): Green background - High confidence, attorney-verified
 * - Medium-High (≥80%): Yellow background - Recommended approval
 * - Medium (≥60%): Orange background - Review required
 * - Low (<60%): Red background - Careful review needed
 *
 * Follows Paper & Steel design system: zero border-radius, border-based styling
 */

import React from 'react';

interface ConfidenceBadgeProps {
  score: number; // 0.0 - 1.0 (will be displayed as percentage)
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function ConfidenceBadge({
  score,
  size = 'md',
  showLabel = true,
  className = ''
}: ConfidenceBadgeProps) {
  // Convert to percentage
  const percentage = Math.round(score * 100);

  // Determine confidence level and styling
  const getConfidenceStyle = () => {
    if (score >= 0.90) {
      return {
        bg: 'bg-green-100',
        border: 'border-green-600',
        text: 'text-green-900',
        label: 'High Confidence',
        icon: '✓'
      };
    } else if (score >= 0.80) {
      return {
        bg: 'bg-yellow-100',
        border: 'border-yellow-600',
        text: 'text-yellow-900',
        label: 'Recommended',
        icon: '⊕'
      };
    } else if (score >= 0.60) {
      return {
        bg: 'bg-orange-100',
        border: 'border-orange-600',
        text: 'text-orange-900',
        label: 'Review Required',
        icon: '⚠'
      };
    } else {
      return {
        bg: 'bg-red-100',
        border: 'border-red-600',
        text: 'text-red-900',
        label: 'Careful Review',
        icon: '✕'
      };
    }
  };

  // Get size classes
  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'px-2 py-0.5 text-xs';
      case 'lg':
        return 'px-4 py-2 text-base';
      case 'md':
      default:
        return 'px-3 py-1 text-sm';
    }
  };

  const style = getConfidenceStyle();
  const sizeClasses = getSizeClasses();

  return (
    <span
      className={`
        inline-flex items-center gap-1
        ${style.bg} ${style.border} ${style.text}
        border-2 font-medium
        ${sizeClasses}
        ${className}
      `}
      title={`${style.label}: ${percentage}% confidence`}
    >
      <span className="leading-none">{style.icon}</span>
      {showLabel && (
        <>
          <span className="font-semibold">{percentage}%</span>
          {size !== 'sm' && (
            <span className="hidden sm:inline">– {style.label}</span>
          )}
        </>
      )}
      {!showLabel && (
        <span className="font-semibold">{percentage}%</span>
      )}
    </span>
  );
}

// Compact version for inline use
export function ConfidenceScore({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  const color = score >= 0.90 ? 'text-green-600' :
                score >= 0.80 ? 'text-yellow-600' :
                score >= 0.60 ? 'text-orange-600' : 'text-red-600';

  return (
    <span className={`font-mono font-semibold ${color}`}>
      {percentage}%
    </span>
  );
}
