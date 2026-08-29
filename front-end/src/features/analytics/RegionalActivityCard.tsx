import React, { useMemo } from 'react';
import { ReportDetailData } from '@/types';
import { GEOGRAPHY_OPTIONS } from './constants';

interface RegionalActivityCardProps {
  reports: ReportDetailData[];
  isLoading: boolean;
}

export const RegionalActivityCard: React.FC<RegionalActivityCardProps> = ({
  reports,
  isLoading,
}) => {
  const regionStats = useMemo(() => {
    const counts: Record<string, { label: string; count: number }> = {};

    // Initialize states from GEOGRAPHY_OPTIONS (excluding ALL)
    for (const [code, opt] of Object.entries(GEOGRAPHY_OPTIONS)) {
      if (code !== 'ALL') {
        counts[code] = { label: opt.label, count: 0 };
      }
    }
    counts['OTHER'] = { label: 'Other Regions', count: 0 };

    for (const r of reports) {
      const locName = (r.location?.name || '').toLowerCase();
      const lat = r.location?.latitude;
      const lon = r.location?.longitude;
      let matchedCode: string | null = null;

      // 1. Match against region keywords
      for (const [code, opt] of Object.entries(GEOGRAPHY_OPTIONS)) {
        if (code !== 'ALL' && opt.keywords) {
          if (opt.keywords.some((kw) => locName.includes(kw))) {
            matchedCode = code;
            break;
          }
        }
      }

      // 2. Spatial bounding box fallback if coordinates available
      if (!matchedCode && lat !== undefined && lon !== undefined) {
        for (const [code, opt] of Object.entries(GEOGRAPHY_OPTIONS)) {
          if (code !== 'ALL' && opt.bbox) {
            const [minLon, minLat, maxLon, maxLat] = opt.bbox.split(',').map(Number);
            if (lon >= minLon && lon <= maxLon && lat >= minLat && lat <= maxLat) {
              matchedCode = code;
              break;
            }
          }
        }
      }

      if (matchedCode && counts[matchedCode]) {
        counts[matchedCode].count++;
      } else {
        counts['OTHER'].count++;
      }
    }

    return Object.values(counts)
      .filter((item) => item.count > 0)
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
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
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold text-slate-900">
          Regional Activity
        </h2>
        <span className="text-[11px] font-medium text-slate-400">
          Derived from spatial bounds
        </span>
      </div>

      {regionStats.length > 0 ? (
        <div className="divide-y divide-slate-100">
          {regionStats.map((item) => (
            <div
              key={item.label}
              className="flex items-center justify-between py-3 text-xs font-semibold text-slate-700"
            >
              <span>{item.label}</span>
              <span className="inline-flex items-center rounded-lg bg-blue-50 px-2.5 py-1 font-mono text-xs font-bold text-blue-700">
                {item.count}
              </span>
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
