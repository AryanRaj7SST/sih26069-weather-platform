import React from 'react';
import { ListFilter, ExternalLink, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ReportDetailData } from '@/types';

interface RecentIncidentFeedProps {
  reports: ReportDetailData[];
  selectedReport: ReportDetailData | null;
  onSelectReport: (report: ReportDetailData) => void;
  isLoading: boolean;
}

const formatRelativeTime = (dateStr: string) => {
  try {
    const diffMs = Date.now() - new Date(dateStr).getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return 'Recent';
  }
};

export const RecentIncidentFeed: React.FC<RecentIncidentFeedProps> = ({
  reports,
  selectedReport,
  onSelectReport,
  isLoading,
}) => {
  // Take the most recent 5 reports
  const displayReports = reports.slice(0, 5);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col h-full">
      {/* Feed Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-white">
        <div className="flex items-center space-x-2">
          <ListFilter className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Current Incident Feed</h3>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="h-2 w-2 rounded-full bg-blue-600 animate-pulse" />
          <span className="text-xs text-slate-500 font-semibold">{reports.length} Reports</span>
        </div>
      </div>

      {/* Feed List Body */}
      <div className="p-4 flex-1 overflow-y-auto space-y-3 max-h-[480px]">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 rounded-xl border border-slate-100 bg-slate-50 p-3 animate-pulse">
                <div className="h-3 w-20 bg-slate-200 rounded" />
                <div className="h-4 w-40 bg-slate-200 rounded mt-2" />
                <div className="h-3 w-full bg-slate-100 rounded mt-2" />
              </div>
            ))}
          </div>
        ) : displayReports.length === 0 ? (
          <div className="py-12 text-center text-slate-500">
            <p className="text-xs font-semibold">No incident reports found matching current filters.</p>
          </div>
        ) : (
          displayReports.map((report) => {
            const isSelected = selectedReport?.tracking_id === report.tracking_id;
            const isSevere = report.severity === 'SEVERE' || report.severity === 'HIGH';
            const isVerified = report.verification_status === 'VERIFIED';
            const isUnderReview = report.verification_status === 'UNDER_REVIEW';

            let borderLeftClass = 'border-l-4 border-l-blue-500';
            let catColorClass = 'text-blue-700';
            if (isSevere) {
              borderLeftClass = 'border-l-4 border-l-red-500';
              catColorClass = 'text-red-700';
            } else if (report.severity === 'MODERATE') {
              borderLeftClass = 'border-l-4 border-l-amber-500';
              catColorClass = 'text-amber-700';
            }

            return (
              <div
                key={report.id || report.tracking_id}
                onClick={() => onSelectReport(report)}
                className={`rounded-xl border p-3.5 transition-all cursor-pointer ${borderLeftClass} ${
                  isSelected
                    ? 'border-blue-500 bg-blue-50/40 ring-2 ring-blue-500/20 shadow-sm'
                    : 'border-slate-200/80 bg-white hover:border-slate-300 hover:bg-slate-50/60 shadow-xs'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-[10px] font-extrabold uppercase tracking-wider ${catColorClass}`}>
                    {report.category?.title || 'Weather Event'}
                  </span>
                  <span className="text-[10px] font-medium text-slate-400">
                    {formatRelativeTime(report.occurred_at || report.created_at)}
                  </span>
                </div>

                <h4 className="text-xs font-bold text-slate-900 mt-1">
                  {report.location?.name || report.title}
                </h4>

                {report.description && (
                  <p className="text-[11px] text-slate-500 line-clamp-2 mt-1 leading-relaxed">
                    {report.description}
                  </p>
                )}

                <div className="mt-2.5 flex items-center justify-between pt-2 border-t border-slate-100">
                  <div className="flex items-center space-x-1.5">
                    <span
                      className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold ${
                        isVerified
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : isUnderReview
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-slate-100 text-slate-700 border border-slate-200'
                      }`}
                    >
                      Status: {report.verification_status || 'Pending'}
                    </span>
                  </div>

                  <Link
                    to={`/track-report?id=${encodeURIComponent(report.tracking_id)}`}
                    onClick={(e) => e.stopPropagation()}
                    className="flex items-center space-x-1 text-[10px] font-bold text-blue-600 hover:text-blue-800"
                  >
                    <span>Inspect</span>
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Feed Footer */}
      <div className="p-3 border-t border-slate-100 bg-slate-50/50">
        <Link
          to="/live-map"
          className="flex w-full items-center justify-center space-x-1.5 rounded-xl bg-white py-2 text-xs font-bold text-blue-600 border border-slate-200 shadow-2xs hover:bg-slate-50 hover:border-slate-300 transition-colors"
        >
          <span>View All Incidents on Map</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
};
