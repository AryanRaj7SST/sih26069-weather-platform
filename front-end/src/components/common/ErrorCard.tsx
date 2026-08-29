// Accessible Error Alert Card Component with Retry Action

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorCardProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorCard: React.FC<ErrorCardProps> = ({
  title = 'Service Notice',
  message = 'Failed to load telemetry data. Please check your connectivity and retry.',
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`rounded-2xl border border-rose-200 bg-rose-50/70 p-5 text-rose-900 shadow-xs ${className}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start space-x-3">
        <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" aria-hidden="true" />
        <div className="flex-1">
          <h4 className="text-xs font-bold uppercase tracking-wider text-rose-950">{title}</h4>
          <p className="mt-1 text-xs text-rose-800 leading-relaxed">{message}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center space-x-1.5 rounded-xl bg-white px-3 py-1.5 text-xs font-bold text-rose-700 border border-rose-200 shadow-2xs hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-rose-500 transition-colors"
            >
              <RefreshCw className="h-3 w-3" aria-hidden="true" />
              <span>Retry Request</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
