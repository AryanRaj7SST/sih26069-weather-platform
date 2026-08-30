import React, { useMemo } from 'react';
import { CategoryDistributionItem, ReportDetailData } from '@/types';

interface EventDistributionCardProps {
  distribution?: CategoryDistributionItem[];
  reports?: ReportDetailData[];
  isLoading: boolean;
}

export const EventDistributionCard: React.FC<EventDistributionCardProps> = ({
  distribution,
  reports = [],
  isLoading,
}) => {
  const categoryStats = useMemo(() => {
    if (distribution && distribution.length > 0) {
      return distribution.slice(0, 6).map((item) => ({
        label: item.category_name,
        count: item.count,
      }));
    }

    if (reports.length === 0) return [];

    const counts: Record<string, { label: string; count: number }> = {};

    for (const r of reports) {
      const code = r.category?.code || 'OTHER';
      const label = r.category?.title || r.title || 'Other Incident';

      if (!counts[code]) {
        counts[code] = { label, count: 0 };
      }
      counts[code].count++;
    }

    return Object.values(counts)
      .sort((a, b) => b.count - a.count)
      .slice(0, 6);
  }, [distribution, reports]);

  const maxCount = categoryStats.length > 0 ? categoryStats[0].count : 1;

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
        Event Distribution
      </h2>

      {categoryStats.length > 0 ? (
        <div className="space-y-4">
          {categoryStats.map((item) => {
            const pct = Math.max(8, Math.round((item.count / maxCount) * 100));

            return (
              <div key={item.label} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                  <span>{item.label}</span>
                  <span className="font-mono text-slate-900 font-bold">
                    {item.count}
                  </span>
                </div>
                {/* Horizontal Progress Bar */}
                <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-blue-600 transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-xs text-slate-400 py-6 text-center">
          No hazard events in selected period
        </p>
      )}
    </div>
  );
};
