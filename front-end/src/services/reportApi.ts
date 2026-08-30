// Backward-Compatible Facade for Citizen Intake and Legacy Components

import {
  CitizenReportFormValues,
  ReportDetailResponse,
  ReportListQueryParams,
  ReportListResponse,
  ReportSubmitResponse,
} from '@/types';
import { apiClient, API_BASE_URL } from './client';
import { incidentApi } from './incidentApi';

export async function submitCitizenReport(
  values: CitizenReportFormValues,
  mediaFiles: File[] = []
): Promise<ReportSubmitResponse> {
  const formData = new FormData();

  formData.append('latitude', values.latitude.toString());
  formData.append('longitude', values.longitude.toString());
  formData.append('category_code', values.category_code);
  formData.append('severity', values.severity);
  formData.append('title', values.title);

  if (values.description && values.description.trim()) {
    formData.append('description', values.description.trim());
  }

  if (values.location_name && values.location_name.trim()) {
    formData.append('location_name', values.location_name.trim());
  }

  if (values.occurred_at) {
    formData.append('occurred_at', values.occurred_at);
  }

  for (const file of mediaFiles) {
    formData.append('media_files', file, file.name);
  }

  return apiClient<ReportSubmitResponse>('/reports', {
    method: 'POST',
    body: formData,
  });
}

export async function fetchReportByTrackingId(
  idOrTracking: string
): Promise<ReportDetailResponse> {
  const cleanId = encodeURIComponent(idOrTracking.trim());
  return apiClient<ReportDetailResponse>(`/reports/${cleanId}`);
}

export async function fetchReportList(
  params: ReportListQueryParams = {}
): Promise<ReportListResponse> {
  const searchParams = new URLSearchParams();

  if (params.page !== undefined) searchParams.append('page', params.page.toString());
  if (params.page_size !== undefined) searchParams.append('page_size', params.page_size.toString());
  if (params.category && params.category !== 'ALL') searchParams.append('category', params.category);
  if (params.severity && params.severity !== 'ALL') searchParams.append('severity', params.severity);
  if (params.status && params.status !== 'ALL') searchParams.append('status', params.status);
  if (params.from_date) searchParams.append('from_date', params.from_date);
  if (params.to_date) searchParams.append('to_date', params.to_date);
  if (params.min_credibility !== undefined) searchParams.append('min_credibility', params.min_credibility.toString());
  if (params.bbox) searchParams.append('bbox', params.bbox);

  const queryString = searchParams.toString();
  const url = `/reports${queryString ? `?${queryString}` : ''}`;
  return apiClient<ReportListResponse>(url);
}

export async function verifyReport(
  id: string,
  notes?: string,
  broadcastAlert?: boolean
): Promise<ReportDetailResponse> {
  const res = await incidentApi.verifyIncident(id, { notes, broadcast_alert: broadcastAlert });
  return res as unknown as ReportDetailResponse;
}

export async function rejectReport(
  id: string,
  rejectionReason?: string,
  notes?: string
): Promise<ReportDetailResponse> {
  const res = await incidentApi.rejectIncident(id, { rejection_reason: rejectionReason, notes });
  return res as unknown as ReportDetailResponse;
}

export async function markDuplicateReport(
  id: string,
  primaryReportId?: string,
  notes?: string
): Promise<ReportDetailResponse> {
  const res = await incidentApi.markDuplicateIncident(id, { primary_report_id: primaryReportId, notes });
  return res as unknown as ReportDetailResponse;
}

export async function placeReportUnderReview(
  id: string,
  notes?: string
): Promise<ReportDetailResponse> {
  const res = await incidentApi.reviewIncident(id, { notes });
  return res as unknown as ReportDetailResponse;
}

export { API_BASE_URL };
