'use client';

import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '@/lib/config';

interface Notification {
  id: string;
  type: string;
  priority: string;
  title: string;
  message: string;
  case_id?: string;
  deadline_id?: string;
  document_id?: string;
  metadata: Record<string, any>;
  action_url?: string;
  action_label?: string;
  is_read: boolean;
  read_at?: string;
  is_dismissed: boolean;
  created_at: string;
}

interface NotificationPreferences {
  in_app_enabled: boolean;
  in_app_deadline_reminders: boolean;
  in_app_document_updates: boolean;
  in_app_case_updates: boolean;
  in_app_ai_insights: boolean;
  email_enabled: boolean;
  email_fatal_deadlines: boolean;
  email_deadline_reminders: boolean;
  email_daily_digest: boolean;
  email_weekly_digest: boolean;
  remind_days_before_fatal: number[];
  remind_days_before_standard: number[];
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

interface UseNotificationsReturn {
  notifications: Notification[];
  unreadCount: number;
  loading: boolean;
  error: string | null;
  preferences: NotificationPreferences | null;
  fetchNotifications: () => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  dismissNotification: (notificationId: string) => Promise<void>;
  fetchPreferences: () => Promise<void>;
  updatePreferences: (updates: Partial<NotificationPreferences>) => Promise<void>;
  triggerDeadlineReminders: () => Promise<{ counts: Record<string, number> }>;
}

export function useNotifications(): UseNotificationsReturn {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);

  const getAuthHeaders = useCallback(() => {
    const token = localStorage.getItem('accessToken');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }, []);

  const apiUrl = API_URL;

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${apiUrl}/api/v1/notifications?limit=50`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch notifications');
      }

      const data = await response.json();
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch notifications');
    } finally {
      setLoading(false);
    }
  }, [apiUrl, getAuthHeaders]);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/notifications/unread-count`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setUnreadCount(data.unread_count || 0);
      }
    } catch (err) {
      console.error('Failed to fetch unread count:', err);
    }
  }, [apiUrl, getAuthHeaders]);

  const markAsRead = useCallback(async (notificationId: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        setNotifications(prev =>
          prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  }, [apiUrl, getAuthHeaders]);

  const markAllAsRead = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/notifications/mark-all-read`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        setUnreadCount(0);
      }
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  }, [apiUrl, getAuthHeaders]);

  const dismissNotification = useCallback(async (notificationId: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/notifications/${notificationId}/dismiss`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        setNotifications(prev => prev.filter(n => n.id !== notificationId));
      }
    } catch (err) {
      console.error('Failed to dismiss notification:', err);
    }
  }, [apiUrl, getAuthHeaders]);

  const fetchPreferences = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/notifications/preferences`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setPreferences(data);
      }
    } catch (err) {
      console.error('Failed to fetch preferences:', err);
    }
  }, [apiUrl, getAuthHeaders]);

  const updatePreferences = useCallback(async (updates: Partial<NotificationPreferences>) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/notifications/preferences`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(updates)
      });

      if (response.ok) {
        const data = await response.json();
        setPreferences(data);
      }
    } catch (err) {
      console.error('Failed to update preferences:', err);
      throw err;
    }
  }, [apiUrl, getAuthHeaders]);

  const triggerDeadlineReminders = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/notifications/process-reminders`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        // Refresh notifications after processing reminders
        await fetchNotifications();
        return data;
      }
      throw new Error('Failed to process reminders');
    } catch (err) {
      console.error('Failed to trigger reminders:', err);
      throw err;
    }
  }, [apiUrl, getAuthHeaders, fetchNotifications]);

  // Initial fetch
  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // Poll for unread count every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  return {
    notifications,
    unreadCount,
    loading,
    error,
    preferences,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    dismissNotification,
    fetchPreferences,
    updatePreferences,
    triggerDeadlineReminders
  };
}
