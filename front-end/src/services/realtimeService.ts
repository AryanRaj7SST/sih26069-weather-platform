// Centralized Frontend Realtime Service & SSE Event Manager

import { QueryClient } from '@tanstack/react-query';
import { API_BASE_URL } from '@/services/client';
import { incidentKeys, dashboardKeys, analyticsKeys } from '@/lib/queryKeys';
import {
  RealtimeConnectionState,
  RealtimeEvent,
  RealtimeEventSubscriber,
  RealtimeStateSubscriber,
} from '@/types/realtime';

export const MAX_DEDUPE_SIZE = 1000;

export class RealtimeService {
  private eventSource: EventSource | null = null;
  private queryClient: QueryClient | null = null;
  private connectionState: RealtimeConnectionState = 'closed';
  private eventSubscribers: Set<RealtimeEventSubscriber> = new Set();
  private stateSubscribers: Set<RealtimeStateSubscriber> = new Set();
  private seenEventIds: Set<string> = new Set();
  private seenEventIdQueue: string[] = [];
  private isExplicitlyClosed: boolean = false;
  private isOnline: boolean =
    typeof navigator !== 'undefined' && typeof navigator.onLine === 'boolean' ? navigator.onLine : true;
  private cleanupWindowListeners: (() => void) | null = null;

  constructor() {
    this.setupWindowListeners();
  }

  /**
   * Attach browser online/offline event listeners.
   */
  private setupWindowListeners(): void {
    if (typeof window === 'undefined') return;

    const handleOnline = () => {
      this.isOnline = true;
      if (!this.isExplicitlyClosed && this.queryClient && !this.eventSource) {
        this.connect();
      }
    };

    const handleOffline = () => {
      this.isOnline = false;
      this.disconnect(false);
      this.updateState('error');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    this.cleanupWindowListeners = () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }

  /**
   * Set QueryClient and connect to SSE stream if not already active.
   */
  public initialize(queryClient: QueryClient): void {
    this.queryClient = queryClient;
    this.isExplicitlyClosed = false;
    if (!this.eventSource && this.isOnline) {
      this.connect();
    }
  }

  /**
   * Establish the singleton EventSource connection.
   */
  public connect(): void {
    const EventSourceClass =
      (typeof window !== 'undefined' && (window as unknown as { EventSource?: typeof EventSource }).EventSource) ||
      (typeof globalThis !== 'undefined' &&
        (globalThis as unknown as { EventSource?: typeof EventSource }).EventSource) ||
      (typeof EventSource !== 'undefined' ? EventSource : undefined);

    if (this.eventSource || !EventSourceClass) {
      return;
    }

    const sseUrl = `${API_BASE_URL}/events/stream`;
    this.updateState('connecting');

    try {
      this.eventSource = new EventSourceClass(sseUrl, { withCredentials: true });

      this.eventSource.onopen = () => {
        this.updateState('open');
      };

      this.eventSource.onerror = () => {
        // Native EventSource automatically retries with Last-Event-ID
        if (this.eventSource?.readyState === EventSource.CLOSED) {
          this.updateState('closed');
        } else {
          this.updateState('error');
        }
      };

      // Listen for all canonical event types
      const eventTypes = [
        'report.created',
        'report.verification_changed',
        'report.intelligence_ready',
        'cluster.updated',
        'system.resync_required',
      ];

      eventTypes.forEach((eventType) => {
        this.eventSource?.addEventListener(eventType, (messageEvent: MessageEvent) => {
          this.handleIncomingEvent(eventType, messageEvent.data);
        });
      });

      // Default message handler fallback
      this.eventSource.onmessage = (messageEvent: MessageEvent) => {
        this.handleIncomingEvent('message', messageEvent.data);
      };
    } catch {
      this.updateState('error');
    }
  }

  /**
   * Process, validate, deduplicate, and dispatch incoming raw SSE message data.
   */
  public handleIncomingEvent(eventType: string, rawData: string): void {
    if (!rawData || typeof rawData !== 'string') {
      return;
    }

    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(rawData);
    } catch {
      // Malformed JSON safely ignored
      return;
    }

    if (!parsed || typeof parsed !== 'object') {
      return;
    }

    const eventId = typeof parsed.event_id === 'string' ? parsed.event_id : '';
    if (!eventId) {
      // Must contain a valid event_id
      return;
    }

    // Bounded deduplication check
    if (this.seenEventIds.has(eventId)) {
      return;
    }

    this.recordSeenEventId(eventId);

    const event: RealtimeEvent = {
      event_id: eventId,
      event_type: (typeof parsed.event_type === 'string' ? parsed.event_type : eventType),
      occurred_at: typeof parsed.occurred_at === 'string' ? parsed.occurred_at : new Date().toISOString(),
      entity_id: typeof parsed.entity_id === 'string' ? parsed.entity_id : '',
      tracking_id: typeof parsed.tracking_id === 'string' ? parsed.tracking_id : null,
      payload: (parsed.payload && typeof parsed.payload === 'object' ? parsed.payload : {}) as Record<string, unknown>,
    };

    // Centralized React Query invalidation
    this.invalidateQueriesForEvent(event);

    // Notify registered subscribers
    this.eventSubscribers.forEach((subscriber) => {
      try {
        subscriber(event);
      } catch {
        // Prevent rogue subscriber from breaking event loop
      }
    });
  }

  /**
   * Centralized query invalidation matrix mapping domain/system events to React Query keys.
   */
  public invalidateQueriesForEvent(event: RealtimeEvent): void {
    if (!this.queryClient) return;

    switch (event.event_type) {
      case 'report.created':
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.lists() });
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.geoAll() });
        this.queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
        this.queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.verificationQueues() });
        break;

      case 'report.verification_changed':
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.lists() });
        if (event.entity_id) {
          this.queryClient.invalidateQueries({ queryKey: incidentKeys.detail(event.entity_id) });
        }
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.geoAll() });
        this.queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
        this.queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.verificationQueues() });
        break;

      case 'report.intelligence_ready':
        if (event.entity_id) {
          this.queryClient.invalidateQueries({ queryKey: incidentKeys.detail(event.entity_id) });
        }
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.lists() });
        this.queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
        break;

      case 'cluster.updated':
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.geoAll() });
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.all });
        this.queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
        break;

      case 'system.resync_required':
        // Broad authoritative state revalidation
        this.queryClient.invalidateQueries({ queryKey: incidentKeys.all });
        this.queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
        this.queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
        break;

      default:
        break;
    }
  }

  /**
   * Record seen event_id in bounded memory buffer.
   */
  private recordSeenEventId(eventId: string): void {
    this.seenEventIds.add(eventId);
    this.seenEventIdQueue.push(eventId);

    if (this.seenEventIdQueue.length > MAX_DEDUPE_SIZE) {
      const oldestId = this.seenEventIdQueue.shift();
      if (oldestId) {
        this.seenEventIds.delete(oldestId);
      }
    }
  }

  /**
   * Subscribe to real-time events. Returns an unsubscribe cleanup function.
   */
  public subscribe(subscriber: RealtimeEventSubscriber): () => void {
    this.eventSubscribers.add(subscriber);
    return () => {
      this.eventSubscribers.delete(subscriber);
    };
  }

  /**
   * Subscribe to connection state changes. Returns an unsubscribe cleanup function.
   */
  public subscribeState(subscriber: RealtimeStateSubscriber): () => void {
    this.stateSubscribers.add(subscriber);
    subscriber(this.connectionState);
    return () => {
      this.stateSubscribers.delete(subscriber);
    };
  }

  /**
   * Get the current connection state.
   */
  public getState(): RealtimeConnectionState {
    return this.connectionState;
  }

  /**
   * Disconnect and release the EventSource socket.
   */
  public disconnect(explicit: boolean = true): void {
    if (explicit) {
      this.isExplicitlyClosed = true;
    }

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    this.updateState('closed');
  }

  /**
   * Tear down all resources, subscribers, and listeners.
   */
  public destroy(): void {
    this.disconnect(true);
    this.eventSubscribers.clear();
    this.stateSubscribers.clear();
    this.seenEventIds.clear();
    this.seenEventIdQueue = [];
    this.queryClient = null;

    if (this.cleanupWindowListeners) {
      this.cleanupWindowListeners();
      this.cleanupWindowListeners = null;
    }
  }

  private updateState(newState: RealtimeConnectionState): void {
    if (this.connectionState !== newState) {
      this.connectionState = newState;
      this.stateSubscribers.forEach((subscriber) => {
        try {
          subscriber(newState);
        } catch {
          // Prevent rogue subscriber from breaking state loop
        }
      });
    }
  }
}

export const realtimeService = new RealtimeService();
