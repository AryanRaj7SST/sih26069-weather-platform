import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { MobileBottomNav } from '@/components/layout/MobileBottomNav';
import {
  DashboardFilters,
  DashboardFilterState,
} from '@/features/dashboard/DashboardFilters';
import { REGIONS } from '@/features/dashboard/constants';
import { DashboardKpiCards } from '@/features/dashboard/DashboardKpiCards';
import { DashboardMap } from '@/features/dashboard/DashboardMap';
import { RecentIncidentFeed } from '@/features/dashboard/RecentIncidentFeed';
import { IncidentTrendCard } from '@/features/dashboard/IncidentTrendCard';
import { EventDistributionCard } from '@/features/dashboard/EventDistributionCard';
import { VerificationSummaryCard } from '@/features/dashboard/VerificationSummaryCard';
import { dashboardApi } from '@/services/dashboardApi';
import { fetchAllDashboardReports } from '@/services/reportApi';
import { dashboardKeys } from '@/lib/queryKeys';
import {
  DashboardSummaryQueryParams,
  ReportDetailData,
  ReportListQueryParams,
} from '@/types';
import { AlertTriangle } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [filters, setFilters] = useState<DashboardFilterState>({
    timeRange: '24h',
    hazard: 'ALL',
    region: 'ALL',
    status: 'ALL',
  });

  const [selectedReport, setSelectedReport] = useState<ReportDetailData | null>(null);

  // Summary aggregation query parameters
  const summaryParams: DashboardSummaryQueryParams = useMemo(() => {
    const params: DashboardSummaryQueryParams = {};
    if (filters.timeRange) {
      params.time_range = filters.timeRange;
    }
    if (filters.hazard !== 'ALL') {
      params.category = filters.hazard;
    }
    if (filters.status !== 'ALL') {
      params.status = filters.status;
    }
    const regionInfo = REGIONS[filters.region];
    if (regionInfo?.bbox) {
      params.bbox = regionInfo.bbox;
    }
    return params;
  }, [filters]);

  // Fetch SQL-aggregated summary data from backend
  const {
    data: summaryResponse,
    isLoading: isSummaryLoading,
    isFetching: isSummaryFetching,
    isError: isSummaryError,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: dashboardKeys.summary(summaryParams as Record<string, unknown>),
    queryFn: ({ signal }) => dashboardApi.getSummary(summaryParams, signal),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });

  const summaryData = summaryResponse?.data;

  // Compute from_date based on timeRange filter for raw incident list (map & feed)
  const fromDate = useMemo(() => {
    const now = Date.now();
    if (filters.timeRange === '24h') {
      return new Date(now - 24 * 60 * 60 * 1000).toISOString();
    }
    if (filters.timeRange === '48h') {
      return new Date(now - 48 * 60 * 60 * 1000).toISOString();
    }
    if (filters.timeRange === '7d') {
      return new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString();
    }
    return undefined;
  }, [filters.timeRange]);

  // Query parameters for raw reports (used by Map pins & Recent Incident Feed)
  const rawQueryParams: ReportListQueryParams = useMemo(() => {
    const params: ReportListQueryParams = {
      page: 1,
      page_size: 100,
    };

    if (fromDate) {
      params.from_date = fromDate;
    }
    if (filters.hazard !== 'ALL') {
      params.category = filters.hazard;
    }
    if (filters.status !== 'ALL') {
      params.status = filters.status;
    }
    const regionInfo = REGIONS[filters.region];
    if (regionInfo?.bbox) {
      params.bbox = regionInfo.bbox;
    }

    return params;
  }, [filters, fromDate]);

  // Fetch raw dataset for map markers and recent feed
  const {
    data: rawResponse,
    isLoading: isRawLoading,
    isFetching: isRawFetching,
    isError: isRawError,
    error: rawError,
    refetch: refetchRaw,
  } = useQuery({
    queryKey: ['dashboard-reports', rawQueryParams],
    queryFn: () => fetchAllDashboardReports(rawQueryParams),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });

  const reports = useMemo(() => rawResponse?.data || [], [rawResponse]);

  const targetRegion = useMemo(() => {
    const reg = REGIONS[filters.region];
    return reg ? { center: reg.center, zoom: reg.zoom } : undefined;
  }, [filters.region]);

  const handleRefresh = () => {
    refetchSummary();
    refetchRaw();
  };

  const isFetching = isSummaryFetching || isRawFetching;
  const isError = isSummaryError || isRawError;
  const activeError = summaryError || rawError;

  return (
    <div className="flex min-h-screen flex-col bg-slate-50/60 text-slate-900 pb-16 md:pb-0">
      {/* Top Navbar */}
      <Navbar />

      {/* Main Dashboard Workspace */}
      <main className="flex-1">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 space-y-6">
          {/* Top Filter Bar */}
          <DashboardFilters
            filters={filters}
            onChange={setFilters}
            onRefresh={handleRefresh}
            isFetching={isFetching}
          />

          {/* Error Banner if API call fails */}
          {isError && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-xs text-red-700 flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
              <span>
                Failed to load situational dashboard data:{' '}
                {activeError instanceof Error ? activeError.message : 'Unknown error'}.
              </span>
            </div>
          )}

          {/* Row 1: KPI Summary Cards (Server-side Aggregated) */}
          <DashboardKpiCards
            summary={summaryData}
            reports={reports}
            isLoading={isSummaryLoading}
          />

          {/* Row 2: Situational Overview Map + Live Incident Feed (Raw Pin/Feed Data) */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Left 8 columns: Situational Map */}
            <div className="lg:col-span-8">
              <DashboardMap
                reports={reports}
                selectedReport={selectedReport}
                onSelectReport={setSelectedReport}
                targetRegion={targetRegion}
              />
            </div>

            {/* Right 4 columns: Recent Incident Feed */}
            <div className="lg:col-span-4">
              <RecentIncidentFeed
                reports={reports}
                selectedReport={selectedReport}
                onSelectReport={setSelectedReport}
                isLoading={isRawLoading}
              />
            </div>
          </div>

          {/* Row 3: Bottom Analytics and Distribution Cards (Server-side Aggregated) */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <IncidentTrendCard
              distribution={summaryData?.diurnal_distribution}
              reports={reports}
              isLoading={isSummaryLoading}
            />
            <EventDistributionCard
              distribution={summaryData?.category_distribution}
              reports={reports}
              isLoading={isSummaryLoading}
            />
            <VerificationSummaryCard
              verification={summaryData?.verification}
              totalCount={summaryData?.total_count}
              reports={reports}
              isLoading={isSummaryLoading}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />

      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />
    </div>
  );
};
