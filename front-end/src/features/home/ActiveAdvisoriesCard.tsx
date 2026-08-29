import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface AdvisoryItem {
  id: string;
  type: string;
  title: string;
  location: string;
  severity: 'HIGH' | 'ELEVATED' | 'MODERATE';
  metricLabel: string;
  metricValue: string;
  progressPercent: number;
}

const SAMPLE_ADVISORIES: AdvisoryItem[] = [
  {
    id: 'adv-1',
    type: 'SEVERE WARNING',
    title: 'Severe Thunderstorm Watch',
    location: 'Mumbai, Maharashtra',
    severity: 'HIGH',
    metricLabel: 'Precipitation Rate',
    metricValue: '45 mm/hr',
    progressPercent: 80,
  },
  {
    id: 'adv-2',
    type: 'ADVISORY',
    title: 'Flash Flood Warning',
    location: 'Chennai, Tamil Nadu',
    severity: 'HIGH',
    metricLabel: 'Max Wind Gust',
    metricValue: '65 km/h',
    progressPercent: 65,
  },
  {
    id: 'adv-3',
    type: 'WATCH',
    title: 'Air Quality & Heatwave Alert',
    location: 'New Delhi, NCR',
    severity: 'ELEVATED',
    metricLabel: 'Peak Temperature',
    metricValue: '44°C',
    progressPercent: 88,
  },
];

export const ActiveAdvisoriesCard: React.FC = () => {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="h-5 w-5 text-rose-500" />
          <h2 className="text-lg font-bold text-slate-900">Active Advisory Summary</h2>
        </div>
        <span className="text-xs font-semibold text-slate-500">
          Regional Bulletins
        </span>
      </div>

      <div className="mt-4 space-y-4">
        {SAMPLE_ADVISORIES.map((item) => {
          const isHigh = item.severity === 'HIGH';

          return (
            <div
              key={item.id}
              className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 transition-all hover:bg-slate-50"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{item.title}</h3>
                  <p className="text-xs text-slate-500">{item.location}</p>
                </div>
                <span
                  className={`rounded px-2 py-0.5 text-[11px] font-bold ${
                    isHigh
                      ? 'bg-rose-100 text-rose-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {item.severity}
                </span>
              </div>

              {/* Metric bar */}
              <div className="mt-3">
                <div className="flex justify-between text-[11px] font-semibold text-slate-700">
                  <span>{item.metricLabel}</span>
                  <span className="font-mono">{item.metricValue}</span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                  <div
                    className={`h-full rounded-full ${
                      isHigh ? 'bg-rose-500' : 'bg-amber-500'
                    }`}
                    style={{ width: `${item.progressPercent}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
