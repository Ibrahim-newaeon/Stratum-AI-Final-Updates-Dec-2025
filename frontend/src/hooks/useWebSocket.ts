/**
 * WebSocket Hook for Real-Time Updates
 *
 * Provides real-time data synchronization for EMQ scores,
 * incidents, and action recommendations
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

type MessageHandler = (data: any) => void;
type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
}

interface UseWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  onMessage?: MessageHandler;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

const DEFAULT_WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = DEFAULT_WS_URL,
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const queryClient = useQueryClient();

  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionState('connected');
        reconnectCountRef.current = 0;
        onConnect?.();
        console.log('[WebSocket] Connected');
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          handleMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.onclose = () => {
        setConnectionState('disconnected');
        onDisconnect?.();
        console.log('[WebSocket] Disconnected');

        // Attempt reconnection
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          console.log(
            `[WebSocket] Reconnecting... (${reconnectCountRef.current}/${reconnectAttempts})`
          );
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        setConnectionState('error');
        onError?.(error);
        console.error('[WebSocket] Error:', error);
      };
    } catch (error) {
      setConnectionState('error');
      console.error('[WebSocket] Connection failed:', error);
    }
  }, [url, reconnectAttempts, reconnectInterval, onConnect, onDisconnect, onError, onMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    reconnectCountRef.current = reconnectAttempts; // Prevent auto-reconnect
    wsRef.current?.close();
    wsRef.current = null;
    setConnectionState('disconnected');
  }, [reconnectAttempts]);

  const send = useCallback((type: string, payload: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = {
        type,
        payload,
        timestamp: new Date().toISOString(),
      };
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send - not connected');
    }
  }, []);

  // Handle incoming messages and update React Query cache
  const handleMessage = useCallback(
    (message: WebSocketMessage) => {
      switch (message.type) {
        case 'emq_update':
          // Update EMQ score in cache
          queryClient.setQueryData(['emq', 'score', message.payload.tenantId], (old: any) => ({
            ...old,
            score: message.payload.score,
            previousScore: old?.score,
            updatedAt: message.timestamp,
          }));
          break;

        case 'incident_opened':
        case 'incident_closed':
          // Invalidate incidents query to refetch
          queryClient.invalidateQueries({
            queryKey: ['emq', 'incidents', message.payload.tenantId],
          });
          break;

        case 'autopilot_mode_change':
          // Update autopilot state
          queryClient.setQueryData(['autopilot', message.payload.tenantId], (old: any) => ({
            ...old,
            mode: message.payload.mode,
            changedAt: message.timestamp,
          }));
          break;

        case 'action_recommendation':
          // Invalidate recommendations to refetch
          queryClient.invalidateQueries({
            queryKey: ['tenant', message.payload.tenantId, 'recommendations'],
          });
          break;

        case 'platform_status':
          // Update platform status in cache
          queryClient.setQueryData(['platforms', 'status'], (old: any) => ({
            ...old,
            [message.payload.platform]: message.payload.status,
          }));
          break;

        default:
          console.log('[WebSocket] Unhandled message type:', message.type);
      }
    },
    [queryClient]
  );

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    connectionState,
    lastMessage,
    connect,
    disconnect,
    send,
    isConnected: connectionState === 'connected',
  };
}

/**
 * Hook for subscribing to specific WebSocket channels
 */
export function useWebSocketChannel(channel: string, onMessage: MessageHandler, deps: any[] = []) {
  const { send, connectionState, isConnected } = useWebSocket({
    onMessage: (message) => {
      if (message.type === channel || message.type.startsWith(`${channel}:`)) {
        onMessage(message.payload);
      }
    },
  });

  // Subscribe to channel on connect
  useEffect(() => {
    if (isConnected) {
      send('subscribe', { channel });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected, channel, ...deps]);

  return { connectionState, isConnected };
}

/**
 * Hook for real-time EMQ score updates
 */
export function useRealtimeEmq(tenantId: number) {
  const queryClient = useQueryClient();
  const [score, setScore] = useState<number | null>(null);

  useWebSocketChannel(
    'emq_update',
    (payload) => {
      if (payload.tenantId === tenantId) {
        setScore(payload.score);
        // Also update the query cache
        queryClient.setQueryData(['emq', 'score', tenantId], (old: any) => ({
          ...old,
          score: payload.score,
          previousScore: old?.score,
        }));
      }
    },
    [tenantId]
  );

  return score;
}

/**
 * Hook for real-time incident notifications
 */
export function useRealtimeIncidents(tenantId: number) {
  const [latestIncident, setLatestIncident] = useState<any>(null);

  useWebSocketChannel(
    'incident',
    (payload) => {
      if (payload.tenantId === tenantId) {
        setLatestIncident(payload);
      }
    },
    [tenantId]
  );

  return latestIncident;
}

export default useWebSocket;
