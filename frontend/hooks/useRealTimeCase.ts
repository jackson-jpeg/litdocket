/**
 * Hook for real-time case collaboration via WebSocket
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketClient, createCaseWebSocket, WebSocketMessage } from '@/lib/websocket';
import { emitEvent } from '@/lib/eventBus';

export interface UserPresence {
  user_id: string;
  user_name?: string;
  last_seen?: string;
}

export interface RealTimeState {
  isConnected: boolean;
  activeUsers: UserPresence[];
  isTyping: Map<string, boolean>;
}

export function useRealTimeCase(caseId: string | null) {
  const wsClient = useRef<WebSocketClient | null>(null);
  const [state, setState] = useState<RealTimeState>({
    isConnected: false,
    activeUsers: [],
    isTyping: new Map(),
  });

  /**
   * Initialize WebSocket connection
   */
  useEffect(() => {
    if (!caseId) return;

    // Get token from localStorage, use demo token if not found
    const token = localStorage.getItem('accessToken') || 'demo-token-for-websocket-connection';

    // Check if WebSocket URL is configured
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
    if (!wsUrl) {
      console.warn('WebSocket URL not configured, running in offline mode');
      setState((prev) => ({ ...prev, isConnected: false }));
      return;
    }

    console.log(`Initializing WebSocket for case ${caseId}`);

    // Create WebSocket client
    const client = createCaseWebSocket(caseId, token);

    // Configure event handlers
    client.config.onConnect = () => {
      console.log('✓ WebSocket connected - real-time updates enabled');
      setState((prev) => ({ ...prev, isConnected: true }));

      // Request current presence
      setTimeout(() => {
        if (client.isConnected) {
          client.requestPresence();
        }
      }, 100);
    };

    client.config.onDisconnect = () => {
      console.log('✗ WebSocket disconnected - running in offline mode');
      setState((prev) => ({
        ...prev,
        isConnected: false,
        activeUsers: [],
        isTyping: new Map(),
      }));
    };

    client.config.onError = (error) => {
      console.error('WebSocket error:', error);
    };

    // Subscribe to events
    const unsubscribers = [
      // User joined
      client.on('user_joined', (data: any) => {
        console.log('User joined:', data.user_name);
        setState((prev) => {
          const newUsers = [
            ...prev.activeUsers.filter((u) => u.user_id !== data.user_id),
            {
              user_id: data.user_id,
              user_name: data.user_name,
              last_seen: data.timestamp,
            },
          ];
          return { ...prev, activeUsers: newUsers };
        });
      }),

      // User left
      client.on('user_left', (data: any) => {
        console.log('User left:', data.user_name);
        setState((prev) => ({
          ...prev,
          activeUsers: prev.activeUsers.filter((u) => u.user_id !== data.user_id),
        }));
      }),

      // Presence update
      client.on('presence_update', (data: any) => {
        console.log('Presence update:', data.users);
        setState((prev) => ({
          ...prev,
          activeUsers: data.users || [],
        }));
      }),

      // Deadline updated
      client.on('deadline_updated', (data: any) => {
        console.log('Deadline updated:', data.action, data.deadline_id);

        // Emit event to refresh deadline data
        emitEvent('deadline:updated', {
          caseId: data.case_id,
          deadlineId: data.deadline_id,
          action: data.action,
          deadline: data.deadline,
        });

        // Show toast notification if update from another user
        const currentUserId = localStorage.getItem('user_id');
        if (data.user_id !== currentUserId) {
          emitEvent('toast:show', {
            message: `${data.user_name} ${data.action} a deadline`,
            type: 'info',
          });
        }
      }),

      // Document updated
      client.on('document_updated', (data: any) => {
        console.log('Document updated:', data.action, data.document_id);

        // Emit event to refresh document data
        emitEvent('document:updated', {
          caseId: data.case_id,
          documentId: data.document_id,
          action: data.action,
          document: data.document,
        });

        // Show toast notification
        const currentUserId = localStorage.getItem('user_id');
        if (data.user_id !== currentUserId) {
          emitEvent('toast:show', {
            message: `${data.user_name} ${data.action} a document`,
            type: 'info',
          });
        }
      }),

      // User typing
      client.on('user_typing', (data: any) => {
        setState((prev) => {
          const newTyping = new Map(prev.isTyping);
          newTyping.set(data.user_id, data.is_typing);
          return { ...prev, isTyping: newTyping };
        });

        // Auto-clear typing indicator after 5 seconds
        if (data.is_typing) {
          setTimeout(() => {
            setState((prev) => {
              const newTyping = new Map(prev.isTyping);
              newTyping.delete(data.user_id);
              return { ...prev, isTyping: newTyping };
            });
          }, 5000);
        }
      }),

      // Error
      client.on('error', (data: any) => {
        console.error('WebSocket error event:', data);
        emitEvent('toast:show', {
          message: data.error || 'WebSocket error occurred',
          type: 'error',
        });
      }),
    ];

    // Connect
    client.connect();

    // Store client ref
    wsClient.current = client;

    // Cleanup
    return () => {
      console.log('Cleaning up WebSocket connection');
      unsubscribers.forEach((unsub) => unsub());

      // Delay disconnect to avoid React strict mode double-mount issues
      setTimeout(() => {
        if (wsClient.current === client) {
          client.disconnect();
          wsClient.current = null;
        }
      }, 100);
    };
  }, [caseId]);

  /**
   * Send typing indicator
   */
  const sendTyping = useCallback((isTyping: boolean) => {
    wsClient.current?.sendTyping(isTyping);
  }, []);

  /**
   * Get list of users currently typing
   */
  const getTypingUsers = useCallback((): string[] => {
    const typingUserIds: string[] = [];
    state.isTyping.forEach((isTyping, userId) => {
      if (isTyping) {
        const user = state.activeUsers.find((u) => u.user_id === userId);
        if (user?.user_name) {
          typingUserIds.push(user.user_name);
        }
      }
    });
    return typingUserIds;
  }, [state.isTyping, state.activeUsers]);

  return {
    isConnected: state.isConnected,
    activeUsers: state.activeUsers,
    sendTyping,
    getTypingUsers,
  };
}
