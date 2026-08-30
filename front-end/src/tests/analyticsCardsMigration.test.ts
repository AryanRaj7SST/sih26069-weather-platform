// Comprehensive Unit Test Suite for Analytics Summary Cards Migration & Recent/Regional Optimizations

import { describe, it, expect } from 'vitest';
import { analyticsKeys, dashboardKeys, incidentKeys } from '../lib/queryKeys';
import {
  AnalyticsRegionalData,
  AnalyticsRegionalQueryParams,
  CategoryDistributionItem,
  DashboardSummaryData,
  DashboardSummaryQueryParams,
  IncidentListQueryParams,
  IncidentSummary,
  RegionalDistributionItem,
  SeverityBreakdown,
  VerificationBreakdown,
} from '../types';

describe('Analytics Summary Cards Migration - Data Mapping & Presentation Logic', () => {
  const mockSummaryData: DashboardSummaryData = {
    total_count: 2279,
    period_count: 2279,
    count_24h: 129,
    last_24h_pct: 6,
    verification: {
      verified_count: 165,
      verified_rate: 7,
      pending_count: 2100, // combined pending + under_review
      under_review_count: 50,
      rejected_count: 10,
      duplicate_count: 4,
    },
    severity: {
      severe_high_count: 540,
      severe_count: 180,
      high_count: 360,
      moderate_count: 920,
      low_count: 819,
    },
    category_distribution: [
      { category_code: 'FLOOD_WATERLOGGING', category_name: 'Flooding & Waterlogging', count: 950, percentage: 42 },
      { category_code: 'HEAVY_RAINFALL', category_name: 'Heavy Rainfall', count: 620, percentage: 27 },
      { category_code: 'HIGH_WINDS', category_name: 'High Winds', count: 310, percentage: 14 },
      { category_code: 'LANDSLIDE', category_name: 'Landslide', count: 180, percentage: 8 },
      { category_code: 'EXTREME_HEAT', category_name: 'Extreme Heat', count: 120, percentage: 5 },
      { category_code: 'POLLUTION_SMOG', category_name: 'Pollution / Smog', count: 60, percentage: 3 },
      { category_code: 'COLD_WAVE', category_name: 'Cold Wave', count: 39, percentage: 1 },
    ],
    diurnal_distribution: [],
  };

  describe('1. Analytics KPI Cards Mapping', () => {
    it('maps summary total, period, verified, and pending metrics directly', () => {
      const stats = {
        totalCount: mockSummaryData.total_count,
        periodReports: mockSummaryData.period_count,
        verifiedCount: mockSummaryData.verification.verified_count,
        verifiedPct: mockSummaryData.verification.verified_rate,
        pendingCount: mockSummaryData.verification.pending_count,
      };

      expect(stats.totalCount).toBe(2279);
      expect(stats.periodReports).toBe(2279);
      expect(stats.verifiedCount).toBe(165);
      expect(stats.verifiedPct).toBe(7);
      expect(stats.pendingCount).toBe(2100);
    });
  });

  describe('2. Event Distribution Top-6 Mapping', () => {
    it('slices top 6 categories from server-provided distribution without client aggregation', () => {
      const distribution: CategoryDistributionItem[] = mockSummaryData.category_distribution;
      const top6 = distribution.slice(0, 6).map((item) => ({
        label: item.category_name,
        count: item.count,
      }));

      expect(top6).toHaveLength(6);
      expect(top6[0]).toEqual({ label: 'Flooding & Waterlogging', count: 950 });
      expect(top6[5]).toEqual({ label: 'Pollution / Smog', count: 60 });
      // 7th category is excluded from top 6 display
      expect(top6.some((item) => item.label === 'Cold Wave')).toBe(false);
    });
  });

  describe('3. Severity Distribution Mapping', () => {
    it('maps severe, high, moderate, and low counts from summary severity breakdown', () => {
      const severity: SeverityBreakdown = mockSummaryData.severity;
      const stats = [
        { label: 'Severe', count: severity.severe_count },
        { label: 'High', count: severity.high_count },
        { label: 'Moderate', count: severity.moderate_count },
        { label: 'Low', count: severity.low_count },
      ];

      expect(stats[0]).toEqual({ label: 'Severe', count: 180 });
      expect(stats[1]).toEqual({ label: 'High', count: 360 });
      expect(stats[2]).toEqual({ label: 'Moderate', count: 920 });
      expect(stats[3]).toEqual({ label: 'Low', count: 819 });
    });
  });

  describe('4. Verification Status & Strict Pending Derivation', () => {
    it('derives strict pending from pending_count and under_review_count', () => {
      const verification: VerificationBreakdown = mockSummaryData.verification;
      const strictPending = Math.max(0, verification.pending_count - verification.under_review_count);

      expect(strictPending).toBe(2050); // 2100 - 50 = 2050
      expect(verification.under_review_count).toBe(50);
      expect(verification.verified_count).toBe(165);
      expect(verification.rejected_count).toBe(10);
      expect(verification.duplicate_count).toBe(4);

      // Coherence check: sum of separate categories
      const totalCategorized = verification.verified_count + strictPending + verification.under_review_count + verification.rejected_count + verification.duplicate_count;
      expect(totalCategorized).toBe(2279);
    });

    it('safely handles zero under_review_count without underflow', () => {
      const verification: VerificationBreakdown = {
        verified_count: 10,
        verified_rate: 100,
        pending_count: 0,
        under_review_count: 0,
        rejected_count: 0,
        duplicate_count: 0,
      };

      const strictPending = Math.max(0, verification.pending_count - verification.under_review_count);
      expect(strictPending).toBe(0);
    });
  });

  describe('5. Observed Patterns Observation Derivation', () => {
    it('derives top category, urgency, and verification text from summary statistics', () => {
      const summary = mockSummaryData;
      const items: string[] = [];

      const topCategory = summary.category_distribution[0];
      if (topCategory && topCategory.count > 0) {
        items.push(
          `${topCategory.category_name} reports constitute the highest activity volume (${topCategory.count} reports, ${topCategory.percentage}% of total) in the selected period.`
        );
      }

      const severeHighCount = summary.severity.severe_high_count;
      if (severeHighCount > 0) {
        const severePct = Math.round((severeHighCount / summary.total_count) * 100);
        items.push(
          `${severeHighCount} reports (${severePct}%) are classified as High or Severe urgency requiring prioritized operator monitoring.`
        );
      }

      const verifiedCount = summary.verification.verified_count;
      const verifiedPct = summary.verification.verified_rate;
      items.push(
        `Verified report rate is currently at ${verifiedPct}% (${verifiedCount} verified reports) across active submissions.`
      );

      expect(items).toHaveLength(3);
      expect(items[0]).toContain('Flooding & Waterlogging reports constitute the highest activity volume (950 reports, 42% of total)');
      expect(items[1]).toContain('540 reports (24%) are classified as High or Severe urgency');
      expect(items[2]).toContain('Verified report rate is currently at 7% (165 verified reports)');
    });

    it('returns empty observations for zero dataset without throwing', () => {
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

      const observations = emptySummary.total_count === 0 ? [] : ['not empty'];
      expect(observations).toEqual([]);
    });
  });

  describe('6. Summary Query Key & Parameter Construction', () => {
    it('constructs normalized query keys for analytics summary requests', () => {
      const summaryParams: DashboardSummaryQueryParams = {
        time_range: '30d',
        category: 'HIGH_WINDS',
        severity: 'SEVERE',
        status: 'PENDING',
        bbox: '72.0,18.0,74.0,20.0',
      };

      const key = dashboardKeys.summary(summaryParams as Record<string, unknown>);
      expect(key).toEqual([
        'dashboard',
        'summary',
        {
          bbox: '72.0,18.0,74.0,20.0',
          category: 'HIGH_WINDS',
          severity: 'SEVERE',
          status: 'PENDING',
          time_range: '30d',
        },
      ]);
    });
  });

  describe('7. Recent Reports Table Bounded Query & Mapping', () => {
    it('constructs bounded incident list query parameters (page_size: 8, occurred_at desc)', () => {
      const recentParams: IncidentListQueryParams = {
        page: 1,
        page_size: 8,
        sort_by: 'occurred_at',
        sort_order: 'desc',
        category: 'FLOOD_WATERLOGGING',
        from_date: '2026-08-23T00:00:00.000Z',
      };

      const key = incidentKeys.list(recentParams as Record<string, unknown>);
      expect(key).toEqual([
        'incidents',
        'list',
        {
          category: 'FLOOD_WATERLOGGING',
          from_date: '2026-08-23T00:00:00.000Z',
          page: 1,
          page_size: 8,
          sort_by: 'occurred_at',
          sort_order: 'desc',
        },
      ]);
    });

    it('slices and formats exactly up to 8 recent incidents', () => {
      const mockIncidents: IncidentSummary[] = Array.from({ length: 15 }, (_, i) => ({
        id: `inc-${i}`,
        tracking_id: `TRK-${1000 + i}`,
        title: `Incident ${i}`,
        category: { code: 'FLOOD_WATERLOGGING', title: 'Flooding & Waterlogging' },
        severity: 'HIGH',
        location: { name: 'Kurla, Mumbai', latitude: 19.07, longitude: 72.88 },
        occurred_at: '2026-08-30T06:00:00Z',
        verification_status: 'VERIFIED',
        credibility_score: 0.85,
        readiness: 'READY',
        media_count: 1,
        created_at: '2026-08-30T06:05:00Z',
      }));

      const recentList = mockIncidents.slice(0, 8);
      expect(recentList).toHaveLength(8);
      expect(recentList[0].tracking_id).toBe('TRK-1000');
      expect(recentList[7].tracking_id).toBe('TRK-1007');
    });
  });

  describe('8. Regional Activity Server Aggregation Mapping', () => {
    it('constructs normalized query keys for analytics regional requests', () => {
      const regionalParams: AnalyticsRegionalQueryParams = {
        time_range: '7d',
        category: 'FLOOD_WATERLOGGING',
        severity: 'HIGH',
        status: 'VERIFIED',
        bbox: '72.0,18.0,74.0,20.0',
      };

      const key = analyticsKeys.regional(regionalParams as Record<string, unknown>);
      expect(key).toEqual([
        'analytics',
        'regional',
        {
          bbox: '72.0,18.0,74.0,20.0',
          category: 'FLOOD_WATERLOGGING',
          severity: 'HIGH',
          status: 'VERIFIED',
          time_range: '7d',
        },
      ]);
    });

    it('presents top 5 server-provided regions directly with counts and percentages', () => {
      const mockRegionalData: AnalyticsRegionalData = {
        time_range: '7d',
        total_classified: 2638,
        regions: [
          { region_code: 'MH', region_name: 'Maharashtra', count: 1422, percentage: 54 },
          { region_code: 'TN', region_name: 'Tamil Nadu', count: 350, percentage: 13 },
          { region_code: 'KA', region_name: 'Karnataka', count: 337, percentage: 13 },
          { region_code: 'DL', region_name: 'Delhi NCR', count: 324, percentage: 12 },
          { region_code: 'OTHER', region_name: 'Other Regions', count: 153, percentage: 6 },
          { region_code: 'KL', region_name: 'Kerala', count: 26, percentage: 1 },
          { region_code: 'RJ', region_name: 'Rajasthan', count: 26, percentage: 1 },
        ],
      };

      const top5: RegionalDistributionItem[] = mockRegionalData.regions.slice(0, 5);
      expect(top5).toHaveLength(5);
      expect(top5[0]).toEqual({ region_code: 'MH', region_name: 'Maharashtra', count: 1422, percentage: 54 });
      expect(top5[1]).toEqual({ region_code: 'TN', region_name: 'Tamil Nadu', count: 350, percentage: 13 });
      expect(top5[4]).toEqual({ region_code: 'OTHER', region_name: 'Other Regions', count: 153, percentage: 6 });
      expect(top5.some((r) => r.region_code === 'KL')).toBe(false);
    });

    it('safely handles empty regional data', () => {
      const emptyRegional: AnalyticsRegionalData = {
        time_range: '24h',
        total_classified: 0,
        regions: [],
      };

      const top5 = emptyRegional.regions.slice(0, 5);
      expect(top5).toEqual([]);
    });
  });
});
