import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  MapContainer,
  TileLayer,
  Marker,
  Polyline,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  RefreshCw,
  Compass,
  Thermometer,
  CloudRain,
  Wind,
  Gauge,
  Waves,
  MapPin,
  Scale,
} from "lucide-react";

import { useLocationScope } from "@/hooks";
import {
  fetchWeatherPoint,
  fetchWeatherLiveCheck,
  HourlyForecastItem,
  WeatherPointResponse,
  WeatherLiveCheckResponse,
} from "@/services/weatherGridApi";

// Custom Leaflet DivIcon helpers
const targetIcon = L.divIcon({
  className: "custom-target-marker",
  html: `
    <div class="relative flex items-center justify-center">
      <span class="animate-ping absolute inline-flex h-6 w-6 rounded-full bg-blue-400 opacity-60"></span>
      <span class="relative inline-flex rounded-full h-4 w-4 bg-blue-600 border-2 border-white shadow-md"></span>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const gridIcon = L.divIcon({
  className: "custom-grid-marker",
  html: `
    <div class="relative flex items-center justify-center">
      <span class="relative inline-flex rounded-full h-4 w-4 bg-indigo-600 border-2 border-white shadow-md"></span>
    </div>
  `,
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});

// Map click listener component
function MapEvents({ onLocationSelect }: { onLocationSelect: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onLocationSelect(
        Number(e.latlng.lat.toFixed(4)),
        Number(e.latlng.lng.toFixed(4))
      );
    },
  });
  return null;
}

// Map center controller
function MapRecenter({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lon], map.getZoom(), { animate: true });
  }, [lat, lon, map]);
  return null;
}

// Numerical delta formatting helpers
function parseUtcTimestamp(isoString: string | null | undefined): number {
  if (!isoString) return NaN;
  // If string does not have timezone offset (+XX:XX or -XX:XX) or Z, treat as UTC by appending Z
  const hasTimezone = isoString.endsWith("Z") || /[+-]\d{2}:?\d{2}$/.test(isoString);
  const normalized = hasTimezone ? isoString : `${isoString}Z`;
  return new Date(normalized).getTime();
}

function formatUtcHour(isoString: string): string {
  try {
    const epoch = parseUtcTimestamp(isoString);
    if (isNaN(epoch)) return isoString.substring(11, 16) || isoString;
    const d = new Date(epoch);
    const hours = String(d.getUTCHours()).padStart(2, "0");
    const minutes = String(d.getUTCMinutes()).padStart(2, "0");
    return `${hours}:${minutes}`;
  } catch {
    return isoString.substring(11, 16) || isoString;
  }
}

function formatDelta(diff: number | null, unit: string = ""): { text: string; isZero: boolean } {
  if (diff === null || isNaN(diff)) return { text: "—", isZero: true };
  const absVal = Math.abs(diff);
  if (absVal < 0.001) return { text: `0.0${unit}`, isZero: true };
  const sign = diff > 0 ? "+" : "";
  return { text: `${sign}${diff.toFixed(2)}${unit}`, isZero: false };
}

export const SourceParityPage: React.FC = () => {
  const { currentLocation } = useLocationScope();

  // Selected coordinates (default to user's city)
  const defaultLat = currentLocation?.lat ?? 19.076;
  const defaultLon = currentLocation?.lon ?? 72.877;

  const [inputLat, setInputLat] = useState<number>(defaultLat);
  const [inputLon, setInputLon] = useState<number>(defaultLon);
  const [activeLat, setActiveLat] = useState<number>(defaultLat);
  const [activeLon, setActiveLon] = useState<number>(defaultLon);

  // Sync with user's detected location on initial load if not modified
  useEffect(() => {
    if (currentLocation?.lat && currentLocation?.lon) {
      setInputLat(currentLocation.lat);
      setInputLon(currentLocation.lon);
      setActiveLat(currentLocation.lat);
      setActiveLon(currentLocation.lon);
    }
  }, [currentLocation]);

  const handleApplyCoordinates = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setActiveLat(inputLat);
    setActiveLon(inputLon);
  };

  const handleResetToCity = () => {
    if (currentLocation?.lat && currentLocation?.lon) {
      setInputLat(currentLocation.lat);
      setInputLon(currentLocation.lon);
      setActiveLat(currentLocation.lat);
      setActiveLon(currentLocation.lon);
    }
  };

  const handleMapSelect = useCallback((lat: number, lon: number) => {
    setInputLat(lat);
    setInputLon(lon);
    setActiveLat(lat);
    setActiveLon(lon);
  }, []);

  // Query Stored Forecast from /api/v1/weather/point
  const {
    data: storedData,
    isLoading: isStoredLoading,
    isError: isStoredError,
    error: storedError,
    refetch: refetchStored,
  } = useQuery<WeatherPointResponse>({
    queryKey: ["weather-point", activeLat, activeLon],
    queryFn: () => fetchWeatherPoint(activeLat, activeLon),
    staleTime: 60_000,
    retry: 1,
  });

  // Query Live Open-Meteo Server-Side from /api/v1/weather/live-check
  const {
    data: liveData,
    isLoading: isLiveLoading,
    isError: isLiveError,
    error: liveError,
    refetch: refetchLive,
  } = useQuery<WeatherLiveCheckResponse>({
    queryKey: ["weather-live-check", activeLat, activeLon],
    queryFn: () => fetchWeatherLiveCheck(activeLat, activeLon),
    staleTime: 60_000,
    retry: 1,
  });

  const isLoading = isStoredLoading || isLiveLoading;

  // Align next 24 hours of data between Stored and Live
  const { alignedRows, parityAnalysis } = useMemo(() => {
    if (!storedData?.hourly || !liveData?.hourly) {
      return { alignedRows: [], parityAnalysis: null };
    }

    const liveMap = new Map<string, HourlyForecastItem>();
    liveData.hourly.forEach((item) => {
      // Key by YYYY-MM-DDTHH:MM
      const key = item.valid_time.substring(0, 16);
      liveMap.set(key, item);
    });

    // Closest hour to now in UTC
    const nowMs = Date.now();
    const closestUtc = new Date(nowMs);
    if (closestUtc.getUTCMinutes() >= 30) {
      closestUtc.setUTCHours(closestUtc.getUTCHours() + 1);
    }
    closestUtc.setUTCMinutes(0, 0, 0);
    const closestUtcHm = closestUtc.getTime();

    // Find the item in storedData.hourly closest to closestUtcHm
    let startIndex = 0;
    let minDistance = Infinity;
    storedData.hourly.forEach((item, idx) => {
      const itemUtc = parseUtcTimestamp(item.valid_time);
      const dist = Math.abs(itemUtc - closestUtcHm);
      if (dist < minDistance) {
        minDistance = dist;
        startIndex = idx;
      }
    });

    let next24Stored: HourlyForecastItem[];
    if (startIndex + 24 <= storedData.hourly.length) {
      next24Stored = storedData.hourly.slice(startIndex, startIndex + 24);
    } else if (storedData.hourly.length >= 24) {
      next24Stored = storedData.hourly.slice(storedData.hourly.length - 24);
    } else {
      next24Stored = storedData.hourly.slice(startIndex);
    }

    let maxTempDiff = 0;
    let maxPrecipDiff = 0;
    let maxWindDiff = 0;
    let maxPressDiff = 0;
    let maxWaveDiff = 0;
    let anyExceedsTolerance = false;
    let mismatchCount = 0;

    const rows = next24Stored.map((sItem) => {
      const key = sItem.valid_time.substring(0, 16);
      const lItem = liveMap.get(key);
      const rowUtc = parseUtcTimestamp(sItem.valid_time);
      const isEarlierToday = !isNaN(rowUtc) && rowUtc < closestUtcHm;

      const dTemp = lItem?.temperature_2m != null && sItem.temperature_2m != null
        ? Number((lItem.temperature_2m - sItem.temperature_2m).toFixed(2))
        : null;
      const dPrecip = lItem?.precipitation != null && sItem.precipitation != null
        ? Number((lItem.precipitation - sItem.precipitation).toFixed(2))
        : null;
      const dWind = lItem?.wind_speed_10m != null && sItem.wind_speed_10m != null
        ? Number((lItem.wind_speed_10m - sItem.wind_speed_10m).toFixed(2))
        : null;
      const dPress = lItem?.pressure_msl != null && sItem.pressure_msl != null
        ? Number((lItem.pressure_msl - sItem.pressure_msl).toFixed(2))
        : null;
      const dWave = lItem?.wave_height != null && sItem.wave_height != null
        ? Number((lItem.wave_height - sItem.wave_height).toFixed(2))
        : null;

      if (dTemp !== null) maxTempDiff = Math.max(maxTempDiff, Math.abs(dTemp));
      if (dPrecip !== null) maxPrecipDiff = Math.max(maxPrecipDiff, Math.abs(dPrecip));
      if (dWind !== null) maxWindDiff = Math.max(maxWindDiff, Math.abs(dWind));
      if (dPress !== null) maxPressDiff = Math.max(maxPressDiff, Math.abs(dPress));
      if (dWave !== null) maxWaveDiff = Math.max(maxWaveDiff, Math.abs(dWave));

      // Strict tolerances: Temp 0.5°C, Precip 0.5mm, Wind 2.0km/h, Press 1.0hPa, Wave 0.2m
      const isMismatch =
        (dTemp !== null && Math.abs(dTemp) > 0.5) ||
        (dPrecip !== null && Math.abs(dPrecip) > 0.5) ||
        (dWind !== null && Math.abs(dWind) > 2.0) ||
        (dPress !== null && Math.abs(dPress) > 1.0) ||
        (dWave !== null && Math.abs(dWave) > 0.2);

      if (isMismatch) {
        anyExceedsTolerance = true;
        mismatchCount++;
      }

      return {
        valid_time: sItem.valid_time,
        stored: sItem,
        live: lItem,
        diffs: {
          dTemp,
          dPrecip,
          dWind,
          dPress,
          dWave,
        },
        isMismatch,
        isEarlierToday,
      };
    });

    // Check age of stored forecast strictly from fetched_at (parsed as UTC)
    const storedEpoch = parseUtcTimestamp(storedData.fetched_at);
    const ageHours = !isNaN(storedEpoch) && storedEpoch <= nowMs
      ? (nowMs - storedEpoch) / (1000 * 3600)
      : 0;
    const isOldData = ageHours > 6.0;

    const exceededVars: string[] = [];
    if (maxTempDiff > 0.5) exceededVars.push("temperature");
    if (maxPrecipDiff > 0.5) exceededVars.push("precipitation");
    if (maxWindDiff > 2.0) exceededVars.push("wind speed");
    if (maxPressDiff > 1.0) exceededVars.push("pressure");
    if (maxWaveDiff > 0.2) exceededVars.push("wave height");

    let badgeType: "green" | "amber" = "green";
    let badgeReason = "Parity Verified: Stored platform forecast matches live upstream Open-Meteo run within strict tolerance.";

    if (isOldData) {
      badgeType = "amber";
      badgeReason = "Stored data is older than 6 hours and may predate the latest upstream update.";
    } else if (anyExceedsTolerance) {
      badgeType = "amber";
      const varsText = exceededVars.length > 0 ? exceededVars.join(", ") : "model variables";
      badgeReason = `Model variance exceeds tolerance in: ${varsText}.`;
    }

    return {
      alignedRows: rows,
      parityAnalysis: {
        badgeType,
        badgeReason,
        ageHours,
        maxTempDiff,
        maxPrecipDiff,
        maxWindDiff,
        maxPressDiff,
        maxWaveDiff,
        mismatchCount,
      },
    };
  }, [storedData, liveData]);

  const gridLat = storedData?.grid_latitude ?? liveData?.grid_latitude;
  const gridLon = storedData?.grid_longitude ?? liveData?.grid_longitude;
  const distanceKm = storedData?.distance_km ?? liveData?.distance_km ?? 0;
  const isSea = liveData?.is_sea ?? false;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="flex items-center space-x-2 text-blue-400 text-sm font-semibold tracking-wide uppercase">
              <Scale className="h-4 w-4" />
              <span>Data Provenance & Assurance</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mt-1">
              Source Parity Verification
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Compare numerical forecast grid cells stored in PostgreSQL against live server-side Open-Meteo API queries to ensure data integrity and detect model run drift.
            </p>
          </div>

          <div className="flex items-center space-x-3 shrink-0">
            <button
              type="button"
              onClick={() => {
                refetchStored();
                refetchLive();
              }}
              disabled={isLoading}
              className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-blue-400" : ""}`} />
              <span>Re-check Parity</span>
            </button>
          </div>
        </div>

        {/* Top Grid: Interactive Map + Coordinate Inspector */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Map Card */}
          <div className="lg:col-span-7 bg-slate-800/80 rounded-2xl border border-slate-700/80 p-4 shadow-xl flex flex-col space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold flex items-center space-x-1.5">
                <MapPin className="h-3.5 w-3.5 text-blue-400" />
                <span>Click map to inspect any coordinate in India & EEZ domain</span>
              </span>
              <span className="bg-slate-900/60 px-2 py-0.5 rounded border border-slate-700/60 text-[11px]">
                Lat 0–40, Lon 60–100
              </span>
            </div>

            <div className="relative h-64 sm:h-72 w-full rounded-xl overflow-hidden border border-slate-700/60 z-0">
              <MapContainer
                center={[activeLat, activeLon]}
                zoom={6}
                scrollWheelZoom={false}
                className="h-full w-full"
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <MapEvents onLocationSelect={handleMapSelect} />
                <MapRecenter lat={activeLat} lon={activeLon} />

                {/* Target Marker */}
                <Marker position={[activeLat, activeLon]} icon={targetIcon} />

                {/* Snapped Grid Point Marker & Connection Line */}
                {gridLat != null && gridLon != null && (
                  <>
                    <Marker position={[gridLat, gridLon]} icon={gridIcon} />
                    <Polyline
                      positions={[
                        [activeLat, activeLon],
                        [gridLat, gridLon],
                      ]}
                      pathOptions={{ color: "#6366f1", dashArray: "4, 6", weight: 2 }}
                    />
                  </>
                )}
              </MapContainer>

              {/* Legend overlay */}
              <div className="absolute bottom-2 left-2 bg-slate-900/85 backdrop-blur-md px-2.5 py-1.5 rounded-lg border border-slate-700/80 text-[11px] flex items-center space-x-3 z-[1000]">
                <div className="flex items-center space-x-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-blue-500 inline-block"></span>
                  <span className="text-slate-300">Clicked Location</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-indigo-500 inline-block"></span>
                  <span className="text-slate-300">Nearest Grid Cell</span>
                </div>
              </div>
            </div>
          </div>

          {/* Coordinate Form & Snapping Summary Card */}
          <div className="lg:col-span-5 bg-slate-800/80 rounded-2xl border border-slate-700/80 p-5 shadow-xl flex flex-col justify-between space-y-4">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center space-x-2">
                <Compass className="h-4 w-4 text-indigo-400" />
                <span>Coordinate Snapping Inspector</span>
              </h2>

              <form onSubmit={handleApplyCoordinates} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">
                      Latitude (°N)
                    </label>
                    <input
                      type="number"
                      step="0.0001"
                      min={0}
                      max={40}
                      value={inputLat}
                      onChange={(e) => setInputLat(parseFloat(e.target.value) || 0)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">
                      Longitude (°E)
                    </label>
                    <input
                      type="number"
                      step="0.0001"
                      min={60}
                      max={100}
                      value={inputLon}
                      onChange={(e) => setInputLon(parseFloat(e.target.value) || 0)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2 pt-1">
                  <button
                    type="submit"
                    className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2 px-3 rounded-xl text-xs transition-colors cursor-pointer"
                  >
                    Inspect Coordinates
                  </button>
                  <button
                    type="button"
                    onClick={handleResetToCity}
                    className="bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold py-2 px-3 rounded-xl text-xs transition-colors cursor-pointer"
                    title="Reset to your local city"
                  >
                    My City
                  </button>
                </div>
              </form>
            </div>

            {/* Snapped Point Metrics */}
            <div className="bg-slate-900/70 rounded-xl border border-slate-700/60 p-3 space-y-2.5 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-slate-400">Target Query Coords:</span>
                <span className="font-mono font-bold text-white">
                  {activeLat.toFixed(4)}°N, {activeLon.toFixed(4)}°E
                </span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-slate-400">Nearest Grid Cell Coords:</span>
                <span className="font-mono font-bold text-indigo-300">
                  {gridLat != null && gridLon != null
                    ? `${gridLat.toFixed(2)}°N, ${gridLon.toFixed(2)}°E`
                    : "—"}
                </span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-slate-400">Snapping Distance:</span>
                <span className="font-mono font-semibold text-emerald-400">
                  {distanceKm.toFixed(2)} km
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Cell Domain Type:</span>
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                    isSea
                      ? "bg-cyan-900/60 text-cyan-300 border border-cyan-700/60"
                      : "bg-emerald-900/60 text-emerald-300 border border-emerald-700/60"
                  }`}
                >
                  {isSea ? "Maritime Sea Point (Wave + Atmos)" : "Inland Atmospheric Point"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Parity Status Badge Banner */}
        {parityAnalysis && (
          <div
            data-testid="parity-badge"
            className={`rounded-2xl p-4.5 border flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg ${
              parityAnalysis.badgeType === "green"
                ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-200"
                : "bg-amber-950/40 border-amber-500/40 text-amber-200"
            }`}
          >
            <div className="flex items-start sm:items-center space-x-3">
              <div
                className={`p-2 rounded-xl shrink-0 ${
                  parityAnalysis.badgeType === "green"
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-amber-500/20 text-amber-400"
                }`}
              >
                {parityAnalysis.badgeType === "green" ? (
                  <CheckCircle2 className="h-5 w-5" />
                ) : (
                  <AlertTriangle className="h-5 w-5" />
                )}
              </div>
              <div>
                <h3 className="font-bold text-sm sm:text-base flex items-center space-x-2 flex-wrap gap-y-1">
                  <span>
                    {parityAnalysis.badgeType === "green"
                      ? "Full Source Parity Confirmed"
                      : "Source Parity Variance Notice"}
                  </span>
                  <span
                    data-testid="stored-data-age"
                    className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono font-normal border border-slate-700"
                  >
                    Stored data age: {parityAnalysis.ageHours.toFixed(1)} h
                  </span>
                </h3>
                <p className="text-xs text-slate-300 mt-0.5">{parityAnalysis.badgeReason}</p>
              </div>
            </div>

            <div className="flex items-center space-x-4 text-xs font-mono shrink-0 pl-11 sm:pl-0">
              <div className="flex items-center space-x-1.5 text-slate-400">
                <Clock className="h-3.5 w-3.5" />
                <span>Stored data age: {parityAnalysis.ageHours.toFixed(1)} h</span>
              </div>
              <div className="bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700 text-slate-300">
                Max ΔT: {parityAnalysis.maxTempDiff.toFixed(1)}°C
              </div>
            </div>
          </div>
        )}

        {/* Timestamps Card */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="bg-slate-800/60 rounded-xl border border-slate-700/60 p-3.5 flex items-center justify-between">
            <span className="text-slate-400 flex items-center space-x-1.5">
              <span className="h-2 w-2 rounded-full bg-indigo-400"></span>
              <span>Database Ingestion Timestamp (fetched_at):</span>
            </span>
            <span className="font-mono text-slate-200">
              {storedData?.fetched_at ? new Date(storedData.fetched_at).toLocaleString() : "Loading…"}
            </span>
          </div>
          <div className="bg-slate-800/60 rounded-xl border border-slate-700/60 p-3.5 flex items-center justify-between">
            <span className="text-slate-400 flex items-center space-x-1.5">
              <span className="h-2 w-2 rounded-full bg-blue-400"></span>
              <span>Live Open-Meteo Server-Side Fetch Time:</span>
            </span>
            <span className="font-mono text-slate-200">
              {liveData?.live_fetched_at ? new Date(liveData.live_fetched_at).toLocaleString() : "Loading…"}
            </span>
          </div>
        </div>

        {/* Comparison Tables: Next 24 Hours */}
        <div className="bg-slate-800/80 rounded-2xl border border-slate-700/80 shadow-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-700/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <h2 className="text-base font-bold text-white flex items-center space-x-2">
                <span>Next 24-Hour Aligned Comparison</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Stored PostgreSQL grid point vs. live upstream Open-Meteo model output with delta values per parameter.
              </p>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Displaying {alignedRows.length} hourly slices
            </div>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-slate-400 space-y-3">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto text-blue-400" />
              <p className="text-sm">Fetching and aligning numerical forecasts…</p>
            </div>
          ) : isStoredError || isLiveError ? (
            <div className="p-8 text-center text-rose-300 space-y-2">
              <AlertTriangle className="h-8 w-8 mx-auto text-rose-400" />
              <p className="font-bold text-sm">Failed to retrieve forecast data</p>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                {((storedError || liveError) as Error)?.message || "Please check coordinate bounds and try again."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-900/80 text-slate-300 border-b border-slate-700/80">
                    <th className="py-3 px-3.5 font-bold">Valid Time (UTC)</th>
                    <th className="py-3 px-3 font-semibold text-center border-l border-slate-800">
                      <div className="flex items-center justify-center space-x-1">
                        <Thermometer className="h-3.5 w-3.5 text-amber-400" />
                        <span>Temp (Stored vs Live)</span>
                      </div>
                    </th>
                    <th className="py-3 px-3 font-semibold text-center border-l border-slate-800">
                      <div className="flex items-center justify-center space-x-1">
                        <CloudRain className="h-3.5 w-3.5 text-cyan-400" />
                        <span>Rain (Stored vs Live)</span>
                      </div>
                    </th>
                    <th className="py-3 px-3 font-semibold text-center border-l border-slate-800">
                      <div className="flex items-center justify-center space-x-1">
                        <Wind className="h-3.5 w-3.5 text-teal-400" />
                        <span>Wind (Stored vs Live)</span>
                      </div>
                    </th>
                    <th className="py-3 px-3 font-semibold text-center border-l border-slate-800">
                      <div className="flex items-center justify-center space-x-1">
                        <Gauge className="h-3.5 w-3.5 text-purple-400" />
                        <span>Pressure (Stored vs Live)</span>
                      </div>
                    </th>
                    {isSea && (
                      <th className="py-3 px-3 font-semibold text-center border-l border-slate-800">
                        <div className="flex items-center justify-center space-x-1">
                          <Waves className="h-3.5 w-3.5 text-blue-400" />
                          <span>Wave Height (Stored vs Live)</span>
                        </div>
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 font-mono">
                  {alignedRows.map((row) => {
                    const timeLabel = `${formatUtcHour(row.valid_time)} UTC (${row.valid_time.substring(5, 10)})`;
                    const tDelta = formatDelta(row.diffs.dTemp, "°C");
                    const pDelta = formatDelta(row.diffs.dPrecip, "mm");
                    const wDelta = formatDelta(row.diffs.dWind, "km/h");
                    const pressDelta = formatDelta(row.diffs.dPress, "hPa");
                    const waveDelta = formatDelta(row.diffs.dWave, "m");

                    return (
                      <tr
                        key={row.valid_time}
                        className={`hover:bg-slate-700/30 transition-colors ${
                          row.isMismatch ? "bg-amber-950/15" : ""
                        }`}
                      >
                        {/* Time */}
                        <td className="py-2.5 px-3.5 font-bold text-slate-300 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            <span>{timeLabel}</span>
                            {row.isEarlierToday && (
                              <span className="text-[10px] font-sans uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-700/90 text-amber-300 border border-amber-500/40">
                                earlier today
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Temperature */}
                        <td className="py-2.5 px-3 text-center border-l border-slate-800/80">
                          <div className="flex items-center justify-center space-x-2">
                            <span className="text-slate-300">
                              {row.stored.temperature_2m != null ? `${row.stored.temperature_2m}°C` : "—"}
                            </span>
                            <span className="text-slate-500">vs</span>
                            <span className="text-white">
                              {row.live?.temperature_2m != null ? `${row.live.temperature_2m}°C` : "—"}
                            </span>
                            <span
                              className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                                tDelta.isZero
                                  ? "text-slate-400 bg-slate-800/60"
                                  : Math.abs(row.diffs.dTemp || 0) > 0.5
                                  ? "text-amber-300 bg-amber-900/60 border border-amber-700/60"
                                  : "text-emerald-300 bg-emerald-900/40"
                              }`}
                            >
                              {tDelta.text}
                            </span>
                          </div>
                        </td>

                        {/* Precipitation */}
                        <td className="py-2.5 px-3 text-center border-l border-slate-800/80">
                          <div className="flex items-center justify-center space-x-2">
                            <span className="text-slate-300">
                              {row.stored.precipitation != null ? `${row.stored.precipitation}mm` : "—"}
                            </span>
                            <span className="text-slate-500">vs</span>
                            <span className="text-white">
                              {row.live?.precipitation != null ? `${row.live.precipitation}mm` : "—"}
                            </span>
                            <span
                              className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                                pDelta.isZero
                                  ? "text-slate-400 bg-slate-800/60"
                                  : Math.abs(row.diffs.dPrecip || 0) > 0.5
                                  ? "text-amber-300 bg-amber-900/60 border border-amber-700/60"
                                  : "text-emerald-300 bg-emerald-900/40"
                              }`}
                            >
                              {pDelta.text}
                            </span>
                          </div>
                        </td>

                        {/* Wind Speed */}
                        <td className="py-2.5 px-3 text-center border-l border-slate-800/80">
                          <div className="flex items-center justify-center space-x-2">
                            <span className="text-slate-300">
                              {row.stored.wind_speed_10m != null ? `${row.stored.wind_speed_10m}` : "—"}
                            </span>
                            <span className="text-slate-500">vs</span>
                            <span className="text-white">
                              {row.live?.wind_speed_10m != null ? `${row.live.wind_speed_10m}` : "—"}
                            </span>
                            <span
                              className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                                wDelta.isZero
                                  ? "text-slate-400 bg-slate-800/60"
                                  : Math.abs(row.diffs.dWind || 0) > 2.0
                                  ? "text-amber-300 bg-amber-900/60 border border-amber-700/60"
                                  : "text-emerald-300 bg-emerald-900/40"
                              }`}
                            >
                              {wDelta.text}
                            </span>
                          </div>
                        </td>

                        {/* Pressure */}
                        <td className="py-2.5 px-3 text-center border-l border-slate-800/80">
                          <div className="flex items-center justify-center space-x-2">
                            <span className="text-slate-300">
                              {row.stored.pressure_msl != null ? `${row.stored.pressure_msl}` : "—"}
                            </span>
                            <span className="text-slate-500">vs</span>
                            <span className="text-white">
                              {row.live?.pressure_msl != null ? `${row.live.pressure_msl}` : "—"}
                            </span>
                            <span
                              className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                                pressDelta.isZero
                                  ? "text-slate-400 bg-slate-800/60"
                                  : Math.abs(row.diffs.dPress || 0) > 1.0
                                  ? "text-amber-300 bg-amber-900/60 border border-amber-700/60"
                                  : "text-emerald-300 bg-emerald-900/40"
                              }`}
                            >
                              {pressDelta.text}
                            </span>
                          </div>
                        </td>

                        {/* Marine Wave */}
                        {isSea && (
                          <td className="py-2.5 px-3 text-center border-l border-slate-800/80">
                            <div className="flex items-center justify-center space-x-2">
                              <span className="text-slate-300">
                                {row.stored.wave_height != null ? `${row.stored.wave_height}m` : "—"}
                              </span>
                              <span className="text-slate-500">vs</span>
                              <span className="text-white">
                                {row.live?.wave_height != null ? `${row.live.wave_height}m` : "—"}
                              </span>
                              <span
                                className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                                  waveDelta.isZero
                                    ? "text-slate-400 bg-slate-800/60"
                                    : Math.abs(row.diffs.dWave || 0) > 0.2
                                    ? "text-amber-300 bg-amber-900/60 border border-amber-700/60"
                                    : "text-emerald-300 bg-emerald-900/40"
                                }`}
                              >
                                {waveDelta.text}
                              </span>
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SourceParityPage;
