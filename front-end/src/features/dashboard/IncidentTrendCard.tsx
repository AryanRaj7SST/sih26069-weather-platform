import React, { useMemo } from 'react';
import { TrendingUp } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { DiurnalDistributionItem, ReportDetailData } from '@/types';

interface IncidentTrendCardProps {
  distribution?: DiurnalDistributionItem[];
  reports?: ReportDetailData[];
  isLoading: boolean;
}

export const IncidentTrendCard: React.FC<IncidentTrendCardProps> = ({
  distribution,
  reports = [],
  isLoading,
}) => {
  const chartData = useMemo(() => {
    if (distribution && distribution.length > 0) {
      return distribution.map((item) => ({
        time: item.window,
        label: item.label,
        count: item.count,
      }));
    }

    // Fallback: Group reports into 4 standard daily time intervals (00:00, 06:00, 12:00, 18:00)
    const buckets: Record<string, number> = {
      '00:00': 0,
      '06:00': 0,
      '12:00': 0,
      '18:00': 0,
    };

    for (const report of reports) {
      const dateStr = report.occurred_at || report.created_at;
      if (dateStr) {
        const d = new Date(dateStr);
        if (!isNaN(d.getTime())) {
          const hour = d.getHours();
          if (hour < 6) buckets['00:00']++;
          else if (hour < 12) buckets['06:00']++;
          else if (hour < 18) buckets['12:00']++;
          else buckets['18:00']++;
        }
      }
    }

    return Object.entries(buckets).map(([time, count]) => ({
      time,
      count,
    }));
  }, [distribution, reports]);

  const hasData = chartData.some((item) => item.count > 0);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col justify-between">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2">
          <TrendingUp className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Incident Trends</h3>
        </div>
        <span className="text-[11px] text-slate-400 font-medium">By Hour of Day</span>
      </div>

      <div className="h-44 w-full mt-4">
        {isLoading ? (
          <div className="h-full w-full flex items-center justify-center bg-slate-50 rounded-xl animate-pulse">
            <span className="text-xs text-slate-400">Loading trends...</span>
          </div>
        ) : !hasData ? (
          <div className="h-full w-full flex items-center justify-center bg-slate-50/50 rounded-xl text-center p-4">
            <span className="text-xs text-slate-400 font-medium">No incident data available for selected filters.</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis
                dataKey="time"
                stroke="#94a3b8"
                fontSize={10}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                stroke="#94a3b8"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
              />
              <Tooltip
                cursor={{ fill: '#f8fafc' }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const row = payload[0].payload as { time: string; label?: string; count: number };
                    return (
                      <div className="rounded-lg border border-slate-200 bg-white p-2 shadow-md text-xs">
                        <span className="font-semibold text-slate-700">
                          {row.label || `${row.time} Window`}
                        </span>
                        <div className="text-blue-600 font-bold mt-0.5">
                          {payload[0].value} {Number(payload[0].value) === 1 ? 'Report' : 'Reports'}
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar
                dataKey="count"
                fill="#93c5fd"
                activeBar={{ fill: '#2563eb' }}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
