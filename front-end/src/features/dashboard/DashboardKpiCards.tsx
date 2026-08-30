import React, { useMemo } from 'react';
import { AlertCircle, FileText, Clock, CheckCircle2 } from 'lucide-react';
import { DashboardSummaryData, PaginationMeta, ReportDetailData } from '@/types';

interface DashboardKpiCardsProps {
  summary?: DashboardSummaryData;
  reports?: ReportDetailData[];
  pagination?: PaginationMeta;
  isLoading: boolean;
}

export const DashboardKpiCards: React.FC<DashboardKpiCardsProps> = ({
  summary,
  reports = [],
  pagination,
  isLoading,
}) => {
  const stats = useMemo(() => {
    if (summary) {
      return {
        totalCount: summary.total_count,
        reportsLast24h: summary.count_24h,
        pct24h: summary.last_24h_pct,
        pendingCount: summary.verification.pending_count,
        verifiedCount: summary.verification.verified_count,
        verifiedPct: summary.verification.verified_rate,
        severeCount: summary.severity.severe_high_count,
      };
    }

    const totalCount = pagination?.total_records ?? reports.length;
    const now = Date.now();
    const oneDayAgo = now - 24 * 60 * 60 * 1000;

    let reportsLast24h = 0;
    let pendingCount = 0;
    let verifiedCount = 0;
    let severeCount = 0;

    for (const report of reports) {
      // Check last 24h
      const reportTime = report.occurred_at ? new Date(report.occurred_at).getTime() : new Date(report.created_at).getTime();
      if (!isNaN(reportTime) && reportTime >= oneDayAgo) {
        reportsLast24h++;
      }

      // Check verification status
      if (report.verification_status === 'VERIFIED') {
        verifiedCount++;
      } else if (report.verification_status === 'PENDING' || report.verification_status === 'UNDER_REVIEW') {
        pendingCount++;
      }

      // Check severity
      if (report.severity === 'SEVERE' || report.severity === 'HIGH') {
        severeCount++;
      }
    }

    const verifiedPct = totalCount > 0 ? Math.round((verifiedCount / totalCount) * 100) : 0;
    const pct24h = totalCount > 0 ? Math.round((reportsLast24h / totalCount) * 100) : 0;

    return {
      totalCount,
      reportsLast24h,
      pct24h,
      pendingCount,
      verifiedCount,
      verifiedPct,
      severeCount,
    };
  }, [summary, reports, pagination]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-28 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm animate-pulse flex flex-col justify-between"
          >
            <div className="h-4 w-24 bg-slate-200 rounded" />
            <div className="h-8 w-16 bg-slate-200 rounded" />
            <div className="h-3 w-32 bg-slate-100 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Active Incidents Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:shadow-md">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Active Incidents
          </span>
          <div className="rounded-full bg-red-50 p-1.5 text-red-600">
            <AlertCircle className="h-4 w-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline space-x-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {stats.totalCount}
          </span>
        </div>
        <div className="mt-2 flex items-center text-xs text-slate-500 font-medium">
          <span className={stats.severeCount > 0 ? 'text-red-600 font-semibold' : 'text-slate-500'}>
            {stats.severeCount > 0 ? `${stats.severeCount} high/severe events` : 'No severe alerts active'}
          </span>
        </div>
      </div>

      {/* 2. Reports Last 24H Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:shadow-md">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Reports (Last 24h)
          </span>
          <div className="rounded-full bg-blue-50 p-1.5 text-blue-600">
            <FileText className="h-4 w-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline space-x-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {stats.reportsLast24h}
          </span>
        </div>
        <div className="mt-2 flex items-center text-xs text-slate-500 font-medium">
          <span className="text-blue-600 font-semibold">{stats.pct24h}% of current records</span>
        </div>
      </div>

      {/* 3. Pending Review Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:shadow-md">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Pending Review
          </span>
          <div className="rounded-full bg-amber-50 p-1.5 text-amber-600">
            <Clock className="h-4 w-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline space-x-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {stats.pendingCount}
          </span>
        </div>
        <div className="mt-2 flex items-center text-xs text-amber-600 font-semibold">
          <span>Awaiting authority verification</span>
        </div>
      </div>

      {/* 4. Verified Reports Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:shadow-md">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Verified Reports
          </span>
          <div className="rounded-full bg-emerald-50 p-1.5 text-emerald-600">
            <CheckCircle2 className="h-4 w-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline space-x-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {stats.verifiedPct}%
          </span>
          <span className="text-xs text-slate-500 font-semibold">
            ({stats.verifiedCount} / {stats.totalCount})
          </span>
        </div>
        {/* Verification Progress Bar */}
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${stats.verifiedPct}%` }}
          />
        </div>
      </div>
    </div>
  );
};
