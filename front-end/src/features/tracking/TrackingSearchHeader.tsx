import React, { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';

interface TrackingSearchHeaderProps {
  initialTrackingId?: string;
  onSearch: (trackingId: string) => void;
  isLoading: boolean;
}

export const TrackingSearchHeader: React.FC<TrackingSearchHeaderProps> = ({
  initialTrackingId = '',
  onSearch,
  isLoading,
}) => {
  const [trackingInput, setTrackingInput] = useState(initialTrackingId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = trackingInput.trim();
    if (cleanId) {
      onSearch(cleanId);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
            <Search className="h-5 w-5" />
          </div>
          <input
            type="text"
            value={trackingInput}
            onChange={(e) => setTrackingInput(e.target.value)}
            placeholder="e.g. RPT-20260829-K8L9"
            aria-label="Tracking ID or Incident ID"
            className="w-full rounded-xl border border-slate-300 bg-white pl-10 pr-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 shadow-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 uppercase tracking-wide font-mono"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || !trackingInput.trim()}
          className="flex items-center justify-center space-x-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-bold text-white shadow-md transition-all hover:bg-blue-700 hover:shadow-blue-600/30 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Tracking...</span>
            </>
          ) : (
            <span>Track Report</span>
          )}
        </button>
      </form>
    </div>
  );
};
