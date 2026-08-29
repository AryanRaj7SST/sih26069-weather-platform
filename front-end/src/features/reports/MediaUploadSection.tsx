import React, { useRef, useState } from 'react';
import { Camera, UploadCloud, X, FileVideo, AlertCircle } from 'lucide-react';

interface MediaUploadSectionProps {
  mediaFiles: File[];
  setMediaFiles: React.Dispatch<React.SetStateAction<File[]>>;
}

const MAX_FILES = 3;
const MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024; // 15 MB
const ALLOWED_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'video/mp4',
  'video/quicktime',
];

export const MediaUploadSection: React.FC<MediaUploadSectionProps> = ({
  mediaFiles,
  setMediaFiles,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const validateAndAddFiles = (newFiles: FileList | File[]) => {
    setErrorMessage(null);
    const addedList: File[] = [];

    if (mediaFiles.length + newFiles.length > MAX_FILES) {
      setErrorMessage(`You can upload a maximum of ${MAX_FILES} media files.`);
      return;
    }

    for (let i = 0; i < newFiles.length; i++) {
      const file = newFiles[i];

      if (!ALLOWED_TYPES.includes(file.type)) {
        setErrorMessage(`"${file.name}" has an unsupported format. Please upload JPEG, PNG, WEBP, or MP4.`);
        return;
      }

      if (file.size > MAX_FILE_SIZE_BYTES) {
        setErrorMessage(`"${file.name}" exceeds the 15MB file size limit.`);
        return;
      }

      addedList.push(file);
    }

    setMediaFiles((prev) => [...prev, ...addedList]);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndAddFiles(e.target.files);
      e.target.value = ''; // Reset input
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAddFiles(e.dataTransfer.files);
    }
  };

  const handleRemoveFile = (indexToRemove: number) => {
    setMediaFiles((prev) => prev.filter((_, idx) => idx !== indexToRemove));
    setErrorMessage(null);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center space-x-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <Camera className="h-5 w-5" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Upload Photo or Video</h2>
      </div>

      {/* Dashed Dropzone */}
      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`mt-5 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 transition-all text-center ${
          dragOver
            ? 'border-blue-600 bg-blue-50/50'
            : 'border-slate-300 bg-slate-50/40 hover:border-blue-500 hover:bg-slate-50'
        }`}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100/80 text-blue-600 mb-3">
          <UploadCloud className="h-6 w-6" />
        </div>
        <p className="text-sm font-semibold text-slate-900">
          Tap to upload or drag & drop
        </p>
        <p className="mt-1 text-xs text-slate-500">
          JPEG, PNG, MP4 up to 15MB (max 3 files)
        </p>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* Error alert */}
      {errorMessage && (
        <div className="mt-3 flex items-center space-x-2 rounded-lg bg-rose-50 p-2.5 text-xs font-medium text-rose-800 border border-rose-200">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Attached Files List */}
      {mediaFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          {mediaFiles.map((file, idx) => {
            const isVideo = file.type.startsWith('video/');
            const previewUrl = URL.createObjectURL(file);

            return (
              <div
                key={`${file.name}-${idx}`}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-2.5"
              >
                <div className="flex items-center space-x-3 overflow-hidden">
                  {isVideo ? (
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-slate-200 text-slate-600">
                      <FileVideo className="h-5 w-5" />
                    </div>
                  ) : (
                    <img
                      src={previewUrl}
                      alt={file.name}
                      className="h-10 w-10 shrink-0 rounded object-cover border border-slate-200"
                    />
                  )}
                  <div className="truncate">
                    <p className="truncate text-xs font-semibold text-slate-900">
                      {file.name}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFile(idx);
                  }}
                  className="rounded-md p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700"
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
