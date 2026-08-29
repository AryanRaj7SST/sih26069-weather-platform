import React, { useState } from 'react';
import { Image as ImageIcon, FileVideo, ExternalLink, AlertCircle } from 'lucide-react';
import { MediaDetail } from '@/types';

interface SubmittedEvidenceCardProps {
  media: MediaDetail[];
}

export const SubmittedEvidenceCard: React.FC<SubmittedEvidenceCardProps> = ({ media }) => {
  const [failedImages, setFailedImages] = useState<Record<string, boolean>>({});

  const handleImageError = (id: string) => {
    setFailedImages((prev) => ({ ...prev, [id]: true }));
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div className="flex items-center justify-between text-slate-700">
        <div className="flex items-center space-x-2">
          <ImageIcon className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Submitted Evidence</h3>
        </div>
        {media.length > 0 && (
          <span className="text-xs font-semibold text-slate-500">
            {media.length} {media.length === 1 ? 'item' : 'items'}
          </span>
        )}
      </div>

      {media.length === 0 ? (
        <p className="mt-3 text-xs text-slate-500">
          No photo or video evidence was attached to this report.
        </p>
      ) : (
        <div className="mt-3 grid grid-cols-2 gap-2.5">
          {media.map((item, idx) => {
            const isVideo = item.media_type === 'VIDEO';
            const isFailed = failedImages[item.id || idx];

            return (
              <a
                key={item.id || idx}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                title="Click to view full media"
                className="group relative overflow-hidden rounded-xl border border-slate-200 bg-slate-100 aspect-video flex items-center justify-center transition-all hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-600/30"
              >
                {isVideo ? (
                  <div className="flex flex-col items-center justify-center p-2 text-center text-slate-600">
                    <FileVideo className="h-8 w-8 text-blue-600" />
                    <span className="mt-1 font-mono text-[10px] text-slate-500">Video Evidence</span>
                  </div>
                ) : isFailed ? (
                  <div className="flex flex-col items-center justify-center p-2 text-center text-slate-400">
                    <AlertCircle className="h-6 w-6 text-slate-400 mb-1" />
                    <span className="font-mono text-[9px] text-slate-500">Preview Unavailable</span>
                  </div>
                ) : (
                  <img
                    src={item.url}
                    alt={`Evidence ${idx + 1}`}
                    loading="lazy"
                    crossOrigin="anonymous"
                    className="h-full w-full object-cover transition-transform group-hover:scale-105"
                    onError={() => handleImageError(item.id || String(idx))}
                  />
                )}

                <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900/60 rounded p-1 text-white">
                  <ExternalLink className="h-3 w-3" />
                </div>

                <div className="absolute bottom-1 right-1 rounded bg-slate-900/70 px-1.5 py-0.5 font-mono text-[9px] text-white">
                  IMG_{idx + 1}
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
};
