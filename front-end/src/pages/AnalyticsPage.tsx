import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { MobileBottomNav } from '@/components/layout/MobileBottomNav';
import {
  AnalyticsFilters,
  AnalyticsFilterState,
  AnalyticsKpiCards,
  ReportActivityChart,
  EventDistributionCard,
  SeverityDistributionCard,
  RecentReportsTable,
  VerificationStatusCard,
  RegionalActivityCard,
  ObservedPatternsCard,
  GEOGRAPHY_OPTIONS,
} from '@/features/analytics';
import { dashboardApi } from '@/services/dashboardApi';
import { analyticsApi } from '@/services/analyticsApi';
import { fetchAllDashboardReports } from '@/services/reportApi';
import { dashboardKeys, analyticsKeys } from '@/lib/queryKeys';
import {
  AnalyticsTrendQueryParams,
  DashboardSummaryQueryParams,
  ReportListQueryParams,
} from '@/types';
import { BarChart3, Filter, AlertCircle } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const [filters, setFilters] = useState<AnalyticsFilterState>({
    timeRange: '7d',
    category: 'ALL',
    severity: 'ALL',
    status: 'ALL',
    region: 'ALL',
  });

  const [tempFilters, setTempFilters] = useState<AnalyticsFilterState>(filters);
  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);

  // Compute server-aggregated summary parameters
  const summaryParams = useMemo<DashboardSummaryQueryParams>(() => {
    const params: DashboardSummaryQueryParams = {};

    if (filters.timeRange) {
      params.time_range = filters.timeRange;
    }
    if (filters.category !== 'ALL') {
      params.category = filters.category;
    }
    if (filters.severity !== 'ALL') {
      params.severity = filters.severity;
    }
    if (filters.status !== 'ALL') {
      params.status = filters.status;
    }
    if (filters.region !== 'ALL' && GEOGRAPHY_OPTIONS[filters.region]?.bbox) {
      params.bbox = GEOGRAPHY_OPTIONS[filters.region].bbox;
    }

    return params;
  }, [filters]);

  // Fetch server-side summary statistics via dashboardApi
  const {
    data: summaryResponse,
    isLoading: isSummaryLoading,
    isError: isSummaryError,
    error: summaryError,
  } = useQuery({
    queryKey: dashboardKeys.summary(summaryParams as Record<string, unknown>),
    queryFn: ({ signal }) => dashboardApi.getSummary(summaryParams, signal),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });

  const summaryData = summaryResponse?.data;

  // Compute server-aggregated trend parameters
  const trendParams = useMemo<AnalyticsTrendQueryParams>(() => {
    const params: AnalyticsTrendQueryParams = {};

    if (filters.timeRange) {
      params.time_range = filters.timeRange;
    }
    if (filters.category !== 'ALL') {
      params.category = filters.category;
    }
    if (filters.severity !== 'ALL') {
      params.severity = filters.severity;
    }
    if (filters.status !== 'ALL') {
      params.status = filters.status;
    }
    if (filters.region !== 'ALL' && GEOGRAPHY_OPTIONS[filters.region]?.bbox) {
      params.bbox = GEOGRAPHY_OPTIONS[filters.region].bbox;
    }

    return params;
  }, [filters]);

  // Fetch server-side activity trends via analyticsApi
  const {
    data: trendResponse,
    isLoading: isTrendLoading,
    isError: isTrendError,
    error: trendError,
  } = useQuery({
    queryKey: analyticsKeys.trends(trendParams as Record<string, unknown>),
    queryFn: ({ signal }) => analyticsApi.getTrends(trendParams, signal),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });

  const trendData = trendResponse?.data;

  // Compute API query params for raw report consumers (RecentReportsTable, RegionalActivityCard)
  const queryParams = useMemo<ReportListQueryParams>(() => {
    const params: ReportListQueryParams = {};

    // Date range filter
    const now = new Date();
    if (filters.timeRange === '24h') {
      params.from_date = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
    } else if (filters.timeRange === '7d') {
      params.from_date = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
    } else if (filters.timeRange === '30d') {
      params.from_date = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();
    }

    // Category filter
    if (filters.category !== 'ALL') {
      params.category = filters.category;
    }

    // Severity filter
    if (filters.severity !== 'ALL') {
      params.severity = filters.severity;
    }

    // Status filter
    if (filters.status !== 'ALL') {
      params.status = filters.status;
    }

    // Geography / bbox filter
    if (filters.region !== 'ALL' && GEOGRAPHY_OPTIONS[filters.region]?.bbox) {
      params.bbox = GEOGRAPHY_OPTIONS[filters.region].bbox;
    }

    return params;
  }, [filters]);

  // Fetch raw reports for non-aggregated components
  const {
    data: response,
    isLoading: isRawLoading,
    isError: isRawError,
    error: rawError,
    isFetching,
  } = useQuery({
    queryKey: ['analytics-reports', queryParams],
    queryFn: () => fetchAllDashboardReports(queryParams),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });

  const reports = response?.data || [];
  const pagination = response?.pagination;

  const handleApplyFilters = () => {
    setFilters(tempFilters);
    setMobileFilterOpen(false);
  };

  const handleResetFilters = () => {
    const defaultState: AnalyticsFilterState = {
      timeRange: '7d',
      category: 'ALL',
      severity: 'ALL',
      status: 'ALL',
      region: 'ALL',
    };
    setTempFilters(defaultState);
    setFilters(defaultState);
    setMobileFilterOpen(false);
  };

  const isAnyError = isRawError || isTrendError || isSummaryError;
  const activeError = summaryError || trendError || rawError;

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <Navbar />

      <main className="flex-1 pb-16 pt-6">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-6">
          {/* Header Banner */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
                  <BarChart3 className="h-4 w-4" />
                </div>
                <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
                  Weather Analytics
                </h1>
              </div>
              <p className="mt-1 text-sm text-slate-600">
                Explore report activity, event distribution, severity patterns, and verification trends across the selected period.
              </p>
            </div>

            {/* Mobile Filters Toggle Button */}
            <div className="block md:hidden">
              <button
                type="button"
                onClick={() => setMobileFilterOpen(!mobileFilterOpen)}
                className="flex items-center space-x-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 shadow-2xs hover:bg-slate-50 cursor-pointer"
              >
                <Filter className="h-3.5 w-3.5 text-blue-600" />
                <span>Filters</span>
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {isAnyError && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-rose-600 flex-shrink-0" />
              <span>
                Failed to load analytics data: {activeError instanceof Error ? activeError.message : 'Unknown error'}
              </span>
            </div>
          )}

          {/* Filters Bar (Always visible on desktop, toggleable on mobile) */}
          <div className={`${mobileFilterOpen ? 'block' : 'hidden md:block'}`}>
            <AnalyticsFilters
              filters={filters}
              tempFilters={tempFilters}
              onTempChange={setTempFilters}
              onApply={handleApplyFilters}
              onReset={handleResetFilters}
              isFetching={isFetching}
            />
          </div>

          {/* 1. KPI Cards (Migrated to dashboardApi.getSummary) */}
          <AnalyticsKpiCards
            summary={summaryData}
            reports={reports}
            pagination={pagination}
            timeRange={filters.timeRange}
            isLoading={isSummaryLoading}
          />

          {/* 2. Main Activity Chart (Migrated to analyticsApi.getTrends) */}
          <ReportActivityChart
            trendData={trendData}
            reports={reports}
            timeRange={filters.timeRange}
            isLoading={isTrendLoading}
          />

          {/* 3. 2-Column Grid: Event & Severity Distribution (Migrated to dashboardApi.getSummary) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <EventDistributionCard
              distribution={summaryData?.category_distribution}
              reports={reports}
              isLoading={isSummaryLoading}
            />
            <SeverityDistributionCard
              severity={summaryData?.severity}
              reports={reports}
              isLoading={isSummaryLoading}
            />
          </div>

          {/* 4. Recent Reports Table (Raw data consumer) */}
          <RecentReportsTable
            reports={reports}
            isLoading={isRawLoading}
          />

          {/* 5. 2-Column Grid: Verification Status & Regional Activity */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <VerificationStatusCard
              verification={summaryData?.verification}
              reports={reports}
              isLoading={isSummaryLoading}
            />
            <RegionalActivityCard
              reports={reports}
              isLoading={isRawLoading}
            />
          </div>

          {/* 6. Observed Patterns Banner (Migrated to dashboardApi.getSummary) */}
          <ObservedPatternsCard
            summary={summaryData}
            reports={reports}
            isLoading={isSummaryLoading}
          />
        </div>
      </main>

      <Footer />
      <MobileBottomNav />
    </div>
  );
};
