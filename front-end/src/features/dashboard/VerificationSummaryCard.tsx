import React, { useMemo } from 'react';
import { ShieldCheck } from 'lucide-react';
import { ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { ReportDetailData } from '@/types';

interface VerificationSummaryCardProps {
  reports: ReportDetailData[];
  isLoading: boolean;
}

export const VerificationSummaryCard: React.FC<VerificationSummaryCardProps> = ({
  reports,
  isLoading,
}) => {
  const stats = useMemo(() => {
    let verified = 0;
    let pending = 0;
    let rejected = 0;

    for (const report of reports) {
      if (report.verification_status === 'VERIFIED') {
        verified++;
      } else if (report.verification_status === 'REJECTED') {
        rejected++;
      } else {
        pending++;
      }
    }

    const total = reports.length;
    const verifiedPct = total > 0 ? Math.round((verified / total) * 100) : 0;

    const data = [
      { name: 'Verified', value: verified, color: '#10b981' },
      { name: 'Pending / Review', value: pending, color: '#f59e0b' },
      { name: 'Rejected', value: rejected, color: '#94a3b8' },
    ].filter((item) => item.value > 0);

    return {
      verified,
      pending,
      rejected,
      total,
      verifiedPct,
      data: data.length > 0 ? data : [{ name: 'None', value: 1, color: '#e2e8f0' }],
    };
  }, [reports]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col justify-between">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Verification Status</h3>
        </div>
        <span className="text-[11px] text-slate-400 font-medium">By Authority</span>
      </div>

      <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Donut Chart with Center Percentage */}
        <div className="relative h-32 w-32 shrink-0">
          {isLoading ? (
            <div className="h-full w-full rounded-full bg-slate-100 animate-pulse" />
          ) : (
            <>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={stats.data}
                    innerRadius={38}
                    outerRadius={54}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {stats.data.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-xl font-extrabold text-slate-900 font-mono">
                  {stats.verifiedPct}%
                </span>
                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                  Verified
                </span>
              </div>
            </>
          )}
        </div>

        {/* Legend Table */}
        <div className="flex-1 w-full space-y-2 text-xs">
          <div className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-1.5">
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="font-semibold text-slate-700">Verified</span>
            </div>
            <span className="font-bold text-slate-900 font-mono">{stats.verified}</span>
          </div>

          <div className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-1.5">
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              <span className="font-semibold text-slate-700">Pending Review</span>
            </div>
            <span className="font-bold text-slate-900 font-mono">{stats.pending}</span>
          </div>

          <div className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-1.5">
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-slate-400" />
              <span className="font-semibold text-slate-700">Rejected</span>
            </div>
            <span className="font-bold text-slate-900 font-mono">{stats.rejected}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
