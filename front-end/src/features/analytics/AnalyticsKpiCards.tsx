import React, { useMemo } from 'react';
import { ReportDetailData, PaginationMeta } from '@/types';

interface AnalyticsKpiCardsProps {
  reports: ReportDetailData[];
  pagination?: PaginationMeta;
  timeRange: string;
  isLoading: boolean;
}

export const AnalyticsKpiCards: React.FC<AnalyticsKpiCardsProps> = ({
  reports,
  pagination,
  timeRange,
  isLoading,
}) => {
  const stats = useMemo(() => {
    const totalCount = pagination?.total_records ?? reports.length;
    let verifiedCount = 0;
    let pendingCount = 0;

    for (const r of reports) {
      if (r.verification_status === 'VERIFIED') {
        verifiedCount++;
      } else if (r.verification_status === 'PENDING' || r.verification_status === 'UNDER_REVIEW') {
        pendingCount++;
      }
    }

    const verifiedPct = reports.length > 0 ? Math.round((verifiedCount / reports.length) * 100) : 0;

    const periodLabelMap: Record<string, string> = {
      '24h': '24 Hours',
      '7d': '7 Days',
      '30d': '30 Days',
      all: 'All Time',
    };

    return {
      totalCount,
      periodReports: reports.length,
      verifiedCount,
      verifiedPct,
      pendingCount,
      periodLabel: periodLabelMap[timeRange] || 'Selected Period',
    };
  }, [reports, pagination, timeRange]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-28 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm animate-pulse flex flex-col justify-between"
          >
            <div className="h-4 w-24 bg-slate-200 rounded" />
            <div className="h-8 w-16 bg-slate-200 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Total Reports */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Total Reports
        </span>
        <div className="mt-2 text-3xl font-extrabold text-slate-900">
          {stats.totalCount.toLocaleString()}
        </div>
      </div>

      {/* 2. Period Reports */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Period Reports
        </span>
        <div className="mt-2 text-3xl font-extrabold text-blue-600">
          {stats.periodReports.toLocaleString()}
        </div>
      </div>

      {/* 3. Verified */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Verified
        </span>
        <div className="mt-2 flex items-baseline space-x-2">
          <span className="text-3xl font-extrabold text-emerald-600">
            {stats.verifiedPct}%
          </span>
          <span className="text-xs font-semibold text-slate-400">
            ({stats.verifiedCount})
          </span>
        </div>
      </div>

      {/* 4. Pending */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Pending
        </span>
        <div className="mt-2 text-3xl font-extrabold text-amber-600">
          {stats.pendingCount.toLocaleString()}
        </div>
      </div>
    </div>
  );
};
