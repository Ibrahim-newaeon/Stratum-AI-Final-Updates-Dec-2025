/**
 * useWebSocket Hook Tests
 *
 * Tests for the WebSocket real-time update hook.
 * Mocks the global WebSocket class and React Query's useQueryClient.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mock React Query
// ---------------------------------------------------------------------------

const mockSetQueryData = vi.fn();
const mockInvalidateQueries = vi.fn();

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    setQueryData: mockSetQueryData,
    invalidateQueries: mockInvalidateQueries,
  }),
}));

// ---------------------------------------------------------------------------
// Mock WebSocket
// ---------------------------------------------------------------------------

type WSHandler = ((event: any) => void) | null;

class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  static CONNECTING = 0;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: WSHandler = null;
  onclose: WSHandler = null;
  onmessage: WSHandler = null;
  onerror: WSHandler = null;
  send = vi.fn();
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  // Test helpers
  static instances: MockWebSocket[] = [];
  static reset() {
    MockWebSocket.instances = [];
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.({});
  }

  simulateMessage(data: any) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({});
  }

  simulateError() {
    this.onerror?.({});
  }
}

// Set static properties for readyState checks
Object.defineProperty(MockWebSocket, 'OPEN', { value: 1, writable: false });
Object.defineProperty(MockWebSocket, 'CLOSED', { value: 3, writable: false });
Object.defineProperty(MockWebSocket, 'CONNECTING', { value: 0, writable: false });

vi.stubGlobal('WebSocket', MockWebSocket);

// ---------------------------------------------------------------------------
// Import hook after mocks
// ---------------------------------------------------------------------------

import { useWebSocket } from './useWebSocket';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.reset();
    mockSetQueryData.mockClear();
    mockInvalidateQueries.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // -------------------------------------------------------------------------
  // Connection
  // -------------------------------------------------------------------------

  describe('Connection', () => {
    it('should auto-connect on mount by default', () => {
      renderHook(() => useWebSocket({ url: 'ws://test' }));

      expect(MockWebSocket.instances).toHaveLength(1);
      expect(MockWebSocket.instances[0].url).toBe('ws://test');
    });

    it('should not auto-connect when autoConnect is false', () => {
      renderHook(() => useWebSocket({ url: 'ws://test', autoConnect: false }));

      expect(MockWebSocket.instances).toHaveLength(0);
    });

    it('should set connectionState to connected on open', () => {
      const { result } = renderHook(() => useWebSocket({ url: 'ws://test' }));

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
      });

      expect(result.current.connectionState).toBe('connected');
      expect(result.current.isConnected).toBe(true);
    });

    it('should call onConnect callback when connection opens', () => {
      const onConnect = vi.fn();
      renderHook(() => useWebSocket({ url: 'ws://test', onConnect }));

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
      });

      expect(onConnect).toHaveBeenCalledTimes(1);
    });

    it('should set connectionState to connecting initially', () => {
      const { result } = renderHook(() => useWebSocket({ url: 'ws://test' }));

      expect(result.current.connectionState).toBe('connecting');
    });
  });

  // -------------------------------------------------------------------------
  // Messages
  // -------------------------------------------------------------------------

  describe('Messages', () => {
    it('should update lastMessage on incoming message', () => {
      const { result } = renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      const msg = { type: 'emq_update', payload: { score: 85 }, timestamp: '2025-01-01T00:00:00Z' };
      act(() => {
        ws.simulateMessage(msg);
      });

      expect(result.current.lastMessage).toEqual(msg);
    });

    it('should call onMessage callback with parsed message', () => {
      const onMessage = vi.fn();
      renderHook(() => useWebSocket({ url: 'ws://test', onMessage }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      const msg = { type: 'test', payload: { data: 1 }, timestamp: '2025-01-01T00:00:00Z' };
      act(() => {
        ws.simulateMessage(msg);
      });

      expect(onMessage).toHaveBeenCalledWith(msg);
    });

    it('should handle emq_update by updating query cache', () => {
      renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        ws.simulateMessage({
          type: 'emq_update',
          payload: { tenantId: 1, score: 90 },
          timestamp: '2025-01-01',
        });
      });

      expect(mockSetQueryData).toHaveBeenCalledWith(
        ['emq', 'score', 1],
        expect.any(Function)
      );
    });

    it('should handle incident messages by invalidating queries', () => {
      renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        ws.simulateMessage({
          type: 'incident_opened',
          payload: { tenantId: 42 },
          timestamp: '2025-01-01',
        });
      });

      expect(mockInvalidateQueries).toHaveBeenCalledWith({
        queryKey: ['emq', 'incidents', 42],
      });
    });

    it('should handle autopilot_mode_change by updating query cache', () => {
      renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        ws.simulateMessage({
          type: 'autopilot_mode_change',
          payload: { tenantId: 5, mode: 'active' },
          timestamp: '2025-01-01',
        });
      });

      expect(mockSetQueryData).toHaveBeenCalledWith(
        ['autopilot', 5],
        expect.any(Function)
      );
    });

    it('should handle platform_status by updating query cache', () => {
      renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        ws.simulateMessage({
          type: 'platform_status',
          payload: { platform: 'meta', status: 'healthy' },
          timestamp: '2025-01-01',
        });
      });

      expect(mockSetQueryData).toHaveBeenCalledWith(
        ['platforms', 'status'],
        expect.any(Function)
      );
    });
  });

  // -------------------------------------------------------------------------
  // Send
  // -------------------------------------------------------------------------

  describe('Send', () => {
    it('should send JSON message when connected', () => {
      const { result } = renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        result.current.send('test_event', { key: 'value' });
      });

      expect(ws.send).toHaveBeenCalledTimes(1);
      const sentData = JSON.parse(ws.send.mock.calls[0][0]);
      expect(sentData.type).toBe('test_event');
      expect(sentData.payload).toEqual({ key: 'value' });
      expect(sentData.timestamp).toBeDefined();
    });

    it('should not send when not connected', () => {
      const { result } = renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      // Don't open connection
      act(() => {
        result.current.send('test', { data: 1 });
      });

      expect(ws.send).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Disconnect
  // -------------------------------------------------------------------------

  describe('Disconnect', () => {
    it('should set connectionState to disconnected on close', () => {
      const { result } = renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        ws.simulateClose();
      });

      expect(result.current.connectionState).toBe('disconnected');
      expect(result.current.isConnected).toBe(false);
    });

    it('should call onDisconnect callback', () => {
      const onDisconnect = vi.fn();
      renderHook(() => useWebSocket({ url: 'ws://test', onDisconnect }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        ws.simulateClose();
      });

      expect(onDisconnect).toHaveBeenCalledTimes(1);
    });

    it('should close WebSocket when disconnect is called', () => {
      const { result } = renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        result.current.disconnect();
      });

      expect(ws.close).toHaveBeenCalled();
      expect(result.current.connectionState).toBe('disconnected');
    });
  });

  // -------------------------------------------------------------------------
  // Error handling
  // -------------------------------------------------------------------------

  describe('Error Handling', () => {
    it('should set connectionState to error on WebSocket error', () => {
      const { result } = renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateError();
      });

      expect(result.current.connectionState).toBe('error');
    });

    it('should call onError callback', () => {
      const onError = vi.fn();
      renderHook(() => useWebSocket({ url: 'ws://test', onError }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateError();
      });

      expect(onError).toHaveBeenCalledTimes(1);
    });
  });

  // -------------------------------------------------------------------------
  // Reconnection
  // -------------------------------------------------------------------------

  describe('Reconnection', () => {
    it('should attempt reconnection after disconnect', () => {
      renderHook(() =>
        useWebSocket({ url: 'ws://test', reconnectAttempts: 3, reconnectInterval: 1000 })
      );
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        ws.simulateClose();
      });

      // Should schedule reconnection
      act(() => {
        vi.advanceTimersByTime(1000);
      });

      // A new WebSocket instance should have been created
      expect(MockWebSocket.instances.length).toBeGreaterThan(1);
    });

    it('should not reconnect after manual disconnect', () => {
      const { result } = renderHook(() =>
        useWebSocket({ url: 'ws://test', reconnectAttempts: 3, reconnectInterval: 500 })
      );
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      const instancesBefore = MockWebSocket.instances.length;

      act(() => {
        result.current.disconnect();
      });

      act(() => {
        vi.advanceTimersByTime(5000);
      });

      // No new instances should be created after manual disconnect
      expect(MockWebSocket.instances.length).toBe(instancesBefore);
    });
  });

  // -------------------------------------------------------------------------
  // Cleanup
  // -------------------------------------------------------------------------

  describe('Cleanup', () => {
    it('should disconnect on unmount', () => {
      const { unmount } = renderHook(() => useWebSocket({ url: 'ws://test' }));
      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      unmount();

      expect(ws.close).toHaveBeenCalled();
    });
  });
});
