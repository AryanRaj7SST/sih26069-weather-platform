import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { ReportDetailData } from '@/types';
import { Activity } from 'lucide-react';

interface ReportActivityChartProps {
  reports: ReportDetailData[];
  timeRange: string;
  isLoading: boolean;
}

export const ReportActivityChart: React.FC<ReportActivityChartProps> = ({
  reports,
  timeRange,
  isLoading,
}) => {
  const chartData = useMemo(() => {
    if (reports.length === 0) return [];

    const now = new Date();

    if (timeRange === '24h') {
      // 6 time buckets (4-hour intervals)
      const buckets: Record<string, { label: string; total: number; verified: number }> = {
        '00:00': { label: '00:00 - 04:00', total: 0, verified: 0 },
        '04:00': { label: '04:00 - 08:00', total: 0, verified: 0 },
        '08:00': { label: '08:00 - 12:00', total: 0, verified: 0 },
        '12:00': { label: '12:00 - 16:00', total: 0, verified: 0 },
        '16:00': { label: '16:00 - 20:00', total: 0, verified: 0 },
        '20:00': { label: '20:00 - 24:00', total: 0, verified: 0 },
      };

      for (const r of reports) {
        const d = new Date(r.occurred_at || r.created_at);
        const hour = d.getHours();
        const isVerified = r.verification_status === 'VERIFIED';

        let key = '00:00';
        if (hour >= 20) key = '20:00';
        else if (hour >= 16) key = '16:00';
        else if (hour >= 12) key = '12:00';
        else if (hour >= 8) key = '08:00';
        else if (hour >= 4) key = '04:00';

        buckets[key].total++;
        if (isVerified) buckets[key].verified++;
      }

      return Object.entries(buckets).map(([time, data]) => ({
        time,
        label: data.label,
        total: data.total,
        verified: data.verified,
      }));
    }

    // Default for 7d, 30d, all: Daily buckets (Last 7 days or matching days)
    const dayCount = timeRange === '30d' ? 14 : 7;
    const daysMap: Record<string, { time: string; label: string; total: number; verified: number }> = {};

    for (let i = dayCount - 1; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
      const dateKey = d.toISOString().split('T')[0];
      const shortDay = d.toLocaleDateString([], { weekday: 'short', day: 'numeric' });
      daysMap[dateKey] = {
        time: shortDay,
        label: d.toLocaleDateString([], { month: 'short', day: 'numeric' }),
        total: 0,
        verified: 0,
      };
    }

    for (const r of reports) {
      const dateKey = (r.occurred_at || r.created_at).split('T')[0];
      const isVerified = r.verification_status === 'VERIFIED';

      if (daysMap[dateKey]) {
        daysMap[dateKey].total++;
        if (isVerified) daysMap[dateKey].verified++;
      } else {
        // Fallback for days outside generated map
        const d = new Date(r.occurred_at || r.created_at);
        const shortDay = d.toLocaleDateString([], { month: 'short', day: 'numeric' });
        daysMap[dateKey] = {
          time: shortDay,
          label: shortDay,
          total: 1,
          verified: isVerified ? 1 : 0,
        };
      }
    }

    return Object.values(daysMap);
  }, [reports, timeRange]);

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm animate-pulse">
        <div className="h-4 w-48 bg-slate-200 rounded mb-4" />
        <div className="h-64 w-full bg-slate-100 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      {/* Header with Title & Legend */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            Report Activity Over Time
          </h2>
          <p className="text-xs text-slate-500">
            Report volume grouped by time period ({reports.length} total reports analyzed)
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-4 text-xs font-semibold text-slate-600">
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-blue-200" />
            <span>Total Reports</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-blue-600" />
            <span>Verified Reports</span>
          </div>
        </div>
      </div>

      {/* Recharts Bar Chart */}
      <div className="h-64 sm:h-72 w-full pt-2">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              barGap={4}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 11, fill: '#64748b' }}
                axisLine={{ stroke: '#e2e8f0' }}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-lg text-xs space-y-1">
                        <p className="font-bold text-slate-900">{data.label || data.time}</p>
                        <p className="text-blue-600 font-semibold">
                          Total Reports: <span className="font-bold">{data.total}</span>
                        </p>
                        <p className="text-emerald-600 font-semibold">
                          Verified: <span className="font-bold">{data.verified}</span>
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              {/* Total Reports Bar (Light Blue) */}
              <Bar
                dataKey="total"
                fill="#93c5fd"
                radius={[4, 4, 0, 0]}
                maxBarSize={28}
              />
              {/* Verified Reports Bar (Dark Blue) */}
              <Bar
                dataKey="verified"
                fill="#2563eb"
                radius={[4, 4, 0, 0]}
                maxBarSize={28}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full flex-col items-center justify-center text-slate-400">
            <Activity className="h-8 w-8 mb-2 stroke-1" />
            <p className="text-xs font-medium">No report activity recorded in this period</p>
          </div>
        )}
      </div>
    </div>
  );
};
