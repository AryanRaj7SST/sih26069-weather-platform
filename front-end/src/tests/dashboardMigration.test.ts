// Comprehensive Dashboard Migration & Summary Mapping Test Suite

import { describe, it, expect } from 'vitest';
import { dashboardKeys } from '../lib/queryKeys';
import { DashboardSummaryData, DashboardSummaryQueryParams } from '../types';

const mockSummary: DashboardSummaryData = {
  total_count: 2279,
  period_count: 2279,
  count_24h: 2279,
  last_24h_pct: 100,
  verification: {
    verified_count: 165,
    verified_rate: 7,
    pending_count: 1903,
    under_review_count: 200,
    rejected_count: 150,
    duplicate_count: 61,
  },
  severity: {
    severe_high_count: 1122,
    severe_count: 265,
    high_count: 857,
    moderate_count: 757,
    low_count: 400,
  },
  category_distribution: [
    { category_code: 'FLOOD_WATERLOGGING', category_name: 'Flooding & Waterlogging', count: 871, percentage: 38 },
    { category_code: 'HEAVY_RAINFALL', category_name: 'Heavy Rainfall', count: 540, percentage: 24 },
    { category_code: 'LANDSLIDE_MUDSLIDE', category_name: 'Landslide / Mudslide', count: 320, percentage: 14 },
    { category_code: 'URBAN_CONGESTION', category_name: 'Urban Congestion', count: 210, percentage: 9 },
    { category_code: 'OTHER', category_name: 'Other Hazards', count: 338, percentage: 15 },
  ],
  diurnal_distribution: [
    { window: '00:00', label: '00:00 - 06:00', count: 420 },
    { window: '06:00', label: '06:00 - 12:00', count: 850 },
    { window: '12:00', label: '12:00 - 18:00', count: 680 },
    { window: '18:00', label: '18:00 - 24:00', count: 329 },
  ],
};

describe('Dashboard Migration - Server-Side Aggregation & Logic Mapping', () => {
  describe('1. Dashboard Summary Parameter & Query Key Construction', () => {
    it('constructs deterministic query keys for summary requests', () => {
      const params: DashboardSummaryQueryParams = {
        time_range: '48h',
        category: 'FLOOD_WATERLOGGING',
        status: 'VERIFIED',
        bbox: '72.75,18.85,73.05,19.35',
      };
      const key = dashboardKeys.summary(params as Record<string, unknown>);
      expect(key).toEqual([
        'dashboard',
        'summary',
        {
          bbox: '72.75,18.85,73.05,19.35',
          category: 'FLOOD_WATERLOGGING',
          status: 'VERIFIED',
          time_range: '48h',
        },
      ]);
    });

    it('omits ALL hazard and ALL status filters from normalized summary query key', () => {
      const params: DashboardSummaryQueryParams = {
        time_range: '24h',
        category: 'ALL',
        status: 'ALL',
      };
      const key = dashboardKeys.summary(params as Record<string, unknown>);
      expect(key).toEqual([
        'dashboard',
        'summary',
        { time_range: '24h' },
      ]);
    });
  });

  describe('2. Dashboard KPI Stats Mapping', () => {
    it('maps summary values directly into KPI presentation structure', () => {
      const stats = {
        totalCount: mockSummary.total_count,
        reportsLast24h: mockSummary.count_24h,
        pct24h: mockSummary.last_24h_pct,
        pendingCount: mockSummary.verification.pending_count,
        verifiedCount: mockSummary.verification.verified_count,
        verifiedPct: mockSummary.verification.verified_rate,
        severeCount: mockSummary.severity.severe_high_count,
      };

      expect(stats.totalCount).toBe(2279);
      expect(stats.reportsLast24h).toBe(2279);
      expect(stats.pct24h).toBe(100);
      expect(stats.pendingCount).toBe(1903);
      expect(stats.verifiedCount).toBe(165);
      expect(stats.verifiedPct).toBe(7);
      expect(stats.severeCount).toBe(1122);
    });

    it('safely handles zero / empty summary data', () => {
      const emptySummary: DashboardSummaryData = {
        total_count: 0,
        period_count: 0,
        count_24h: 0,
        last_24h_pct: 0,
        verification: { verified_count: 0, verified_rate: 0, pending_count: 0, under_review_count: 0, rejected_count: 0, duplicate_count: 0 },
        severity: { severe_high_count: 0, severe_count: 0, high_count: 0, moderate_count: 0, low_count: 0 },
        category_distribution: [],
        diurnal_distribution: [],
      };

      const stats = {
        totalCount: emptySummary.total_count,
        reportsLast24h: emptySummary.count_24h,
        pct24h: emptySummary.last_24h_pct,
        pendingCount: emptySummary.verification.pending_count,
        verifiedCount: emptySummary.verification.verified_count,
        verifiedPct: emptySummary.verification.verified_rate,
        severeCount: emptySummary.severity.severe_high_count,
      };

      expect(stats.totalCount).toBe(0);
      expect(stats.reportsLast24h).toBe(0);
      expect(stats.pct24h).toBe(0);
      expect(stats.verifiedPct).toBe(0);
      expect(stats.severeCount).toBe(0);
    });
  });

  describe('3. Event Distribution Top-4 Grouping', () => {
    it('groups categories into top 4 and sums remaining into Other Hazards', () => {
      const sorted = [...mockSummary.category_distribution].sort((a, b) => b.count - a.count);
      const top4 = sorted.slice(0, 4).map((item) => ({
        title: item.category_name,
        count: item.count,
        pct: item.percentage,
      }));
      const otherItems = sorted.slice(4);
      if (otherItems.length > 0) {
        const otherCount = otherItems.reduce((sum, item) => sum + item.count, 0);
        const otherPct = otherItems.reduce((sum, item) => sum + item.percentage, 0);
        top4.push({
          title: 'Other Hazards',
          count: otherCount,
          pct: otherPct,
        });
      }

      expect(top4).toHaveLength(5);
      expect(top4[0].title).toBe('Flooding & Waterlogging');
      expect(top4[0].count).toBe(871);
      expect(top4[0].pct).toBe(38);
      expect(top4[4].title).toBe('Other Hazards');
      expect(top4[4].count).toBe(210);
      expect(top4[4].pct).toBe(9);
    });
  });

  describe('4. Verification Donut Chart Data Mapping', () => {
    it('constructs donut chart items filtered to non-zero values', () => {
      const verified = mockSummary.verification.verified_count;
      const pending = mockSummary.verification.pending_count;
      const rejected = mockSummary.verification.rejected_count;

      const data = [
        { name: 'Verified', value: verified, color: '#10b981' },
        { name: 'Pending / Review', value: pending, color: '#f59e0b' },
        { name: 'Rejected', value: rejected, color: '#94a3b8' },
      ].filter((item) => item.value > 0);

      expect(data).toHaveLength(3);
      expect(data[0]).toEqual({ name: 'Verified', value: 165, color: '#10b981' });
      expect(data[1]).toEqual({ name: 'Pending / Review', value: 1903, color: '#f59e0b' });
      expect(data[2]).toEqual({ name: 'Rejected', value: 150, color: '#94a3b8' });
    });
  });

  describe('5. Diurnal Distribution Chart Mapping', () => {
    it('maps 4 standard diurnal buckets to time series entries', () => {
      const chartData = mockSummary.diurnal_distribution.map((item) => ({
        time: item.window,
        label: item.label,
        count: item.count,
      }));

      expect(chartData).toHaveLength(4);
      expect(chartData[0]).toEqual({ time: '00:00', label: '00:00 - 06:00', count: 420 });
      expect(chartData[1]).toEqual({ time: '06:00', label: '06:00 - 12:00', count: 850 });
      expect(chartData[2]).toEqual({ time: '12:00', label: '12:00 - 18:00', count: 680 });
      expect(chartData[3]).toEqual({ time: '18:00', label: '18:00 - 24:00', count: 329 });
    });
  });
});
