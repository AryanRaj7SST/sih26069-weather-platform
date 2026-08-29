import {
  CitizenReportFormValues,
  ReportDetailResponse,
  ReportListQueryParams,
  ReportListResponse,
  ReportSubmitResponse,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

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

  // Append up to 3 media files
  for (const file of mediaFiles) {
    formData.append('media_files', file, file.name);
  }

  const response = await fetch(`${API_BASE_URL}/reports`, {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();

  if (!response.ok || !data.success) {
    const errorMsg =
      data.error?.message ||
      (data.detail?.message ? data.detail.message : 'Failed to submit report. Please check your inputs.');
    throw new Error(errorMsg);
  }

  return data as ReportSubmitResponse;
}

export async function fetchReportByTrackingId(
  idOrTracking: string
): Promise<ReportDetailResponse> {
  const cleanId = idOrTracking.trim();
  const response = await fetch(`${API_BASE_URL}/reports/${encodeURIComponent(cleanId)}`);

  const data = await response.json();

  if (!response.ok || !data.success) {
    const errorMsg =
      data.error?.message ||
      (data.detail?.message
        ? data.detail.message
        : `Weather report with ID ${cleanId} does not exist.`);
    throw new Error(errorMsg);
  }

  return data as ReportDetailResponse;
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
  const url = `${API_BASE_URL}/reports${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  const data = await response.json();

  if (!response.ok || !data.success) {
    const errorMsg =
      data.error?.message ||
      (data.detail?.message
        ? data.detail.message
        : 'Failed to fetch weather reports.');
    throw new Error(errorMsg);
  }

  return data as ReportListResponse;
}

export async function fetchAllDashboardReports(
  params: ReportListQueryParams = {}
): Promise<ReportListResponse> {
  // Fetch page 1 first (standard 100-record batch)
  const firstPage = await fetchReportList({ ...params, page: 1, page_size: 100 });
  const { total_pages, total_records } = firstPage.pagination;

  // If only 1 page or all records already returned, return immediately
  if (total_pages <= 1 || firstPage.data.length >= total_records) {
    return firstPage;
  }

  // Fetch remaining pages in parallel (bounded by total_pages, max 10 pages for safety)
  const maxPagesToFetch = Math.min(total_pages, 10);
  const pagePromises: Promise<ReportListResponse>[] = [];

  for (let pageNum = 2; pageNum <= maxPagesToFetch; pageNum++) {
    pagePromises.push(fetchReportList({ ...params, page: pageNum, page_size: 100 }));
  }

  const remainingPages = await Promise.all(pagePromises);
  const allData = [...firstPage.data];

  for (const pageRes of remainingPages) {
    allData.push(...pageRes.data);
  }

  return {
    ...firstPage,
    data: allData,
    pagination: {
      ...firstPage.pagination,
      page_size: allData.length,
      has_next: false,
    },
  };
}
