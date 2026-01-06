/**
 * WebSocket client for real-time case collaboration
 */

export type WebSocketEventType =
  | 'user_joined'
  | 'user_left'
  | 'presence_update'
  | 'deadline_updated'
  | 'document_updated'
  | 'user_typing'
  | 'chat_message'
  | 'case_updated'
  | 'error'
  | 'pong';

export interface WebSocketMessage {
  type: WebSocketEventType;
  data: any;
  timestamp?: string;
}

export interface WebSocketConfig {
  url: string;
  token: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private eventHandlers: Map<WebSocketEventType, Set<Function>> = new Map();
  private isManualClose = false;

  constructor(config: WebSocketConfig) {
    this.config = config;
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    this.isManualClose = false;
    const wsUrl = `${this.config.url}?token=${this.config.token}`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);

    try {
      // WebSocket connection - this may fail silently in some environments
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;

        // Start ping interval to keep connection alive
        this.startPingInterval();

        if (this.config.onConnect) {
          this.config.onConnect();
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('WebSocket message received:', message.type, message.data);

          // Call global message handler
          if (this.config.onMessage) {
            this.config.onMessage(message);
          }

          // Call event-specific handlers
          const handlers = this.eventHandlers.get(message.type);
          if (handlers) {
            handlers.forEach((handler) => handler(message.data));
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.warn('WebSocket connection error - app will continue in offline mode');
        // Don't propagate error to avoid breaking the app
        if (this.config.onError) {
          this.config.onError(error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);

        this.stopPingInterval();

        if (this.config.onDisconnect) {
          this.config.onDisconnect();
        }

        // Don't reconnect immediately on clean close (React strict mode)
        const isCleanClose = event.code === 1000 || event.code === 1001;

        // Attempt reconnection with exponential backoff
        if (!this.isManualClose && !isCleanClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(
            `Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`
          );

          this.reconnectTimer = setTimeout(() => {
            this.connect();
          }, this.reconnectDelay);

          // Exponential backoff: 1s, 2s, 4s, 8s, 16s
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, 16000);
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.log('Max reconnection attempts reached - running in offline mode');
        } else if (isCleanClose) {
          console.log('WebSocket closed cleanly - not reconnecting');
        }
      };
    } catch (error) {
      console.warn('WebSocket not available - app will continue in offline mode:', error);
      // Don't throw error, just fail silently
      if (this.config.onDisconnect) {
        this.config.onDisconnect();
      }
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isManualClose = true;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopPingInterval();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Send message to server
   */
  send(type: string, data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = {
        type,
        data,
        timestamp: new Date().toISOString(),
      };
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  /**
   * Subscribe to specific event type
   */
  on(eventType: WebSocketEventType, handler: Function): () => void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }

    this.eventHandlers.get(eventType)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.eventHandlers.get(eventType);
      if (handlers) {
        handlers.delete(handler);
      }
    };
  }

  /**
   * Send typing indicator
   */
  sendTyping(isTyping: boolean): void {
    this.send(isTyping ? 'typing' : 'stop_typing', {});
  }

  /**
   * Request presence update
   */
  requestPresence(): void {
    this.send('get_presence', {});
  }

  /**
   * Get connection state
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send('ping', { timestamp: Date.now() });
      }
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}

/**
 * Create WebSocket client for a case room
 */
export function createCaseWebSocket(caseId: string, token: string): WebSocketClient {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = process.env.NEXT_PUBLIC_WS_URL || 'localhost:8000';
  const wsUrl = `${wsProtocol}//${wsHost}/ws/cases/${caseId}`;

  // Ensure token exists, use a demo token if not
  const validToken = token || 'demo-token-for-websocket-connection';

  return new WebSocketClient({
    url: wsUrl,
    token: validToken,
  });
}
