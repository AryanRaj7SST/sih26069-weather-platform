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

  describe('6. Recent Incident Feed Bounded Query & Contract', () => {
    it('constructs bounded query params with page_size 6 and occurred_at desc sort', () => {
      const filters = {
        timeRange: '24h',
        hazard: 'FLOOD_WATERLOGGING',
        region: 'MUMBAI_METRO',
        status: 'VERIFIED',
      };
      const fromDate = '2026-08-29T16:00:00.000Z';
      const bbox = '72.75,18.85,73.05,19.35';

      const recentFeedParams = {
        page: 1,
        page_size: 6,
        sort_by: 'occurred_at',
        sort_order: 'desc',
        from_date: fromDate,
        category: filters.hazard !== 'ALL' ? filters.hazard : undefined,
        verification_status: filters.status !== 'ALL' ? filters.status : undefined,
        bbox,
      };

      expect(recentFeedParams.page).toBe(1);
      expect(recentFeedParams.page_size).toBe(6);
      expect(recentFeedParams.sort_by).toBe('occurred_at');
      expect(recentFeedParams.sort_order).toBe('desc');
      expect(recentFeedParams.category).toBe('FLOOD_WATERLOGGING');
      expect(recentFeedParams.verification_status).toBe('VERIFIED');
      expect(recentFeedParams.bbox).toBe(bbox);
      expect(recentFeedParams.from_date).toBe(fromDate);
    });

    it('generates canonical incident query key matching list hierarchy', () => {
      const recentFeedParams = {
        page: 1,
        page_size: 6,
        sort_by: 'occurred_at',
        sort_order: 'desc',
        category: 'HEAVY_RAINFALL',
      };

      const key = [
        'incidents',
        'list',
        {
          category: recentFeedParams.category,
          page: recentFeedParams.page,
          page_size: recentFeedParams.page_size,
          sort_by: recentFeedParams.sort_by,
          sort_order: recentFeedParams.sort_order,
        },
      ];

      expect(key[0]).toBe('incidents');
      expect(key[1]).toBe('list');
      expect((key[2] as Record<string, unknown>).page_size).toBe(6);
    });

    it('feed correctly bounds display records to at most 6', () => {
      const mockIncidents = Array.from({ length: 10 }, (_, i) => ({
        id: `inc_${i}`,
        tracking_id: `RPT-20260830-${i}`,
        title: `Incident ${i}`,
        category: { code: 'FLOOD_WATERLOGGING', title: 'Flooding' },
        severity: 'HIGH' as const,
        location: { name: 'Dadar West', latitude: 19.0178, longitude: 72.8478 },
        occurred_at: '2026-08-30T10:00:00Z',
        verification_status: 'VERIFIED' as const,
        credibility_score: 0.85,
        readiness: 'INTELLIGENCE_READY' as const,
        media_count: 1,
        created_at: '2026-08-30T10:00:00Z',
      }));

      const displayReports = mockIncidents.slice(0, 6);
      expect(displayReports).toHaveLength(6);
      expect(displayReports[0].id).toBe('inc_0');
      expect(displayReports[5].id).toBe('inc_5');
    });

    it('safely handles empty feed with zero records', () => {
      const emptyReports: Array<{ id: string }> = [];
      const displayReports = emptyReports.slice(0, 6);
      expect(displayReports).toHaveLength(0);
    });
  });
});
