/**
 * useStreamingChat - Custom hook for SSE-based AI chat streaming
 *
 * Manages EventSource connection, state machine, and approval flow.
 * Provides clean API for sending messages and handling approvals.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import apiClient from '@/lib/api-client';

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

    // Reset message buffer
    setCurrentMessage('');

    // Set connecting state
    setStreamState({ type: 'connecting', sessionId });

    try {
      // Build SSE URL
      const url = `/api/v1/chat/stream?case_id=${encodeURIComponent(caseId)}&session_id=${sessionId}&message=${encodeURIComponent(message)}`;

      // Create EventSource
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      setStreamState({ type: 'streaming', sessionId, eventSource });

      // Handle status events
      eventSource.addEventListener('status', (e) => {
        const data = JSON.parse(e.data);
        if (onStatus) {
          onStatus(data.status, data.message);
        }
      });

      // Handle token events (streaming text)
      eventSource.addEventListener('token', (e) => {
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

      // Handle error events
      eventSource.addEventListener('error', (e: any) => {
        let errorData = { error: 'Connection error', code: 'CONNECTION_ERROR' };

        try {
          errorData = JSON.parse(e.data);
        } catch {
          // Default error if parsing fails
        }

        console.error('SSE error:', errorData);

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

        if (onDone) {
          onDone(data);
        }

        // Close connection
        eventSource.close();
        eventSourceRef.current = null;

        // Return to idle
        setStreamState({ type: 'idle' });
        setReconnectAttempts(0);
      });

      // Handle connection errors (EventSource standard error event)
      eventSource.onerror = (e) => {
        console.error('EventSource connection error:', e);

        // Attempt reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
          const delay = 2000 * (reconnectAttempts + 1); // Exponential backoff
          setTimeout(() => {
            console.log(`Reconnecting... attempt ${reconnectAttempts + 1}`);
            setReconnectAttempts(prev => prev + 1);
            sendMessage(message);
          }, delay);
        } else {
          // Max retries exceeded
          setStreamState({
            type: 'error',
            error: 'Connection lost. Please try again.',
            code: 'MAX_RETRIES'
          });

          if (onError) {
            onError('Connection lost. Please try again.', 'MAX_RETRIES');
          }

          eventSource.close();
          eventSourceRef.current = null;
        }
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
