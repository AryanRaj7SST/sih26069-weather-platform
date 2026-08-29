// Accessible Empty State Card Component

import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description: string;
  icon?: LucideIcon;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Records Found',
  description,
  icon: Icon = Inbox,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-8 text-center ${className}`}
      role="region"
      aria-label={title}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-500 mb-3 shadow-2xs">
        <Icon className="h-6 w-6" aria-hidden="true" />
      </div>
      <h4 className="text-sm font-bold text-slate-800">{title}</h4>
      <p className="mt-1.5 text-xs text-slate-500 max-w-sm leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 inline-flex items-center rounded-xl bg-white px-4 py-2 text-xs font-bold text-blue-600 border border-slate-200 shadow-xs hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};
