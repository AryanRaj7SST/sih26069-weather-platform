import React from 'react';
import { Filter, RefreshCw, X } from 'lucide-react';
import {
  TIME_RANGE_OPTIONS,
  HAZARD_OPTIONS,
  SEVERITY_OPTIONS,
  VERIFICATION_OPTIONS,
  GEOGRAPHY_OPTIONS,
} from './constants';

export interface AnalyticsFilterState {
  timeRange: string;
  category: string;
  severity: string;
  status: string;
  region: string;
}

interface AnalyticsFiltersProps {
  filters: AnalyticsFilterState;
  tempFilters: AnalyticsFilterState;
  onTempChange: (newFilters: AnalyticsFilterState) => void;
  onApply: () => void;
  onReset: () => void;
  isFetching: boolean;
}

export const AnalyticsFilters: React.FC<AnalyticsFiltersProps> = ({
  filters,
  tempFilters,
  onTempChange,
  onApply,
  onReset,
  isFetching,
}) => {
  const isFiltered =
    filters.timeRange !== '7d' ||
    filters.category !== 'ALL' ||
    filters.severity !== 'ALL' ||
    filters.status !== 'ALL' ||
    filters.region !== 'ALL';

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        {/* Dropdown Filters Group */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Time Range */}
          <div className="relative">
            <select
              value={tempFilters.timeRange}
              onChange={(e) => onTempChange({ ...tempFilters, timeRange: e.target.value })}
              aria-label="Filter by date range"
              className="appearance-none rounded-xl border border-slate-200 bg-slate-50/80 py-2 pl-3.5 pr-8 text-xs font-semibold text-slate-700 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            >
              {TIME_RANGE_OPTIONS.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-2.5 top-2.5 text-[10px] text-slate-400">
              ▼
            </div>
          </div>

          {/* Event / Hazard */}
          <div className="relative">
            <select
              value={tempFilters.category}
              onChange={(e) => onTempChange({ ...tempFilters, category: e.target.value })}
              aria-label="Filter by event hazard"
              className="appearance-none rounded-xl border border-slate-200 bg-slate-50/80 py-2 pl-3.5 pr-8 text-xs font-semibold text-slate-700 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            >
              {HAZARD_OPTIONS.map((h) => (
                <option key={h.code} value={h.code}>
                  {h.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-2.5 top-2.5 text-[10px] text-slate-400">
              ▼
            </div>
          </div>

          {/* Severity */}
          <div className="relative">
            <select
              value={tempFilters.severity}
              onChange={(e) => onTempChange({ ...tempFilters, severity: e.target.value })}
              aria-label="Filter by severity"
              className="appearance-none rounded-xl border border-slate-200 bg-slate-50/80 py-2 pl-3.5 pr-8 text-xs font-semibold text-slate-700 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            >
              {SEVERITY_OPTIONS.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-2.5 top-2.5 text-[10px] text-slate-400">
              ▼
            </div>
          </div>

          {/* Verification Status */}
          <div className="relative">
            <select
              value={tempFilters.status}
              onChange={(e) => onTempChange({ ...tempFilters, status: e.target.value })}
              aria-label="Filter by verification status"
              className="appearance-none rounded-xl border border-slate-200 bg-slate-50/80 py-2 pl-3.5 pr-8 text-xs font-semibold text-slate-700 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            >
              {VERIFICATION_OPTIONS.map((v) => (
                <option key={v.code} value={v.code}>
                  {v.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-2.5 top-2.5 text-[10px] text-slate-400">
              ▼
            </div>
          </div>

          {/* Geography / Region */}
          <div className="relative">
            <select
              value={tempFilters.region}
              onChange={(e) => onTempChange({ ...tempFilters, region: e.target.value })}
              aria-label="Filter by geographic region"
              className="appearance-none rounded-xl border border-slate-200 bg-slate-50/80 py-2 pl-3.5 pr-8 text-xs font-semibold text-slate-700 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            >
              {Object.entries(GEOGRAPHY_OPTIONS).map(([code, reg]) => (
                <option key={code} value={code}>
                  {reg.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-2.5 top-2.5 text-[10px] text-slate-400">
              ▼
            </div>
          </div>

          {isFiltered && (
            <button
              type="button"
              onClick={onReset}
              className="flex items-center space-x-1 rounded-xl px-2.5 py-1.5 text-xs font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors cursor-pointer"
            >
              <X className="h-3 w-3" />
              <span>Reset</span>
            </button>
          )}
        </div>

        {/* Right Action: Apply Filters Button */}
        <div className="flex items-center justify-end">
          <button
            type="button"
            onClick={onApply}
            disabled={isFetching}
            className="flex items-center space-x-1.5 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/30 disabled:opacity-60 transition-all cursor-pointer"
          >
            {isFetching ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Filter className="h-3.5 w-3.5" />
            )}
            <span>Apply Filters</span>
          </button>
        </div>
      </div>
    </div>
  );
};
