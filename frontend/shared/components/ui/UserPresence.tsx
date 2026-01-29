'use client';

import { Users, Wifi, WifiOff } from 'lucide-react';
import { UserPresence as UserPresenceType } from '@/features/cases/hooks/useRealTimeCase';

interface UserPresenceProps {
  isConnected: boolean;
  activeUsers: UserPresenceType[];
  className?: string;
}

export default function UserPresence({
  isConnected,
  activeUsers,
  className = '',
}: UserPresenceProps) {
  // Filter out current user (optional, depending on your preference)
  const otherUsers = activeUsers;

  // Only show if connected or has active users
  if (!isConnected && otherUsers.length === 0) {
    return null; // Don't show anything when offline and alone
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Connection status indicator - only show when connected */}
      {isConnected && (
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs font-medium text-green-700">Live</span>
        </div>
      )}

      {/* Active users indicator */}
      {otherUsers.length > 0 && (
        <div className={`flex items-center gap-1.5 ${isConnected ? 'pl-2 border-l border-gray-300' : ''}`}>
          <Users className="w-4 h-4 text-blue-600" />
          <span className="text-xs font-medium text-blue-700">
            {otherUsers.length === 1
              ? `${otherUsers[0].user_name || 'User'} is viewing`
              : `${otherUsers.length} users viewing`}
          </span>
        </div>
      )}
    </div>
  );
}
