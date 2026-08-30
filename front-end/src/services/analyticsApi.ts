// Analytics Aggregation API Client

import { ApiResponse, AnalyticsTrendData, AnalyticsTrendQueryParams } from '@/types';
import { apiClient } from './client';

export const analyticsApi = {
  /**
   * Retrieve SQL-aggregated time-series trend buckets for analytics charts.
   */
  async getTrends(
    params: AnalyticsTrendQueryParams = {},
    signal?: AbortSignal
  ): Promise<ApiResponse<AnalyticsTrendData>> {
    const searchParams = new URLSearchParams();
    if (params.time_range) searchParams.append('time_range', params.time_range);
    if (params.interval) searchParams.append('interval', params.interval);
    if (params.category && params.category !== 'ALL') searchParams.append('category', params.category);
    if (params.severity && params.severity !== 'ALL') searchParams.append('severity', params.severity);
    if (params.status && params.status !== 'ALL') searchParams.append('status', params.status);
    if (params.bbox) searchParams.append('bbox', params.bbox);

    const query = searchParams.toString();
    return apiClient<ApiResponse<AnalyticsTrendData>>(`/analytics/trends${query ? `?${query}` : ''}`, { signal });
  },
};
