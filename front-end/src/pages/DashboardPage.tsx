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
import { fetchAllDashboardReports } from '@/services/reportApi';
import { ReportDetailData, ReportListQueryParams } from '@/types';
import { AlertTriangle } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [filters, setFilters] = useState<DashboardFilterState>({
    timeRange: '24h',
    hazard: 'ALL',
    region: 'ALL',
    status: 'ALL',
  });

  const [selectedReport, setSelectedReport] = useState<ReportDetailData | null>(null);

  // Compute from_date based on timeRange filter
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

  // Construct query parameters matching the real backend GET /api/v1/reports
  const queryParams: ReportListQueryParams = useMemo(() => {
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

    // Map regional filter to spatial bounding box
    const regionInfo = REGIONS[filters.region];
    if (regionInfo?.bbox) {
      params.bbox = regionInfo.bbox;
    }

    return params;
  }, [filters, fromDate]);

  // Fetch complete dataset across pages from real backend API using shared TanStack Query hook
  const {
    data: response,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['dashboard-reports', queryParams],
    queryFn: () => fetchAllDashboardReports(queryParams),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });

  const reports = useMemo(() => response?.data || [], [response]);
  const pagination = response?.pagination;

  const targetRegion = useMemo(() => {
    const reg = REGIONS[filters.region];
    return reg ? { center: reg.center, zoom: reg.zoom } : undefined;
  }, [filters.region]);

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
            onRefresh={() => refetch()}
            isFetching={isFetching}
          />

          {/* Error Banner if API call fails */}
          {isError && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-xs text-red-700 flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
              <span>
                Failed to load situational dashboard data: {error instanceof Error ? error.message : 'Unknown error'}.
              </span>
            </div>
          )}

          {/* Row 1: KPI Summary Cards */}
          <DashboardKpiCards
            reports={reports}
            pagination={pagination}
            isLoading={isLoading}
          />

          {/* Row 2: Situational Overview Map + Live Incident Feed */}
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
                isLoading={isLoading}
              />
            </div>
          </div>

          {/* Row 3: Bottom Analytics and Distribution Cards */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <IncidentTrendCard reports={reports} isLoading={isLoading} />
            <EventDistributionCard reports={reports} isLoading={isLoading} />
            <VerificationSummaryCard reports={reports} isLoading={isLoading} />
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
