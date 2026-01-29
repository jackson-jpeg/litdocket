'use client';

/**
 * Breadcrumbs - Navigation path indicator
 *
 * Shows the current location in the app hierarchy.
 * Auto-generates from pathname with support for dynamic segments.
 */

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight, Home } from 'lucide-react';
import { parseBreadcrumbs, BreadcrumbItem } from '@/lib/breadcrumbConfig';

interface BreadcrumbsProps {
  /**
   * Dynamic labels for path segments (e.g., case IDs to case numbers)
   * Key is the path segment, value is the display label
   */
  dynamicLabels?: Record<string, string>;

  /**
   * Optional class name for styling
   */
  className?: string;
}

export function Breadcrumbs({ dynamicLabels, className = '' }: BreadcrumbsProps) {
  const pathname = usePathname();
  const breadcrumbs = parseBreadcrumbs(pathname || '/', dynamicLabels);

  // Don't show breadcrumbs on dashboard (it's the root)
  if (pathname === '/dashboard' || pathname === '/') {
    return null;
  }

  // Don't render if only one breadcrumb (just Dashboard)
  if (breadcrumbs.length <= 1) {
    return null;
  }

  return (
    <nav
      aria-label="Breadcrumb"
      className={`flex items-center gap-1 text-sm ${className}`}
    >
      {breadcrumbs.map((crumb, index) => (
        <React.Fragment key={crumb.href}>
          {index > 0 && (
            <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
          )}
          <BreadcrumbLink crumb={crumb} isFirst={index === 0} />
        </React.Fragment>
      ))}
    </nav>
  );
}

interface BreadcrumbLinkProps {
  crumb: BreadcrumbItem;
  isFirst: boolean;
}

function BreadcrumbLink({ crumb, isFirst }: BreadcrumbLinkProps) {
  if (crumb.isCurrentPage) {
    return (
      <span
        className="font-medium text-slate-900 truncate max-w-[200px]"
        aria-current="page"
        title={crumb.label}
      >
        {crumb.label}
      </span>
    );
  }

  return (
    <Link
      href={crumb.href}
      className="flex items-center gap-1.5 text-slate-600 hover:text-blue-600 transition-colors truncate max-w-[150px]"
      title={crumb.label}
    >
      {isFirst && <Home className="w-3.5 h-3.5 flex-shrink-0" />}
      <span className="truncate">{crumb.label}</span>
    </Link>
  );
}

export default Breadcrumbs;
