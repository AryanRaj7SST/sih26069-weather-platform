import React from 'react';
import { CloudRain, Droplets, Wind } from 'lucide-react';
import { Link } from 'react-router-dom';

interface VerifiedReportItem {
  id: string;
  type: string;
  location: string;
  timeUTC: string;
  icon: 'hail' | 'rain' | 'wind';
}

const RECENT_REPORTS: VerifiedReportItem[] = [
  {
    id: 'rpt-1',
    type: 'Hail (1.5")',
    location: 'Guwahati, Assam',
    timeUTC: '14:32',
    icon: 'hail',
  },
  {
    id: 'rpt-2',
    type: 'Heavy Rain',
    location: 'Kochi, Kerala',
    timeUTC: '13:15',
    icon: 'rain',
  },
  {
    id: 'rpt-3',
    type: 'High Wind (55mph)',
    location: 'Jaipur, Rajasthan',
    timeUTC: '12:45',
    icon: 'wind',
  },
];

export const RecentReportsTable: React.FC = () => {
  const getIcon = (type: string) => {
    switch (type) {
      case 'hail':
        return <CloudRain className="h-4 w-4 text-sky-600" />;
      case 'rain':
        return <Droplets className="h-4 w-4 text-blue-600" />;
      case 'wind':
      default:
        return <Wind className="h-4 w-4 text-teal-600" />;
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <h2 className="text-lg font-bold text-slate-900">Recent Verified Reports</h2>
        <Link
          to="/track-report"
          className="text-xs font-semibold text-blue-600 hover:text-blue-700"
        >
          View All
        </Link>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase tracking-wider">
              <th className="pb-2.5 font-medium">Type</th>
              <th className="pb-2.5 font-medium">Location</th>
              <th className="pb-2.5 font-medium text-right">Time (UTC)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {RECENT_REPORTS.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="py-3">
                  <div className="flex items-center space-x-2">
                    {getIcon(item.icon)}
                    <span className="font-semibold text-slate-800">{item.type}</span>
                  </div>
                </td>
                <td className="py-3 text-slate-600 font-medium">{item.location}</td>
                <td className="py-3 text-right font-mono text-slate-500">{item.timeUTC}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
