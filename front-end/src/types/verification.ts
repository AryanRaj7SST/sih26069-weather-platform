// Operator Verification & Triage Models

import { RejectionReasonCode } from './enums';

export interface VerificationQueueParams {
  page?: number;
  page_size?: number;
  priority?: 'HIGH' | 'NORMAL' | string;
  category?: string;
  jurisdiction?: string;
}

export interface VerificationEventDetail {
  id: string;
  previous_status: string;
  new_status: string;
  notes: string | null;
  action_metadata: Record<string, unknown> | null;
  created_at: string;
  reviewer_name: string;
}

export interface ReportVerifyRequest {
  notes?: string;
  broadcast_alert?: boolean;
}

export interface ReportRejectRequest {
  rejection_reason?: RejectionReasonCode | string;
  notes?: string;
}

export interface ReportDuplicateRequest {
  primary_report_id?: string;
  notes?: string;
}

export interface ReportReviewRequest {
  notes?: string;
}
