export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 bg-[length:200%_100%] rounded ${className}`}
      style={{
        animation: 'shimmer 2s infinite linear'
      }}
    />
  )
}

export function DeadlineCardSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <Skeleton className="h-5 w-3/4 mb-2" />
          <Skeleton className="h-4 w-1/2" />
        </div>
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <Skeleton className="h-3 w-full mb-1" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  )
}

export function DocumentCardSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg">
      <Skeleton className="h-12 w-12 rounded" />
      <div className="flex-1">
        <Skeleton className="h-4 w-3/4 mb-2" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="h-8 w-8 rounded" />
    </div>
  )
}

export function CalendarSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <Skeleton className="h-6 w-32" />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="h-8 w-8 rounded" />
        </div>
      </div>
      <div className="grid grid-cols-7 gap-2 mb-4">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton key={i} className="h-8 w-full" />
        ))}
      </div>
      <div className="grid grid-cols-7 gap-2">
        {Array.from({ length: 35 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    </div>
  )
}

export function CaseSummarySkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <Skeleton className="h-6 w-48 mb-4" />
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-40" />
        </div>
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-36" />
        </div>
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-28" />
        </div>
      </div>
    </div>
  )
}

// Paper & Steel Skeletons
export function HeatMapSkeleton() {
  return (
    <div className="card border border-slate-200">
      <div className="p-6 border-b border-slate-200 bg-slate-50">
        <Skeleton className="h-6 w-48 mb-2" />
        <Skeleton className="h-4 w-64" />
      </div>
      <div className="p-6">
        <div className="grid grid-cols-5 gap-2">
          {Array.from({ length: 25 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    </div>
  )
}

export function MatterHealthSkeleton() {
  return (
    <div className="card">
      <div className="p-6 border-b border-slate-200">
        <Skeleton className="h-6 w-48 mb-2" />
        <Skeleton className="h-4 w-64" />
      </div>
      <div className="p-6 space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-slate-50 p-5 rounded-lg border border-slate-200">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <Skeleton className="h-5 w-32 mb-2" />
                <Skeleton className="h-4 w-64" />
              </div>
              <Skeleton className="h-8 w-24 rounded" />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function StatsCardSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5">
      <div className="flex items-center gap-3 mb-3">
        <Skeleton className="h-10 w-10 rounded-lg" />
        <Skeleton className="h-4 w-24" />
      </div>
      <Skeleton className="h-8 w-20 mb-2" />
      <Skeleton className="h-3 w-32" />
    </div>
  );
}

export function CaseCardSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <Skeleton className="h-5 w-48 mb-2" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4 rounded" />
          <Skeleton className="h-4 w-24" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4 rounded" />
          <Skeleton className="h-4 w-16" />
        </div>
      </div>
    </div>
  );
}

export function CaseListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <CaseCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function DeadlineRowSkeleton() {
  return (
    <div className="flex items-center gap-4 p-3 border-l-4 border-slate-200 bg-white rounded-r-lg">
      <Skeleton className="h-5 w-5 rounded-full flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <Skeleton className="h-4 w-3/4 mb-2" />
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-16 rounded" />
          <Skeleton className="h-5 w-12 rounded" />
        </div>
      </div>
      <Skeleton className="h-4 w-20 flex-shrink-0" />
    </div>
  );
}

export function DeadlineListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <DeadlineRowSkeleton key={i} />
      ))}
    </div>
  );
}

export function TableRowSkeleton({ columns = 5 }: { columns?: number }) {
  return (
    <tr className="border-b border-slate-100">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}

export function TableSkeleton({ rows = 5, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <table className="w-full">
      <thead>
        <tr className="border-b border-slate-200 bg-slate-50">
          {Array.from({ length: columns }).map((_, i) => (
            <th key={i} className="px-4 py-3 text-left">
              <Skeleton className="h-4 w-24" />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: rows }).map((_, i) => (
          <TableRowSkeleton key={i} columns={columns} />
        ))}
      </tbody>
    </table>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatsCardSkeleton />
        <StatsCardSkeleton />
        <StatsCardSkeleton />
        <StatsCardSkeleton />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <Skeleton className="h-6 w-48 mb-4" />
            <DeadlineListSkeleton count={5} />
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <Skeleton className="h-6 w-32 mb-4" />
          <div className="space-y-3">
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-20 w-full rounded-lg" />
          </div>
        </div>
      </div>
    </div>
  );
}

// Add shimmer animation to global CSS
export const skeletonStyles = `
@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
`;
