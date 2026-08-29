import React from 'react';
import { RefreshCw, CheckCircle2, AlertTriangle } from 'lucide-react';
import { ReportDetailData } from '@/types';

interface ReportStatusBannerProps {
  report: ReportDetailData;
}

export const ReportStatusBanner: React.FC<ReportStatusBannerProps> = ({ report }) => {
  const formattedDate = new Date(report.occurred_at || report.created_at).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
      case 'VERIFIED':
        return (
          <span className="inline-flex items-center space-x-1.5 rounded-full bg-emerald-50 px-3.5 py-1 text-xs font-bold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>VERIFIED</span>
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center space-x-1.5 rounded-full bg-rose-50 px-3.5 py-1 text-xs font-bold text-rose-700 border border-rose-200">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>REJECTED</span>
          </span>
        );
      case 'PROCESSING':
      case 'QUEUED':
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 rounded-full bg-blue-50 px-3.5 py-1 text-xs font-bold text-blue-700 border border-blue-200">
            <RefreshCw className="h-3.5 w-3.5 animate-spin text-blue-600" />
            <span>{status || 'QUEUED'}</span>
          </span>
        );
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* ID & Date Pill */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-slate-100 px-2.5 py-1 font-mono text-xs font-bold tracking-wider text-slate-700 border border-slate-200">
            ID: {report.tracking_id}
          </span>
          <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
            {formattedDate}
          </span>
        </div>

        {/* Status Badge */}
        <div>{getStatusBadge(report.processing_status)}</div>
      </div>

      {/* Main Title */}
      <h2 className="mt-3 text-xl md:text-2xl font-bold tracking-tight text-slate-900">
        {report.title}
      </h2>

      {report.description && (
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          {report.description}
        </p>
      )}
    </div>
  );
};
