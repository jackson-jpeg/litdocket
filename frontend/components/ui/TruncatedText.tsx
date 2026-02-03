'use client';

import { useState, useRef, useEffect } from 'react';

interface TruncatedTextProps {
  text: string;
  maxLength?: number;
  className?: string;
  tooltipClassName?: string;
  truncateAt?: 'word' | 'character';
}

/**
 * TruncatedText - Smart text truncation with tooltip
 *
 * Features:
 * - Word-boundary truncation (avoids cutting words)
 * - Full text visible on hover via tooltip
 * - Auto-detects if truncation is needed
 */
export function TruncatedText({
  text,
  maxLength = 50,
  className = '',
  tooltipClassName = '',
  truncateAt = 'word',
}: TruncatedTextProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLSpanElement>(null);

  const needsTruncation = text.length > maxLength;

  const truncatedText = (() => {
    if (!needsTruncation) return text;

    if (truncateAt === 'character') {
      return text.slice(0, maxLength - 3) + '...';
    }

    // Word-boundary truncation
    let truncated = text.slice(0, maxLength);

    // Find last space to avoid cutting words
    const lastSpace = truncated.lastIndexOf(' ');
    if (lastSpace > maxLength * 0.6) {
      truncated = truncated.slice(0, lastSpace);
    }

    return truncated + '...';
  })();

  const handleMouseEnter = (e: React.MouseEvent) => {
    if (!needsTruncation) return;

    const rect = (e.target as HTMLElement).getBoundingClientRect();
    setTooltipPosition({
      x: rect.left + rect.width / 2,
      y: rect.top - 8,
    });
    setShowTooltip(true);
  };

  const handleMouseLeave = () => {
    setShowTooltip(false);
  };

  return (
    <>
      <span
        ref={containerRef}
        className={`${className} ${needsTruncation ? 'cursor-help' : ''}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        title={needsTruncation ? text : undefined}
      >
        {truncatedText}
      </span>

      {/* Tooltip */}
      {showTooltip && needsTruncation && (
        <div
          className={`fixed z-50 px-3 py-2 text-sm bg-slate-900 text-white rounded-lg shadow-lg max-w-xs transform -translate-x-1/2 -translate-y-full pointer-events-none ${tooltipClassName}`}
          style={{
            left: tooltipPosition.x,
            top: tooltipPosition.y,
          }}
        >
          {text}
          {/* Arrow */}
          <div className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
        </div>
      )}
    </>
  );
}

/**
 * TruncatedCell - Table cell variant with CSS truncation
 *
 * Uses CSS text-overflow for more reliable table layouts
 */
export function TruncatedCell({
  text,
  className = '',
  maxWidth = '200px',
}: {
  text: string;
  className?: string;
  maxWidth?: string;
}) {
  return (
    <span
      className={`block truncate ${className}`}
      style={{ maxWidth }}
      title={text}
    >
      {text}
    </span>
  );
}

export default TruncatedText;
