// Standard API Envelope and Error Contracts

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ApiMeta {
  timestamp: string;
  request_id?: string;
}

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
  message?: string;
}

export interface ApiErrorEnvelope {
  code: string;
  message: string;
  details?: ApiErrorDetail[] | unknown[];
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  pagination?: PaginationMeta;
  meta: ApiMeta;
  error?: ApiErrorEnvelope;
}
