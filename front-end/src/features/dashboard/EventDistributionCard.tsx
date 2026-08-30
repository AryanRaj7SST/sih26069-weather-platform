import React, { useMemo } from 'react';
import { BarChart3 } from 'lucide-react';
import { CategoryDistributionItem, ReportDetailData } from '@/types';

interface EventDistributionCardProps {
  distribution?: CategoryDistributionItem[];
  reports?: ReportDetailData[];
  isLoading: boolean;
}

export const EventDistributionCard: React.FC<EventDistributionCardProps> = ({
  distribution: inputDistribution,
  reports = [],
  isLoading,
}) => {
  const distribution = useMemo(() => {
    if (inputDistribution && inputDistribution.length > 0) {
      const sorted = [...inputDistribution].sort((a, b) => b.count - a.count);
      const top4 = sorted.slice(0, 4).map((item) => ({
        title: item.category_name,
        count: item.count,
        pct: item.percentage,
      }));
      const otherItems = sorted.slice(4);
      if (otherItems.length > 0) {
        const otherCount = otherItems.reduce((sum, item) => sum + item.count, 0);
        const otherPct = otherItems.reduce((sum, item) => sum + item.percentage, 0);
        top4.push({
          title: 'Other Hazards',
          count: otherCount,
          pct: otherPct,
        });
      }
      return top4;
    }

    if (reports.length === 0) return [];

    const catCounts: Record<string, { title: string; count: number }> = {};

    for (const report of reports) {
      const code = report.category?.code || 'OTHER';
      const title = report.category?.title || 'Other Hazard';

      if (!catCounts[code]) {
        catCounts[code] = { title, count: 0 };
      }
      catCounts[code].count++;
    }

    // Sort by count descending and take top 4
    const sorted = Object.values(catCounts).sort((a, b) => b.count - a.count);
    const top4 = sorted.slice(0, 4);
    const otherCount = sorted.slice(4).reduce((sum, item) => sum + item.count, 0);

    if (otherCount > 0) {
      top4.push({ title: 'Other Hazards', count: otherCount });
    }

    return top4.map((item) => ({
      title: item.title,
      count: item.count,
      pct: Math.round((item.count / reports.length) * 100),
    }));
  }, [inputDistribution, reports]);

  const barColors = ['bg-blue-600', 'bg-sky-500', 'bg-amber-500', 'bg-slate-400'];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col justify-between">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2">
          <BarChart3 className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Event Distribution</h3>
        </div>
        <span className="text-[11px] text-slate-400 font-medium">By Category</span>
      </div>

      <div className="mt-4 space-y-3.5 flex-1 flex flex-col justify-center">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="space-y-1 animate-pulse">
                <div className="h-3 w-28 bg-slate-200 rounded" />
                <div className="h-2 w-full bg-slate-100 rounded-full" />
              </div>
            ))}
          </div>
        ) : distribution.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-400 font-medium">
            No hazard category data in current selection.
          </div>
        ) : (
          distribution.map((item, idx) => (
            <div key={item.title} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">{item.title}</span>
                <span className="font-bold text-slate-900 font-mono text-[11px]">
                  {item.pct}% <span className="text-slate-400 font-normal">({item.count})</span>
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    barColors[idx % barColors.length]
                  }`}
                  style={{ width: `${Math.max(item.pct, 3)}%` }}
                />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
