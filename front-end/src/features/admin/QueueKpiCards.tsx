import React, { useMemo } from 'react';
import { Clock, AlertTriangle, AlertCircle, Copy } from 'lucide-react';
import { ReportDetailData } from '@/types';

interface QueueKpiCardsProps {
  reports: ReportDetailData[];
  isLoading: boolean;
}

export const QueueKpiCards: React.FC<QueueKpiCardsProps> = ({ reports, isLoading }) => {
  const counts = useMemo(() => {
    let pending = 0;
    let underReview = 0;
    let highPriority = 0;
    let duplicates = 0;

    for (const r of reports) {
      if (r.verification_status === 'PENDING') {
        pending++;
      } else if (r.verification_status === 'UNDER_REVIEW') {
        underReview++;
      } else if (r.verification_status === 'DUPLICATE') {
        duplicates++;
      }

      if (
        (r.severity === 'HIGH' || r.severity === 'SEVERE') &&
        (r.verification_status === 'PENDING' || r.verification_status === 'UNDER_REVIEW')
      ) {
        highPriority++;
      }
    }

    return { pending, underReview, highPriority, duplicates };
  }, [reports]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-28 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm animate-pulse flex flex-col justify-between"
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
      {/* 1. Pending Review */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Pending Review
            </span>
            <Clock className="h-4 w-4 text-blue-600" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-blue-600">
            {counts.pending}
          </div>
        </div>
        <p className="mt-2 text-[11px] text-slate-400 font-medium">
          Awaiting initial triage
        </p>
      </div>

      {/* 2. Under Review */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Under Review
            </span>
            <AlertCircle className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-emerald-600">
            {counts.underReview}
          </div>
        </div>
        <p className="mt-2 text-[11px] text-slate-400 font-medium">
          Active operator inspection
        </p>
      </div>

      {/* 3. High Priority */}
      <div className="rounded-2xl border-l-4 border-l-amber-500 border border-slate-200 bg-white p-5 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              High Priority
            </span>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-amber-600">
            {counts.highPriority}
          </div>
        </div>
        <p className="mt-2 text-[11px] text-slate-400 font-medium">
          Severe & High unverified reports
        </p>
      </div>

      {/* 4. Possible Duplicates */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Possible Duplicates
            </span>
            <Copy className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-slate-700">
            {counts.duplicates}
          </div>
        </div>
        <p className="mt-2 text-[11px] text-slate-400 font-medium">
          Flagged or duplicate status
        </p>
      </div>
    </div>
  );
};
