import React, { useMemo } from 'react';
import { ReportDetailData } from '@/types';

interface SeverityDistributionCardProps {
  reports: ReportDetailData[];
  isLoading: boolean;
}

export const SeverityDistributionCard: React.FC<SeverityDistributionCardProps> = ({
  reports,
  isLoading,
}) => {
  const severityStats = useMemo(() => {
    let severe = 0;
    let high = 0;
    let moderate = 0;
    let low = 0;

    for (const r of reports) {
      const sev = r.severity.toUpperCase();
      if (sev === 'SEVERE' || sev === 'CRITICAL') severe++;
      else if (sev === 'HIGH') high++;
      else if (sev === 'MODERATE') moderate++;
      else if (sev === 'LOW') low++;
    }

    return [
      { label: 'Severe', count: severe, color: 'bg-red-600', textClass: 'text-red-700' },
      { label: 'High', count: high, color: 'bg-amber-600', textClass: 'text-amber-700' },
      { label: 'Moderate', count: moderate, color: 'bg-teal-600', textClass: 'text-teal-700' },
      { label: 'Low', count: low, color: 'bg-slate-600', textClass: 'text-slate-700' },
    ];
  }, [reports]);

  const maxCount = Math.max(1, ...severityStats.map((s) => s.count));

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
        Severity Distribution
      </h2>

      <div className="space-y-4">
        {severityStats.map((item) => {
          const pct = Math.max(item.count > 0 ? 8 : 0, Math.round((item.count / maxCount) * 100));

          return (
            <div key={item.label} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <span className={item.textClass}>{item.label}</span>
                <span className="font-mono text-slate-900 font-bold">
                  {item.count}
                </span>
              </div>
              {/* Horizontal Progress Bar */}
              <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full rounded-full ${item.color} transition-all duration-500`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
