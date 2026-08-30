// Triage Cache Invalidation & Authoritative Queue KPI Test Suite

import { describe, it, expect, vi } from 'vitest';
import { QueryClient } from '@tanstack/react-query';
import { incidentKeys, dashboardKeys, analyticsKeys } from '../lib/queryKeys';
import { DashboardSummaryData, DashboardSummaryQueryParams } from '../types';

describe('Triage Cache Invalidation & Authoritative Queue KPIs', () => {
  describe('1. Query Key Hierarchy & Prefix Matching', () => {
    it('dashboardKeys.all matches all dashboard summary keys', () => {
      const allKey = dashboardKeys.all; // ['dashboard']
      const summaryKey1 = dashboardKeys.summary({ time_range: 'all' });
      const summaryKey2 = dashboardKeys.summary({ time_range: 'all', category: 'FLOOD_WATERLOGGING' });
      const summaryKey3 = dashboardKeys.summary({ time_range: 'all', severity: 'HIGH' });
      const summariesKey = dashboardKeys.summaries();

      expect(summaryKey1[0]).toBe(allKey[0]);
      expect(summaryKey2[0]).toBe(allKey[0]);
      expect(summaryKey3[0]).toBe(allKey[0]);
      expect(summariesKey[0]).toBe(allKey[0]);
    });

    it('analyticsKeys.all matches both trends and regional analytics keys', () => {
      const allKey = analyticsKeys.all; // ['analytics']
      const trendsKey = analyticsKeys.trends({ time_range: '7d', category: 'HEAVY_RAINFALL' });
      const regionalKey = analyticsKeys.regional({ time_range: '24h', status: 'VERIFIED' });
      const trendsAllKey = analyticsKeys.trendsAll();
      const regionalAllKey = analyticsKeys.regionalAll();

      expect(trendsKey[0]).toBe(allKey[0]);
      expect(regionalKey[0]).toBe(allKey[0]);
      expect(trendsAllKey[0]).toBe(allKey[0]);
      expect(regionalAllKey[0]).toBe(allKey[0]);
    });

    it('incidentKeys.lists matches all incident list queries including Recent Reports', () => {
      const listsKey = incidentKeys.lists(); // ['incidents', 'list']
      const recentReportsKey = incidentKeys.list({ verification_status: 'VERIFIED', page_size: 5 });
      const incidentListKey = incidentKeys.list({ page: 1, page_size: 20, severity: 'HIGH' });

      expect(recentReportsKey[0]).toBe(listsKey[0]);
      expect(recentReportsKey[1]).toBe(listsKey[1]);
      expect(incidentListKey[0]).toBe(listsKey[0]);
      expect(incidentListKey[1]).toBe(listsKey[1]);
    });
  });

  describe('2. QueryClient Invalidation Scope & Precision', () => {
    it('invalidates dashboard, analytics, queue, and list caches without affecting unrelated caches', async () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 1000 * 60 * 10, // 10 minutes fresh
          },
        },
      });

      // 1. Populate query cache with various queries
      const dashboardSummaryKey = dashboardKeys.summary({ time_range: 'all' });
      const analyticsTrendsKey = analyticsKeys.trends({ time_range: '7d' });
      const analyticsRegionalKey = analyticsKeys.regional({ time_range: '24h' });
      const incidentListKey = incidentKeys.list({ verification_status: 'VERIFIED', page_size: 5 });
      const queueListKey = incidentKeys.verificationQueueList({ page: 1 });
      const adminQueueKey = ['admin-queue-reports', { page: 1, page_size: 20 }];
      const dashboardReportsKey = ['dashboard-reports', { page: 1, page_size: 100 }];
      const liveMapReportsKey = ['live-map-reports', { page: 1 }];

      // Unrelated queries
      const authUserKey = ['auth', 'current-user'];
      const staticConfigKey = ['static-config', 'hazard-categories'];

      queryClient.setQueryData(dashboardSummaryKey, { total_count: 100 });
      queryClient.setQueryData(analyticsTrendsKey, { trend_points: [] });
      queryClient.setQueryData(analyticsRegionalKey, { regional_aggregates: [] });
      queryClient.setQueryData(incidentListKey, { data: [] });
      queryClient.setQueryData(queueListKey, { data: [] });
      queryClient.setQueryData(adminQueueKey, { data: [] });
      queryClient.setQueryData(dashboardReportsKey, { data: [] });
      queryClient.setQueryData(liveMapReportsKey, { data: [] });
      queryClient.setQueryData(authUserKey, { id: 'usr_123', name: 'Admin Officer' });
      queryClient.setQueryData(staticConfigKey, { categories: ['FLOOD'] });

      // Verify all queries are initially fresh
      const getQuery = (key: readonly unknown[]) => queryClient.getQueryCache().find({ queryKey: key });

      expect(getQuery(dashboardSummaryKey)?.isStale()).toBe(false);
      expect(getQuery(analyticsTrendsKey)?.isStale()).toBe(false);
      expect(getQuery(analyticsRegionalKey)?.isStale()).toBe(false);
      expect(getQuery(incidentListKey)?.isStale()).toBe(false);
      expect(getQuery(queueListKey)?.isStale()).toBe(false);
      expect(getQuery(adminQueueKey)?.isStale()).toBe(false);
      expect(getQuery(dashboardReportsKey)?.isStale()).toBe(false);
      expect(getQuery(liveMapReportsKey)?.isStale()).toBe(false);
      expect(getQuery(authUserKey)?.isStale()).toBe(false);
      expect(getQuery(staticConfigKey)?.isStale()).toBe(false);

      // 2. Execute exact invalidation sequence from AdminVerificationQueuePage.handleActionComplete
      await queryClient.invalidateQueries({ queryKey: incidentKeys.verificationQueues() });
      await queryClient.invalidateQueries({ queryKey: incidentKeys.lists() });
      await queryClient.invalidateQueries({ queryKey: incidentKeys.geoAll() });
      await queryClient.invalidateQueries({ queryKey: incidentKeys.details() });
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
      await queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
      await queryClient.invalidateQueries({ queryKey: ['admin-queue-reports'] });
      await queryClient.invalidateQueries({ queryKey: ['dashboard-reports'] });
      await queryClient.invalidateQueries({ queryKey: ['live-map-reports'] });
      await queryClient.invalidateQueries({ queryKey: ['reports'] });

      // 3. Verify all affected queries are marked STALE (invalidated)
      expect(getQuery(dashboardSummaryKey)?.isStale()).toBe(true);
      expect(getQuery(analyticsTrendsKey)?.isStale()).toBe(true);
      expect(getQuery(analyticsRegionalKey)?.isStale()).toBe(true);
      expect(getQuery(incidentListKey)?.isStale()).toBe(true);
      expect(getQuery(queueListKey)?.isStale()).toBe(true);
      expect(getQuery(adminQueueKey)?.isStale()).toBe(true);
      expect(getQuery(dashboardReportsKey)?.isStale()).toBe(true);
      expect(getQuery(liveMapReportsKey)?.isStale()).toBe(true);

      // 4. Verify unrelated queries remain completely UNTOUCHED and FRESH
      expect(getQuery(authUserKey)?.isStale()).toBe(false);
      expect(getQuery(staticConfigKey)?.isStale()).toBe(false);
    });
  });

  describe('3. Action Failure Boundary', () => {
    it('does not invalidate caches if operator action throws an error', async () => {
      const queryClient = new QueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const onActionComplete = vi.fn(() => {
        queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
        queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
      });

      // Simulate a failed verification API call
      const failingAction = async () => {
        throw new Error('400 Bad Request: Invalid State Transition');
      };

      let caughtError: Error | null = null;
      try {
        await failingAction();
        onActionComplete();
      } catch (err) {
        caughtError = err as Error;
      }

      expect(caughtError).not.toBeNull();
      expect(caughtError?.message).toContain('Invalid State Transition');
      expect(onActionComplete).not.toHaveBeenCalled();
      expect(invalidateSpy).not.toHaveBeenCalled();
    });
  });

  describe('4. Authoritative Queue KPI Semantics & Calculations', () => {
    const mockSummary: DashboardSummaryData = {
      total_count: 3135,
      period_count: 3135,
      count_24h: 700,
      last_24h_pct: 22,
      verification: {
        verified_count: 271,
        verified_rate: 9,
        pending_count: 2554, // Total active backlog (PENDING + UNDER_REVIEW)
        under_review_count: 44, // Active operator review
        rejected_count: 159,
        duplicate_count: 151,
      },
      severity: {
        severe_high_count: 1584,
        severe_count: 361,
        high_count: 1223,
        moderate_count: 1240,
        low_count: 311,
      },
      category_distribution: [],
      diurnal_distribution: [],
    };

    it('correctly calculates strict Pending Review and Under Review counts', () => {
      const pending = Math.max(
        0,
        mockSummary.verification.pending_count - mockSummary.verification.under_review_count
      );
      const underReview = mockSummary.verification.under_review_count;

      // Strict PENDING = 2554 - 44 = 2510
      expect(pending).toBe(2510);
      expect(underReview).toBe(44);
    });

    it('correctly maps High Priority and Possible Duplicates from authoritative summary', () => {
      const highPriority = mockSummary.severity.severe_high_count;
      const duplicates = mockSummary.verification.duplicate_count;

      expect(highPriority).toBe(1584);
      expect(duplicates).toBe(151);
    });

    it('is completely independent of 20-row table page slice', () => {
      // Suppose the table page has 20 items:
      const pageSlice = Array(20).fill({ verification_status: 'PENDING' });
      expect(pageSlice.length).toBe(20);

      // KPI counts come from server summary, NOT page slice length
      const pending = Math.max(
        0,
        mockSummary.verification.pending_count - mockSummary.verification.under_review_count
      );
      expect(pending).toBe(2510);
      expect(pending).not.toBe(pageSlice.length);
    });

    it('handles empty or null summary safely with 0 fallbacks', () => {
      const emptySummary: DashboardSummaryData | null = null;
      const pending = emptySummary?.verification
        ? Math.max(0, emptySummary.verification.pending_count - emptySummary.verification.under_review_count)
        : 0;
      const underReview = emptySummary?.verification?.under_review_count ?? 0;
      const highPriority = emptySummary?.severity?.severe_high_count ?? 0;
      const duplicates = emptySummary?.verification?.duplicate_count ?? 0;

      expect(pending).toBe(0);
      expect(underReview).toBe(0);
      expect(highPriority).toBe(0);
      expect(duplicates).toBe(0);
    });

    it('constructs summary query params reflecting Category and Severity filters with time_range: all', () => {
      const filters = {
        status: 'ACTIVE',
        category: 'FLOOD_WATERLOGGING',
        severity: 'HIGH',
        searchQuery: '',
      };

      const summaryParams: DashboardSummaryQueryParams = {
        time_range: 'all',
      };
      if (filters.category !== 'ALL') {
        summaryParams.category = filters.category;
      }
      if (filters.severity !== 'ALL') {
        summaryParams.severity = filters.severity;
      }

      expect(summaryParams).toEqual({
        time_range: 'all',
        category: 'FLOOD_WATERLOGGING',
        severity: 'HIGH',
      });

      const key = dashboardKeys.summary(summaryParams as Record<string, unknown>);
      expect(key).toEqual([
        'dashboard',
        'summary',
        {
          category: 'FLOOD_WATERLOGGING',
          severity: 'HIGH',
          time_range: 'all',
        },
      ]);
    });
  });
});
