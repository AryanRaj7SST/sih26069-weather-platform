import React from 'react';
import { MapPin, Clock, ImageOff, ChevronRight } from 'lucide-react';
import { ReportDetailData } from '@/types';

interface QueueMobileListProps {
  reports: ReportDetailData[];
  selectedReport: ReportDetailData | null;
  onSelectReport: (report: ReportDetailData) => void;
  isLoading: boolean;
}

export const QueueMobileList: React.FC<QueueMobileListProps> = ({
  reports,
  selectedReport,
  onSelectReport,
  isLoading,
}) => {
  const formatRelativeTime = (dateStr: string) => {
    try {
      const now = Date.now();
      const past = new Date(dateStr).getTime();
      const diffMinutes = Math.max(1, Math.floor((now - past) / (1000 * 60)));

      if (diffMinutes < 60) return `${diffMinutes} mins ago`;
      const diffHours = Math.floor(diffMinutes / 60);
      if (diffHours < 24) return `${diffHours} hr${diffHours > 1 ? 's' : ''} ago`;
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    } catch {
      return dateStr;
    }
  };

  const getSeverityBadge = (severity: string) => {
    const sev = severity.toUpperCase();
    if (sev === 'SEVERE' || sev === 'CRITICAL') {
      return (
        <span className="rounded-md bg-red-100 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-red-700">
          Severe
        </span>
      );
    }
    if (sev === 'HIGH') {
      return (
        <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-amber-700">
          High
        </span>
      );
    }
    if (sev === 'MODERATE') {
      return (
        <span className="rounded-md bg-blue-100 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-blue-700">
          Moderate
        </span>
      );
    }
    return (
      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-slate-700">
        Low
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-36 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-semibold text-slate-700">
          No reports matching the selected filters.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {reports.map((report) => {
        const isSelected = selectedReport?.id === report.id;
        const hasMedia = report.media && report.media.length > 0;
        const mediaUrl = hasMedia ? report.media[0].url : null;

        return (
          <div
            key={report.id}
            onClick={() => onSelectReport(report)}
            className={`rounded-2xl border bg-white p-4 shadow-sm transition-all cursor-pointer ${
              isSelected
                ? 'border-blue-500 ring-2 ring-blue-500/20'
                : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            {/* Header: Severity Badge & Tracking ID */}
            <div className="flex items-center justify-between">
              {getSeverityBadge(report.severity)}
              <span className="font-mono text-xs font-bold text-slate-700">
                ID: {report.tracking_id}
              </span>
            </div>

            {/* Content: Photo + Title + Location + Time */}
            <div className="mt-3 flex items-start space-x-3">
              {mediaUrl ? (
                <img
                  src={mediaUrl}
                  alt={report.title}
                  className="h-16 w-16 flex-shrink-0 rounded-xl object-cover border border-slate-200 shadow-2xs"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              ) : (
                <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-400 border border-slate-200">
                  <ImageOff className="h-6 w-6" />
                </div>
              )}

              <div className="flex-1 min-w-0">
                <h4 className="font-bold text-sm text-slate-900 truncate">
                  {report.category?.title || report.title}
                </h4>
                <div className="mt-1 flex items-center space-x-1 text-xs text-slate-600 truncate">
                  <MapPin className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
                  <span className="truncate">
                    {report.location?.name || `${report.location?.latitude.toFixed(2)}, ${report.location?.longitude.toFixed(2)}`}
                  </span>
                </div>
                <div className="mt-1 flex items-center space-x-1 text-xs text-slate-500">
                  <Clock className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
                  <span>{formatRelativeTime(report.occurred_at || report.created_at)}</span>
                </div>
              </div>
            </div>

            {/* Footer Divider: Credibility & Review Button */}
            <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
              <div className="text-xs text-slate-600">
                <span className="text-slate-400 font-medium">Credibility: </span>
                {report.credibility_score > 0 ? (
                  <span className="font-bold text-emerald-600">
                    {(report.credibility_score * 100).toFixed(0)}%
                  </span>
                ) : (
                  <span className="text-slate-400 italic">Not Calculated</span>
                )}
              </div>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectReport(report);
                }}
                className="flex items-center space-x-1 text-xs font-bold text-blue-600 hover:text-blue-700 cursor-pointer"
              >
                <span>Review</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};
