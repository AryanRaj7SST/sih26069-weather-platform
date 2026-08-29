import React, { useState } from 'react';
import { MapPin, LocateFixed, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { UseFormReturn } from 'react-hook-form';
import { CitizenReportFormValues } from '@/types';

interface LocationSectionProps {
  form: UseFormReturn<CitizenReportFormValues>;
}

export const LocationSection: React.FC<LocationSectionProps> = ({ form }) => {
  const { register, setValue, watch, formState: { errors } } = form;
  const latitude = watch('latitude');
  const longitude = watch('longitude');

  const [geoStatus, setGeoStatus] = useState<'idle' | 'locating' | 'success' | 'error'>('idle');
  const [geoMessage, setGeoMessage] = useState<string>('');

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGeoStatus('error');
      setGeoMessage('Geolocation is not supported by your browser.');
      return;
    }

    setGeoStatus('locating');
    setGeoMessage('Detecting GPS location...');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = parseFloat(position.coords.latitude.toFixed(6));
        const lon = parseFloat(position.coords.longitude.toFixed(6));

        setValue('latitude', lat, { shouldValidate: true });
        setValue('longitude', lon, { shouldValidate: true });

        setGeoStatus('success');
        setGeoMessage(`GPS Acquired: ${lat}° N, ${lon}° E (±${Math.round(position.coords.accuracy)}m)`);
      },
      (error) => {
        setGeoStatus('error');
        switch (error.code) {
          case error.PERMISSION_DENIED:
            setGeoMessage('Location permission denied. Please enter locality manually.');
            break;
          case error.POSITION_UNAVAILABLE:
            setGeoMessage('Location information is unavailable. Please enter locality.');
            break;
          case error.TIMEOUT:
            setGeoMessage('Location request timed out. Please try again.');
            break;
          default:
            setGeoMessage('Could not retrieve location. Please enter manually.');
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  };

  const hasCoordinates = typeof latitude === 'number' && !isNaN(latitude) && typeof longitude === 'number' && !isNaN(longitude);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm transition-all">
      {/* Header */}
      <div className="flex items-center space-x-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <MapPin className="h-5 w-5" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Where did this happen?</h2>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Left Column: Form Controls */}
        <div className="flex flex-col justify-between space-y-4">
          <div>
            <label
              htmlFor="location_name"
              className="block text-sm font-semibold text-slate-700"
            >
              Locality / Landmark
            </label>
            <div className="relative mt-1.5">
              <input
                id="location_name"
                type="text"
                {...register('location_name')}
                placeholder="e.g., Marine Drive, Mumbai"
                className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20"
              />
            </div>
          </div>

          <div className="relative flex items-center justify-center">
            <div className="w-full border-t border-slate-200" />
            <span className="absolute bg-white px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
              OR
            </span>
          </div>

          <div>
            <button
              type="button"
              onClick={handleUseCurrentLocation}
              disabled={geoStatus === 'locating'}
              className="flex w-full items-center justify-center space-x-2 rounded-lg border-2 border-blue-600 bg-white px-4 py-2.5 text-sm font-semibold text-blue-600 transition-colors hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-600/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {geoStatus === 'locating' ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  <span>Acquiring GPS...</span>
                </>
              ) : (
                <>
                  <LocateFixed className="h-4 w-4 text-blue-600" />
                  <span>Use Current Location</span>
                </>
              )}
            </button>

            {/* GPS Feedback message */}
            {geoStatus === 'success' && (
              <div className="mt-2.5 flex items-center space-x-2 rounded-md bg-emerald-50 p-2 text-xs font-medium text-emerald-800 border border-emerald-200">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                <span>{geoMessage}</span>
              </div>
            )}

            {geoStatus === 'error' && (
              <div className="mt-2.5 flex items-center space-x-2 rounded-md bg-amber-50 p-2 text-xs font-medium text-amber-800 border border-amber-200">
                <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
                <span>{geoMessage}</span>
              </div>
            )}

            {/* Hidden / Bound coordinate inputs */}
            <input type="hidden" {...register('latitude', { valueAsNumber: true })} />
            <input type="hidden" {...register('longitude', { valueAsNumber: true })} />

            {(errors.latitude || errors.longitude) && (
              <p className="mt-1.5 text-xs font-medium text-rose-600">
                Please provide location or use GPS to record coordinates.
              </p>
            )}
          </div>
        </div>

        {/* Right Column: Visual Location Preview (Matching Stitch Reference) */}
        <div className="relative min-h-[160px] overflow-hidden rounded-xl border border-slate-200 bg-slate-100 flex flex-col items-center justify-center p-4">
          <div className="absolute inset-0 bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] [background-size:16px_16px] opacity-70" />

          {hasCoordinates ? (
            <div className="relative z-10 flex flex-col items-center text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white shadow-md">
                <MapPin className="h-6 w-6 animate-bounce" />
              </div>
              <p className="mt-2 text-sm font-bold text-slate-900">
                {watch('location_name') || 'Selected Location'}
              </p>
              <p className="font-mono text-xs text-slate-600 bg-white/90 px-2 py-0.5 rounded border border-slate-200 mt-1">
                {latitude?.toFixed(4)}° N, {longitude?.toFixed(4)}° E
              </p>
            </div>
          ) : (
            <div className="relative z-10 flex flex-col items-center text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-200 text-slate-500">
                <MapPin className="h-5 w-5" />
              </div>
              <p className="mt-2 text-xs font-medium text-slate-600">
                Location pin will appear here once GPS or landmark is confirmed.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
