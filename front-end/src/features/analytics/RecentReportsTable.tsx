import React from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { IncidentSummary, ReportDetailData } from '@/types';

interface RecentReportsTableProps {
  reports: (ReportDetailData | IncidentSummary)[];
  isLoading: boolean;
}

export const RecentReportsTable: React.FC<RecentReportsTableProps> = ({
  reports,
  isLoading,
}) => {
  const recentList = reports.slice(0, 8);

  const formatTime = (dateStr?: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    } catch {
      return dateStr;
    }
  };

  const getSeverityBadge = (severity: string) => {
    const sev = severity.toUpperCase();
    if (sev === 'SEVERE' || sev === 'CRITICAL') {
      return (
        <span className="rounded-md bg-red-50 px-2 py-0.5 text-[11px] font-bold text-red-700 border border-red-200">
          Severe
        </span>
      );
    }
    if (sev === 'HIGH') {
      return (
        <span className="rounded-md bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700 border border-amber-200">
          High
        </span>
      );
    }
    if (sev === 'MODERATE') {
      return (
        <span className="rounded-md bg-teal-50 px-2 py-0.5 text-[11px] font-bold text-teal-700 border border-teal-200">
          Moderate
        </span>
      );
    }
    return (
      <span className="rounded-md bg-slate-50 px-2 py-0.5 text-[11px] font-bold text-slate-700 border border-slate-200">
        Low
      </span>
    );
  };

  const getStatusText = (status: string) => {
    const s = status.toUpperCase();
    if (s === 'VERIFIED') {
      return <span className="font-semibold text-emerald-600">Verified</span>;
    }
    if (s === 'UNDER_REVIEW') {
      return <span className="font-semibold text-amber-600">Under Review</span>;
    }
    if (s === 'REJECTED') {
      return <span className="font-semibold text-rose-600">Rejected</span>;
    }
    if (s === 'DUPLICATE') {
      return <span className="font-semibold text-purple-600">Duplicate</span>;
    }
    return <span className="font-semibold text-slate-600">Pending</span>;
  };

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm animate-pulse space-y-3">
        <div className="h-4 w-36 bg-slate-200 rounded" />
        <div className="h-40 bg-slate-100 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-900">
          Recent Reports
        </h2>
        <Link
          to="/live-map"
          className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center space-x-1"
        >
          <span>Explore on Map</span>
          <ExternalLink className="h-3 w-3" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-600">
          <thead className="border-b border-slate-100 bg-slate-50/60 text-[11px] font-bold uppercase tracking-wider text-slate-400">
            <tr>
              <th className="px-6 py-3">Event</th>
              <th className="px-6 py-3">Location</th>
              <th className="px-6 py-3">Severity</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Time</th>
              <th className="px-6 py-3 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {recentList.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50/60 transition-colors">
                <td className="px-6 py-3.5 font-bold text-slate-900">
                  {r.category?.title || ('title' in r ? r.title : 'Weather Event')}
                </td>
                <td className="px-6 py-3.5 text-slate-700">
                  {r.location?.name ||
                    (r.location?.latitude != null && r.location?.longitude != null
                      ? `${r.location.latitude.toFixed(2)}, ${r.location.longitude.toFixed(2)}`
                      : 'Unknown')}
                </td>
                <td className="px-6 py-3.5">
                  {getSeverityBadge(r.severity)}
                </td>
                <td className="px-6 py-3.5">
                  {getStatusText(r.verification_status)}
                </td>
                <td className="px-6 py-3.5 font-mono text-slate-500">
                  {formatTime(r.occurred_at || ('created_at' in r ? r.created_at : null))}
                </td>
                <td className="px-6 py-3.5 text-right">
                  <Link
                    to={`/track-report?id=${encodeURIComponent(r.tracking_id)}`}
                    className="font-semibold text-blue-600 hover:underline inline-flex items-center space-x-0.5"
                  >
                    <span>Inspect</span>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
