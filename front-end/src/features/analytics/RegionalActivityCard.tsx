import React from 'react';
import { AnalyticsRegionalData, RegionalDistributionItem, ReportDetailData } from '@/types';

interface RegionalActivityCardProps {
  regionalData?: AnalyticsRegionalData;
  regions?: RegionalDistributionItem[];
  reports?: ReportDetailData[]; // compatibility fallback
  isLoading: boolean;
}

export const RegionalActivityCard: React.FC<RegionalActivityCardProps> = ({
  regionalData,
  regions: propRegions,
  isLoading,
}) => {
  // Directly consume server-provided ranked regions (top 5 displayed)
  const items = propRegions || regionalData?.regions || [];
  const displayStats = items.slice(0, 5);

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
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold text-slate-900">
          Regional Activity
        </h2>
        <span className="text-[11px] font-medium text-slate-400">
          Derived from location & spatial classification
        </span>
      </div>

      {displayStats.length > 0 ? (
        <div className="divide-y divide-slate-100">
          {displayStats.map((item) => (
            <div
              key={item.region_code}
              className="flex items-center justify-between py-3 text-xs font-semibold text-slate-700"
            >
              <span>{item.region_name}</span>
              <div className="flex items-center space-x-2">
                {item.percentage !== undefined && item.percentage > 0 && (
                  <span className="text-[11px] font-mono text-slate-400">
                    {item.percentage}%
                  </span>
                )}
                <span className="inline-flex items-center rounded-lg bg-blue-50 px-2.5 py-1 font-mono text-xs font-bold text-blue-700">
                  {item.count}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-400 py-6 text-center">
          No regional report activity recorded
        </p>
      )}
    </div>
  );
};
