/**
 * useStreamingChat - Custom hook for SSE-based AI chat streaming
 *
 * Manages EventSource connection, state machine, and approval flow.
 * Provides clean API for sending messages and handling approvals.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import apiClient from '@/lib/api-client';
import { API_URL } from '@/lib/config';

// Stream states
export type StreamState =
  | { type: 'idle' }
  | { type: 'connecting', sessionId: string }
  | { type: 'streaming', sessionId: string, eventSource: EventSource }
  | { type: 'awaiting_approval', toolCall: ToolCallProposal, approvalId: string }
  | { type: 'executing_tool', toolName: string }
  | { type: 'error', error: string, code?: string };

// Types
export interface ToolCallProposal {
  tool_id: string;
  tool_name: string;
  input: Record<string, any>;
  requires_approval: boolean;
  rationale?: string;
}

export interface StreamingMessage {
  id: string;
  content: string;
  isComplete: boolean;
}

interface UseStreamingChatOptions {
  caseId: string;
  onToken?: (token: string) => void;
  onStatus?: (status: string, message: string) => void;
  onToolUse?: (toolCall: ToolCallProposal) => void;
  onToolResult?: (toolId: string, result: any) => void;
  onError?: (error: string, code?: string) => void;
  onDone?: (data: { message_id: string; tokens_used: number }) => void;
}

export function useStreamingChat(options: UseStreamingChatOptions) {
  const {
    caseId,
    onToken,
    onStatus,
    onToolUse,
    onToolResult,
    onError,
    onDone
  } = options;

  const [streamState, setStreamState] = useState<StreamState>({ type: 'idle' });
  const [currentMessage, setCurrentMessage] = useState('');
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const maxReconnectAttempts = 3;
  const receivedDataRef = useRef(false);  // Track if we received any data
  const streamCompletedRef = useRef(false);  // Track if stream completed successfully

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  /**
   * Send a message and start streaming response
   */
  const sendMessage = useCallback(async (message: string) => {
    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Generate unique session ID
    const sessionId = uuidv4();

    // Reset message buffer and flags
    setCurrentMessage('');
    receivedDataRef.current = false;
    streamCompletedRef.current = false;

    // Set connecting state
    setStreamState({ type: 'connecting', sessionId });

    try {
      // Get auth token from localStorage
      // EventSource doesn't support custom headers, so we pass token as query param
      if (typeof window === 'undefined') {
        throw new Error('Cannot connect to SSE from server-side');
      }

      const token = localStorage.getItem('accessToken');
      if (!token) {
        throw new Error('No authentication token found. Please log in.');
      }

      // Build SSE URL with full backend URL
      const url = `${API_URL}/api/v1/chat/stream?case_id=${encodeURIComponent(caseId)}&session_id=${sessionId}&message=${encodeURIComponent(message)}&token=${encodeURIComponent(token)}`;

      // Create EventSource
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      setStreamState({ type: 'streaming', sessionId, eventSource });

      // Handle status events
      eventSource.addEventListener('status', (e) => {
        receivedDataRef.current = true;  // Mark that we received data
        const data = JSON.parse(e.data);
        console.log('[SSE] Status:', data);
        if (onStatus) {
          onStatus(data.status, data.message);
        }
      });

      // Handle token events (streaming text)
      eventSource.addEventListener('token', (e) => {
        receivedDataRef.current = true;  // Mark that we received data
        const data = JSON.parse(e.data);
        setCurrentMessage(prev => prev + data.text);

        if (onToken) {
          onToken(data.text);
        }
      });

      // Handle tool use events
      eventSource.addEventListener('tool_use', (e) => {
        const toolCall: ToolCallProposal = JSON.parse(e.data);

        if (toolCall.requires_approval) {
          // Requires user approval
          setStreamState({
            type: 'awaiting_approval',
            toolCall,
            approvalId: toolCall.tool_id
          });
        } else {
          // Auto-executing safe tool
          setStreamState({
            type: 'executing_tool',
            toolName: toolCall.tool_name
          });
        }

        if (onToolUse) {
          onToolUse(toolCall);
        }
      });

      // Handle tool approved events
      eventSource.addEventListener('tool_approved', (e) => {
        const data = JSON.parse(e.data);
        // Tool was approved, will now execute
        setStreamState({ type: 'streaming', sessionId, eventSource });
      });

      // Handle tool rejected events
      eventSource.addEventListener('tool_rejected', (e) => {
        const data = JSON.parse(e.data);
        console.log('Tool rejected:', data.tool_id, data.reason);
        // Continue streaming (AI will get rejection result)
        setStreamState({ type: 'streaming', sessionId, eventSource });
      });

      // Handle tool result events
      eventSource.addEventListener('tool_result', (e) => {
        const data = JSON.parse(e.data);

        if (onToolResult) {
          onToolResult(data.tool_id, data.result);
        }

        // Continue streaming
        setStreamState({ type: 'streaming', sessionId, eventSource });
      });

      // Handle error events from server (custom events with data)
      eventSource.addEventListener('error', (e: any) => {
        // Only process if this is a real error event with data from the server
        // Native EventSource errors don't have .data
        if (!e.data) {
          console.log('[SSE] Ignoring native error event (will be handled by onerror)');
          return;
        }

        receivedDataRef.current = true;  // Mark that we received data
        let errorData = { error: 'Unknown error', code: 'UNKNOWN' };

        try {
          errorData = JSON.parse(e.data);
        } catch (err) {
          console.error('[SSE] Failed to parse error event data:', err);
        }

        console.error('[SSE] Server error:', errorData);

        if (onError) {
          onError(errorData.error, errorData.code);
        }

        setStreamState({
          type: 'error',
          error: errorData.error,
          code: errorData.code
        });

        // Close connection
        eventSource.close();
        eventSourceRef.current = null;
      });

      // Handle done events
      eventSource.addEventListener('done', (e) => {
        const data = JSON.parse(e.data);

        // CRITICAL: Set completion flag FIRST to prevent onerror race
        streamCompletedRef.current = true;

        if (onDone) {
          onDone(data);
        }

        // Return to idle
        setStreamState({ type: 'idle' });
        setReconnectAttempts(0);

        // Close connection (will trigger onerror but streamCompletedRef prevents error)
        eventSource.close();
        eventSourceRef.current = null;
      });

      // Handle connection open
      eventSource.onopen = () => {
        console.log('[SSE] Connection opened successfully');
        receivedDataRef.current = true;  // Connection is working
      };

      // Handle connection errors (EventSource standard error event)
      eventSource.onerror = (e) => {
        // CRITICAL: Check completion flag FIRST - this is synchronous and reliable
        if (streamCompletedRef.current) {
          console.log('[SSE] Ignoring onerror - stream completed successfully');
          return;
        }

        console.log('[SSE] onerror fired. ReadyState:', eventSource.readyState);

        // If we received any data, this is likely normal connection close
        if (receivedDataRef.current) {
          console.log('[SSE] Connection closed after receiving data - ignoring');
          eventSource.close();
          eventSourceRef.current = null;
          setStreamState({ type: 'idle' });
          setReconnectAttempts(0);
          return;
        }

        // If we NEVER received data, this is a real connection failure
        console.error('[SSE] Real connection failure - no data received');

        // Only retry if we haven't exceeded max attempts
        if (reconnectAttempts < maxReconnectAttempts) {
          const delay = 2000 * (reconnectAttempts + 1);
          console.log(`[SSE] Retrying in ${delay}ms... (${reconnectAttempts + 1}/${maxReconnectAttempts})`);
          eventSource.close();
          eventSourceRef.current = null;

          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            sendMessage(message);
          }, delay);
          return;
        }

        // Max retries exceeded
        console.error('[SSE] Max retries exceeded');
        setStreamState({
          type: 'error',
          error: 'Failed to connect to AI service. Please try again.',
          code: 'MAX_RETRIES'
        });

        if (onError) {
          onError('Failed to connect to AI service. Please try again.', 'MAX_RETRIES');
        }

        eventSource.close();
        eventSourceRef.current = null;
      };

    } catch (error) {
      console.error('Failed to start stream:', error);

      setStreamState({
        type: 'error',
        error: 'Failed to connect to AI service',
        code: 'CONNECT_FAILED'
      });

      if (onError) {
        onError('Failed to connect to AI service', 'CONNECT_FAILED');
      }
    }
  }, [caseId, reconnectAttempts, onToken, onStatus, onToolUse, onToolResult, onError, onDone]);

  /**
   * Approve a tool execution
   */
  const approveToolUse = useCallback(async (
    approvalId: string,
    modifications?: Record<string, any>
  ) => {
    try {
      await apiClient.post(`/api/v1/chat/approve/${approvalId}`, {
        approved: true,
        modifications
      });

      // Resume streaming
      if (eventSourceRef.current) {
        setStreamState({
          type: 'streaming',
          sessionId: (streamState as any).sessionId || 'unknown',
          eventSource: eventSourceRef.current
        });
      }
    } catch (error) {
      console.error('Failed to approve tool:', error);

      if (onError) {
        onError('Failed to submit approval', 'APPROVAL_FAILED');
      }
    }
  }, [streamState, onError]);

  /**
   * Reject a tool execution
   */
  const rejectToolUse = useCallback(async (
    approvalId: string,
    reason?: string
  ) => {
    try {
      await apiClient.post(`/api/v1/chat/reject/${approvalId}`, {
        reason: reason || 'User rejected'
      });

      // Resume streaming
      if (eventSourceRef.current) {
        setStreamState({
          type: 'streaming',
          sessionId: (streamState as any).sessionId || 'unknown',
          eventSource: eventSourceRef.current
        });
      }
    } catch (error) {
      console.error('Failed to reject tool:', error);

      if (onError) {
        onError('Failed to submit rejection', 'REJECTION_FAILED');
      }
    }
  }, [streamState, onError]);

  /**
   * Cancel current stream
   */
  const cancelStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setStreamState({ type: 'idle' });
    setCurrentMessage('');
  }, []);

  return {
    streamState,
    currentMessage,
    sendMessage,
    approveToolUse,
    rejectToolUse,
    cancelStream,
    isStreaming: streamState.type === 'streaming' || streamState.type === 'connecting',
    isAwaitingApproval: streamState.type === 'awaiting_approval',
    hasError: streamState.type === 'error'
  };
}
