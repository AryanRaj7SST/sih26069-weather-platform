// Unit & Integration Tests for Dashboard and Analytics Aggregation API Clients & Query Keys

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { dashboardApi } from '../services/dashboardApi';
import { analyticsApi } from '../services/analyticsApi';
import { dashboardKeys, analyticsKeys } from '../lib/queryKeys';
import { ApiError } from '../services/client';
import { DashboardSummaryData, AnalyticsTrendData } from '../types';

describe('Dashboard & Analytics API Clients & Query Keys', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  describe('1. dashboardApi.getSummary', () => {
    it('queries /dashboard/summary with default parameters when none provided', async () => {
      const mockData: DashboardSummaryData = {
        total_count: 50,
        period_count: 50,
        count_24h: 20,
        last_24h_pct: 40,
        verification: {
          verified_count: 25,
          verified_rate: 50,
          pending_count: 20,
          under_review_count: 5,
          rejected_count: 3,
          duplicate_count: 2,
        },
        severity: {
          severe_high_count: 15,
          severe_count: 5,
          high_count: 10,
          moderate_count: 25,
          low_count: 10,
        },
        category_distribution: [
          {
            category_code: 'FLOOD_WATERLOGGING',
            category_name: 'Flooding & Waterlogging',
            count: 20,
            percentage: 40,
          },
        ],
        diurnal_distribution: [
          { window: '00:00', label: '00:00 - 06:00', count: 10 },
          { window: '06:00', label: '06:00 - 12:00', count: 15 },
          { window: '12:00', label: '12:00 - 18:00', count: 15 },
          { window: '18:00', label: '18:00 - 24:00', count: 10 },
        ],
      };

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: true,
          data: mockData,
          meta: { timestamp: '2026-08-30T05:00:00Z' },
        }),
      });
      global.fetch = fetchMock;

      const res = await dashboardApi.getSummary();

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toBe('/api/v1/dashboard/summary');
      expect(res.success).toBe(true);
      expect(res.data.total_count).toBe(50);
      expect(res.data.verification.verified_rate).toBe(50);
      expect(res.data.diurnal_distribution).toHaveLength(4);
    });

    it('correctly serializes query parameters and strips ALL values', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: true,
          data: {
            total_count: 10,
            period_count: 10,
            count_24h: 5,
            last_24h_pct: 50,
            verification: { verified_count: 5, verified_rate: 50, pending_count: 5, under_review_count: 0, rejected_count: 0, duplicate_count: 0 },
            severity: { severe_high_count: 5, severe_count: 2, high_count: 3, moderate_count: 3, low_count: 2 },
            category_distribution: [],
            diurnal_distribution: [],
          },
          meta: { timestamp: '2026-08-30T05:00:00Z' },
        }),
      });
      global.fetch = fetchMock;

      await dashboardApi.getSummary({
        time_range: '7d',
        category: 'FLOOD_WATERLOGGING',
        severity: 'ALL',
        status: 'VERIFIED,UNDER_REVIEW',
        bbox: '72.0,18.0,73.0,19.0',
      });

      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain('time_range=7d');
      expect(url).toContain('category=FLOOD_WATERLOGGING');
      expect(url).not.toContain('severity=ALL');
      expect(url).toContain('status=VERIFIED%2CUNDER_REVIEW');
      expect(url).toContain('bbox=72.0%2C18.0%2C73.0%2C19.0');
    });

    it('propagates ApiError on 422 validation failure', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: "Invalid time_range '99d'. Allowed values: 24h, 48h, 7d, all.",
          },
        }),
      });
      global.fetch = fetchMock;

      await expect(dashboardApi.getSummary({ time_range: '99d' })).rejects.toThrow(ApiError);
    });
  });

  describe('2. analyticsApi.getTrends', () => {
    it('queries /analytics/trends with default parameters (7d)', async () => {
      const mockData: AnalyticsTrendData = {
        time_range: '7d',
        interval: 'day',
        buckets: [
          { bucket: '2026-08-24T00:00:00Z', label: 'Aug 24', total: 10, verified: 5 },
          { bucket: '2026-08-25T00:00:00Z', label: 'Aug 25', total: 12, verified: 8 },
        ],
      };

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: true,
          data: mockData,
          meta: { timestamp: '2026-08-30T05:00:00Z' },
        }),
      });
      global.fetch = fetchMock;

      const res = await analyticsApi.getTrends();

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toBe('/api/v1/analytics/trends');
      expect(res.data.time_range).toBe('7d');
      expect(res.data.interval).toBe('day');
      expect(res.data.buckets).toHaveLength(2);
    });

    it('correctly serializes 24h hourly query parameters', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: true,
          data: { time_range: '24h', interval: 'hour', buckets: [] },
          meta: { timestamp: '2026-08-30T05:00:00Z' },
        }),
      });
      global.fetch = fetchMock;

      await analyticsApi.getTrends({
        time_range: '24h',
        interval: 'hour',
        severity: 'HIGH',
      });

      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain('time_range=24h');
      expect(url).toContain('interval=hour');
      expect(url).toContain('severity=HIGH');
    });

    it('propagates ApiError on 500 server failure', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: false,
          error: {
            code: 'INTERNAL_SERVER_ERROR',
            message: 'Database query failed.',
          },
        }),
      });
      global.fetch = fetchMock;

      await expect(analyticsApi.getTrends()).rejects.toThrow(ApiError);
    });
  });

  describe('3. Query Keys Factory', () => {
    it('produces deterministic normalized query keys for dashboard summary', () => {
      const key1 = dashboardKeys.summary({ time_range: '7d', category: 'FLOOD_WATERLOGGING', severity: 'ALL' });
      const key2 = dashboardKeys.summary({ category: 'FLOOD_WATERLOGGING', time_range: '7d' });

      expect(key1).toEqual(key2);
      expect(key1).toEqual(['dashboard', 'summary', { category: 'FLOOD_WATERLOGGING', time_range: '7d' }]);
    });

    it('produces deterministic normalized query keys for analytics trends', () => {
      const key1 = analyticsKeys.trends({ time_range: '24h', interval: 'hour', bbox: undefined });
      const key2 = analyticsKeys.trends({ interval: 'hour', time_range: '24h' });

      expect(key1).toEqual(key2);
      expect(key1).toEqual(['analytics', 'trends', { interval: 'hour', time_range: '24h' }]);
    });

    it('returns clean hierarchy for empty params', () => {
      expect(dashboardKeys.summary()).toEqual(['dashboard', 'summary', undefined]);
      expect(analyticsKeys.trends()).toEqual(['analytics', 'trends', undefined]);
    });
  });
});
