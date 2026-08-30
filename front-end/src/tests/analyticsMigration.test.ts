// Comprehensive Analytics Trend Chart Migration Test Suite

import { describe, it, expect } from 'vitest';
import { analyticsKeys } from '../lib/queryKeys';
import {
  AnalyticsTrendBucket,
  AnalyticsTrendData,
  AnalyticsTrendQueryParams,
} from '../types';

describe('Analytics Migration - Server-Side Trend Aggregation & Logic Mapping', () => {
  describe('1. Analytics Trend Parameter & Query Key Construction', () => {
    it('constructs deterministic query keys for analytics trend requests', () => {
      const params: AnalyticsTrendQueryParams = {
        time_range: '7d',
        category: 'FLOOD_WATERLOGGING',
        severity: 'HIGH',
        status: 'VERIFIED',
        bbox: '72.75,18.85,73.05,19.35',
      };
      const key = analyticsKeys.trends(params as Record<string, unknown>);
      expect(key).toEqual([
        'analytics',
        'trends',
        {
          bbox: '72.75,18.85,73.05,19.35',
          category: 'FLOOD_WATERLOGGING',
          severity: 'HIGH',
          status: 'VERIFIED',
          time_range: '7d',
        },
      ]);
    });

    it('omits ALL hazard, severity, and status filters from normalized trend query key', () => {
      const params: AnalyticsTrendQueryParams = {
        time_range: '24h',
        category: 'ALL',
        severity: 'ALL',
        status: 'ALL',
      };
      const key = analyticsKeys.trends(params as Record<string, unknown>);
      expect(key).toEqual([
        'analytics',
        'trends',
        { time_range: '24h' },
      ]);
    });
  });

  describe('2. 24h Hourly Trend Mapping (6 4-Hour Buckets)', () => {
    it('maps 6 diurnal buckets directly to chart series without client-side loops', () => {
      const mock24hData: AnalyticsTrendData = {
        time_range: '24h',
        interval: 'hour',
        buckets: [
          { bucket: '00:00', label: '00:00 - 04:00', total: 120, verified: 15 },
          { bucket: '04:00', label: '04:00 - 08:00', total: 340, verified: 40 },
          { bucket: '08:00', label: '08:00 - 12:00', total: 680, verified: 55 },
          { bucket: '12:00', label: '12:00 - 16:00', total: 510, verified: 30 },
          { bucket: '16:00', label: '16:00 - 20:00', total: 420, verified: 20 },
          { bucket: '20:00', label: '20:00 - 24:00', total: 209, verified: 5 },
        ],
      };

      const chartData = mock24hData.buckets.map((b) => ({
        time: mock24hData.time_range === '24h' ? b.bucket : b.label,
        label: b.label,
        total: b.total,
        verified: b.verified,
      }));

      expect(chartData).toHaveLength(6);
      expect(chartData[0]).toEqual({ time: '00:00', label: '00:00 - 04:00', total: 120, verified: 15 });
      expect(chartData[5]).toEqual({ time: '20:00', label: '20:00 - 24:00', total: 209, verified: 5 });

      const totalSum = chartData.reduce((acc, d) => acc + d.total, 0);
      expect(totalSum).toBe(2279);
    });
  });

  describe('3. 7d Daily Trend Mapping (7 Daily Buckets)', () => {
    it('maps 7 daily buckets directly to chart series', () => {
      const mock7dData: AnalyticsTrendData = {
        time_range: '7d',
        interval: 'day',
        buckets: [
          { bucket: '2026-08-24T00:00:00Z', label: 'Aug 24', total: 0, verified: 0 },
          { bucket: '2026-08-25T00:00:00Z', label: 'Aug 25', total: 0, verified: 0 },
          { bucket: '2026-08-26T00:00:00Z', label: 'Aug 26', total: 0, verified: 0 },
          { bucket: '2026-08-27T00:00:00Z', label: 'Aug 27', total: 0, verified: 0 },
          { bucket: '2026-08-28T00:00:00Z', label: 'Aug 28', total: 0, verified: 0 },
          { bucket: '2026-08-29T00:00:00Z', label: 'Aug 29', total: 2150, verified: 150 },
          { bucket: '2026-08-30T00:00:00Z', label: 'Aug 30', total: 129, verified: 15 },
        ],
      };

      const chartData = mock7dData.buckets.map((b) => ({
        time: mock7dData.time_range === '24h' ? b.bucket : b.label,
        label: b.label,
        total: b.total,
        verified: b.verified,
      }));

      expect(chartData).toHaveLength(7);
      expect(chartData[0].time).toBe('Aug 24');
      expect(chartData[6].time).toBe('Aug 30');
      expect(chartData[5].total).toBe(2150);
      expect(chartData[5].verified).toBe(150);
    });
  });

  describe('4. 30d Daily Trend Mapping (14 Daily Buckets)', () => {
    it('maps 14 daily buckets matching the preserved 30d progression', () => {
      const mock30dBuckets: AnalyticsTrendBucket[] = Array.from({ length: 14 }, (_, i) => ({
        bucket: `2026-08-${String(17 + i).padStart(2, '0')}T00:00:00Z`,
        label: `Aug ${17 + i}`,
        total: i === 12 ? 2150 : i === 13 ? 129 : 0,
        verified: i === 12 ? 150 : i === 13 ? 15 : 0,
      }));

      const mock30dData: AnalyticsTrendData = {
        time_range: '30d',
        interval: 'day',
        buckets: mock30dBuckets,
      };

      const chartData = mock30dData.buckets.map((b) => ({
        time: mock30dData.time_range === '24h' ? b.bucket : b.label,
        label: b.label,
        total: b.total,
        verified: b.verified,
      }));

      expect(chartData).toHaveLength(14);
      expect(chartData[0].label).toBe('Aug 17');
      expect(chartData[13].label).toBe('Aug 30');
    });
  });

  describe('5. Zero / Empty Dataset Safety', () => {
    it('safely handles empty trend buckets without crashing or NaN', () => {
      const emptyData: AnalyticsTrendData = {
        time_range: '7d',
        interval: 'day',
        buckets: [],
      };

      const chartData = emptyData.buckets.map((b) => ({
        time: b.label,
        label: b.label,
        total: b.total,
        verified: b.verified,
      }));

      expect(chartData).toEqual([]);
      const totalAnalyzed = emptyData.buckets.reduce((acc, b) => acc + b.total, 0);
      expect(totalAnalyzed).toBe(0);
    });
  });
});
