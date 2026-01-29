/**
 * Breadcrumb Configuration
 *
 * Maps URL paths to human-readable breadcrumb labels.
 * Supports dynamic segments like [caseId] with title lookup.
 */

export interface BreadcrumbItem {
  label: string;
  href: string;
  isCurrentPage?: boolean;
}

// Static route labels
const routeLabels: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/cases': 'Cases',
  '/calendar': 'Docket',
  '/settings': 'Settings',
  '/tools': 'Tools',
  '/tools/deadline-calculator': 'Deadline Calculator',
  '/tools/jurisdiction-selector': 'Jurisdiction Navigator',
  '/tools/document-analyzer': 'Document Analyzer',
  '/tools/authority-core': 'Authority Core',
  '/ai-assistant': 'AI Assistant',
  '/rules': 'Rules',
};

// Dynamic segment patterns
type DynamicResolver = (segment: string, fullPath: string) => string | null;

const dynamicResolvers: Record<string, DynamicResolver> = {
  // Case ID resolver - returns case number if available, otherwise the ID
  'cases/[caseId]': (segment) => {
    // This will be resolved by the component using case data
    return null; // Signal that we need dynamic data
  },
};

/**
 * Parse a pathname into breadcrumb items
 * @param pathname Current URL pathname
 * @param dynamicLabels Optional map of dynamic segment values to labels
 */
export function parseBreadcrumbs(
  pathname: string,
  dynamicLabels?: Record<string, string>
): BreadcrumbItem[] {
  if (!pathname || pathname === '/') {
    return [{ label: 'Dashboard', href: '/dashboard', isCurrentPage: true }];
  }

  const segments = pathname.split('/').filter(Boolean);
  const breadcrumbs: BreadcrumbItem[] = [];

  // Always start with Dashboard
  breadcrumbs.push({
    label: 'Dashboard',
    href: '/dashboard',
    isCurrentPage: pathname === '/dashboard',
  });

  let currentPath = '';

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    currentPath += `/${segment}`;

    // Skip dashboard since it's always first
    if (segment === 'dashboard') continue;

    // Check for static label
    const staticLabel = routeLabels[currentPath];
    if (staticLabel) {
      breadcrumbs.push({
        label: staticLabel,
        href: currentPath,
        isCurrentPage: i === segments.length - 1,
      });
      continue;
    }

    // Check for dynamic label from props
    if (dynamicLabels && dynamicLabels[segment]) {
      breadcrumbs.push({
        label: dynamicLabels[segment],
        href: currentPath,
        isCurrentPage: i === segments.length - 1,
      });
      continue;
    }

    // Check for UUID-like segment (case ID, etc.)
    const isUuid = /^[a-f0-9-]{36}$/i.test(segment);
    if (isUuid) {
      // Use the segment as-is or a placeholder
      breadcrumbs.push({
        label: dynamicLabels?.[segment] || 'Case',
        href: currentPath,
        isCurrentPage: i === segments.length - 1,
      });
      continue;
    }

    // Fallback: capitalize the segment
    const fallbackLabel = segment
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');

    breadcrumbs.push({
      label: fallbackLabel,
      href: currentPath,
      isCurrentPage: i === segments.length - 1,
    });
  }

  return breadcrumbs;
}

/**
 * Get the page title from breadcrumbs
 */
export function getPageTitle(breadcrumbs: BreadcrumbItem[]): string {
  if (breadcrumbs.length === 0) return 'LitDocket';

  const current = breadcrumbs.find(b => b.isCurrentPage) || breadcrumbs[breadcrumbs.length - 1];
  return `${current.label} | LitDocket`;
}
