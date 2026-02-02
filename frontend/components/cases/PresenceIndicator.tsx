'use client';

import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api-client';
import { Users } from 'lucide-react';
import type { CasePresenceResponse, CasePresenceUser } from '@/types';

interface PresenceIndicatorProps {
  caseId: string;
  className?: string;
}

export default function PresenceIndicator({ caseId, className = '' }: PresenceIndicatorProps) {
  const [users, setUsers] = useState<CasePresenceUser[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPresence = useCallback(async () => {
    try {
      const response = await apiClient.get<CasePresenceResponse>(
        `/api/v1/case-access/cases/${caseId}/presence`
      );
      setUsers(response.data.active_users.filter((u) => !u.is_current_user));
    } catch (err) {
      // Silently fail - presence is not critical
      console.debug('Presence fetch failed:', err);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  const sendHeartbeat = useCallback(async () => {
    try {
      await apiClient.post(`/api/v1/case-access/cases/${caseId}/presence/heartbeat`);
    } catch (err) {
      console.debug('Heartbeat failed:', err);
    }
  }, [caseId]);

  useEffect(() => {
    // Initial fetch
    fetchPresence();
    sendHeartbeat();

    // Poll every 30 seconds
    const pollInterval = setInterval(() => {
      fetchPresence();
    }, 30000);

    // Heartbeat every 60 seconds
    const heartbeatInterval = setInterval(() => {
      sendHeartbeat();
    }, 60000);

    // Cleanup on unmount
    return () => {
      clearInterval(pollInterval);
      clearInterval(heartbeatInterval);
      // Try to remove presence
      apiClient.delete(`/api/v1/case-access/cases/${caseId}/presence`).catch(() => {});
    };
  }, [caseId, fetchPresence, sendHeartbeat]);

  // Don't show if no other users
  if (loading || users.length === 0) {
    return null;
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="flex -space-x-2">
        {users.slice(0, 3).map((user) => (
          <div
            key={user.user_id}
            className="w-8 h-8 rounded-full bg-blue-500 border-2 border-white flex items-center justify-center text-white text-xs font-medium"
            title={user.name || user.email || 'User'}
          >
            {(user.name || user.email || 'U').charAt(0).toUpperCase()}
          </div>
        ))}
        {users.length > 3 && (
          <div className="w-8 h-8 rounded-full bg-slate-400 border-2 border-white flex items-center justify-center text-white text-xs font-medium">
            +{users.length - 3}
          </div>
        )}
      </div>
      <span className="text-sm text-slate-500">
        {users.length === 1 ? '1 other viewing' : `${users.length} others viewing`}
      </span>
    </div>
  );
}
