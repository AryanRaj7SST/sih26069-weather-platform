import React, { useMemo } from 'react';
import { ReportDetailData } from '@/types';

interface VerificationStatusCardProps {
  reports: ReportDetailData[];
  isLoading: boolean;
}

export const VerificationStatusCard: React.FC<VerificationStatusCardProps> = ({
  reports,
  isLoading,
}) => {
  const statusStats = useMemo(() => {
    let verified = 0;
    let pending = 0;
    let underReview = 0;
    let rejected = 0;
    let duplicate = 0;

    for (const r of reports) {
      const s = r.verification_status.toUpperCase();
      if (s === 'VERIFIED') verified++;
      else if (s === 'UNDER_REVIEW') underReview++;
      else if (s === 'REJECTED') rejected++;
      else if (s === 'DUPLICATE') duplicate++;
      else pending++;
    }

    return [
      { label: 'Verified', count: verified, countClass: 'text-blue-600 font-extrabold' },
      { label: 'Pending', count: pending, countClass: 'text-slate-700 font-bold' },
      { label: 'Under Review', count: underReview, countClass: 'text-slate-700 font-bold' },
      { label: 'Rejected', count: rejected, countClass: 'text-rose-600 font-bold' },
      { label: 'Duplicate', count: duplicate, countClass: 'text-purple-600 font-bold' },
    ];
  }, [reports]);

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm animate-pulse space-y-4">
        <div className="h-4 w-36 bg-slate-200 rounded" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-6 bg-slate-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-bold text-slate-900 mb-4">
        Verification Status
      </h2>

      <div className="divide-y divide-slate-100">
        {statusStats.map((item) => (
          <div
            key={item.label}
            className="flex items-center justify-between py-3 text-xs font-semibold text-slate-700"
          >
            <span>{item.label}</span>
            <span className={`font-mono text-sm ${item.countClass}`}>
              {item.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
