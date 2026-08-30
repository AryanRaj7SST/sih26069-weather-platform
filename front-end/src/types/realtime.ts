// Canonical Frontend Realtime Event Contract matching Backend SSE stream

export type RealtimeEventType =
  | 'report.created'
  | 'report.verification_changed'
  | 'report.intelligence_ready'
  | 'cluster.updated'
  | 'system.heartbeat'
  | 'system.resync_required';

export interface ReportCreatedPayload {
  tracking_id: string;
  category_code: string;
  severity: string;
  verification_status: string;
  location_name?: string | null;
  latitude: number;
  longitude: number;
  occurred_at: string;
  has_media?: boolean;
}

export interface ReportVerificationChangedPayload {
  tracking_id: string;
  category_code: string;
  previous_status: string;
  new_status: string;
  reason?: string | null;
  verified_at: string;
}

export interface ReportIntelligenceReadyPayload {
  tracking_id: string;
  credibility_score: number;
  readiness: string;
  cluster_id?: string | null;
  corroborated?: boolean;
}

export interface ClusterUpdatedPayload {
  cluster_id: string;
  member_count: number;
  primary_report_id: string;
  centroid_latitude: number;
  centroid_longitude: number;
  radius_meters?: number;
}

export interface SystemResyncRequiredPayload {
  reason: string;
  message: string;
  requested_last_event_id?: string;
  oldest_available_id?: string;
}

export type RealtimeEventPayload =
  | ReportCreatedPayload
  | ReportVerificationChangedPayload
  | ReportIntelligenceReadyPayload
  | ClusterUpdatedPayload
  | SystemResyncRequiredPayload
  | Record<string, unknown>;

export interface RealtimeEvent<T = RealtimeEventPayload> {
  event_id: string;
  event_type: RealtimeEventType | string;
  occurred_at: string;
  entity_id: string;
  tracking_id?: string | null;
  payload: T;
}

export type RealtimeConnectionState = 'connecting' | 'open' | 'error' | 'closed';

export type RealtimeEventSubscriber = (event: RealtimeEvent) => void;
export type RealtimeStateSubscriber = (state: RealtimeConnectionState) => void;
