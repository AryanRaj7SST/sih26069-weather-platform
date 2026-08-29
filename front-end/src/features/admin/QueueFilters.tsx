import React from 'react';
import { Filter, Search, X } from 'lucide-react';
import { HAZARD_OPTIONS, SEVERITY_OPTIONS, STATUS_OPTIONS } from './constants';

export interface QueueFilterState {
  status: string;
  category: string;
  severity: string;
  searchQuery: string;
}

interface QueueFiltersProps {
  filters: QueueFilterState;
  onChange: (newFilters: QueueFilterState) => void;
  onReset: () => void;
}

export const QueueFilters: React.FC<QueueFiltersProps> = ({
  filters,
  onChange,
  onReset,
}) => {
  const isFiltered =
    filters.status !== 'ACTIVE' ||
    filters.category !== 'ALL' ||
    filters.severity !== 'ALL' ||
    Boolean(filters.searchQuery);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        {/* Filters group */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500 mr-1">
            <Filter className="h-3.5 w-3.5 text-blue-600" />
            <span>Filters:</span>
          </div>

          {/* Status Dropdown */}
          <div className="relative">
            <select
              value={filters.status}
              onChange={(e) => onChange({ ...filters, status: e.target.value })}
              aria-label="Filter queue by status"
              className="appearance-none rounded-xl border border-slate-200 bg-slate-50/70 py-2 pl-3.5 pr-8 text-xs font-semibold text-slate-700 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.code} value={opt.code}>
                  {opt.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-2.5 top-2.5 text-slate-400">
              ▼
            </div>
          </div>

          {/* Event Dropdown */}
          <div className="relative">
            <select
              value={filters.category}
              onChange={(e) => onChange({ ...filters, category: e.target.value })}
              aria-label="Filter queue by hazard event"
              className="appearance-none rounded-xl border border-slate-200 bg-slate-50/70 py-2 pl-3.5 pr-8 text-xs font-semibold text-slate-700 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            >
              {HAZARD_OPTIONS.map((opt) => (
                <option key={opt.code} value={opt.code}>
                  {opt.code === 'ALL' ? 'Event: All' : opt.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-2.5 top-2.5 text-slate-400">
              ▼
            </div>
          </div>

          {/* Severity Dropdown */}
          <div className="relative">
            <select
              value={filters.severity}
              onChange={(e) => onChange({ ...filters, severity: e.target.value })}
              aria-label="Filter queue by severity"
              className="appearance-none rounded-xl border border-slate-200 bg-slate-50/70 py-2 pl-3.5 pr-8 text-xs font-semibold text-slate-700 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            >
              {SEVERITY_OPTIONS.map((opt) => (
                <option key={opt.code} value={opt.code}>
                  {opt.code === 'ALL' ? 'Severity: All' : opt.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-2.5 top-2.5 text-slate-400">
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

        {/* Tracking ID / Search Bar */}
        <div className="relative w-full lg:w-72">
          <input
            type="text"
            value={filters.searchQuery}
            onChange={(e) => onChange({ ...filters, searchQuery: e.target.value })}
            placeholder="Tracking ID or keyword..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50/70 py-2 pl-9 pr-4 text-xs font-medium text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
          />
          <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
        </div>
      </div>
    </div>
  );
};
