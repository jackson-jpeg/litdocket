/**
 * Dashboard Hooks - Progressive loading for dashboard data
 *
 * Each hook independently fetches and revalidates data without blocking
 * other sections or causing UI flicker on background refresh.
 */

export { useDashboardAlerts } from './useDashboardAlerts';
export type { DashboardAlerts } from './useDashboardAlerts';

export { useDashboardStats } from './useDashboardStats';
export type { DashboardStats } from './useDashboardStats';

export { useDashboardUpcoming } from './useDashboardUpcoming';
export type { DashboardUpcoming, UpcomingDeadline } from './useDashboardUpcoming';

export { useHeatMap } from './useHeatMap';
export type { HeatMapData } from './useHeatMap';

export { useActivityFeed } from './useActivityFeed';
export type { ActivityFeedData, ActivityItem } from './useActivityFeed';

export { useMatterHealth } from './useMatterHealth';
export type { MatterHealthData, MatterHealthCard, CriticalCase, ZombieCase } from './useMatterHealth';
