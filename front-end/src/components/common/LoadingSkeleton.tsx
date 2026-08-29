// Reusable Accessible Loading Skeleton Component

import React from 'react';

interface LoadingSkeletonProps {
  className?: string;
  count?: number;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ className = 'h-24 w-full', count = 1 }) => {
  return (
    <div className="space-y-3" role="status" aria-label="Loading content...">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`rounded-2xl bg-slate-100/90 animate-pulse border border-slate-200/60 ${className}`}
        />
      ))}
      <span className="sr-only">Loading...</span>
    </div>
  );
};
