// Core Domain Enums & Types conforming to docs/DATA_MODEL.md and docs/API_CONTRACT.md

export type SeverityLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE' | 'CRITICAL';

export type VerificationStatus =
  | 'PENDING'
  | 'UNDER_REVIEW'
  | 'VERIFIED'
  | 'REJECTED'
  | 'DUPLICATE';

export type ProcessingStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    timestamp: string;
    request_id?: string;
  };
  pagination?: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
  error?: {
    code: string;
    message: string;
    details?: unknown[];
  };
}

export interface HealthStatus {
  status: string;
  service: string;
  environment: string;
  version: string;
}
