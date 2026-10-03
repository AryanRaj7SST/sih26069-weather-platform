import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, Circle } from 'react-leaflet';
import L from 'leaflet';
import { Globe, Layers, RefreshCw, Thermometer, CloudRain, Wind, Waves } from 'lucide-react';
import { routeApi } from '@/services/routeApi';
import { incidentApi } from '@/services/incidentApi';
import { GeoJSONFeatureCollection } from '@/types';
import { fetchWeatherTimes, fetchWeatherGrid, fetchMarineGrid, WeatherGridFeatureCollection } from '@/services/weatherGridApi';
import { WeatherCanvasLayer, WeatherMetric } from '@/components/map/WeatherCanvasLayer';
import { WeatherTimeSlider } from '@/components/map/WeatherTimeSlider';
import { WeatherColorLegend } from '@/components/map/WeatherColorLegend';

// Custom Leaflet incident marker icon for national view
const nationalIncidentIcon = (severity: string) => {
  const bg = severity === 'SEVERE' ? 'bg-rose-600' : severity === 'HIGH' ? 'bg-orange-500' : 'bg-blue-600';
  return L.divIcon({
    className: 'national-incident-marker',
    html: `<div class="flex h-5 w-5 items-center justify-center rounded-full ${bg} text-white font-extrabold text-[9px] shadow-md border border-white">
            !
          </div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
};

export const NationalMapPage: React.FC = () => {
  const [showEEZ, setShowEEZ] = useState(true);
  const [showIncidents, setShowIncidents] = useState(true);
  const [showForecasts, setShowForecasts] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [activeWeatherMetric, setActiveWeatherMetric] = useState<WeatherMetric | null>('temperature');
  const [selectedTime, setSelectedTime] = useState<string | null>(null);

  // 1. Fetch Nationwide Verified Incidents
  const { data: incidentsGeo, isLoading: isLoadingIncidents, refetch: refetchIncidents } = useQuery<GeoJSONFeatureCollection>({
    queryKey: ['nationalIncidentsGeo'],
    queryFn: () => incidentApi.getGeoIncidents(undefined, { status: 'VERIFIED', hours_ago: 72 }),
    staleTime: 1000 * 60 * 2,
  });

  // 2. Fetch Forecast Advisories & Cyclone Tracks
  const { data: forecastGeo } = useQuery<GeoJSONFeatureCollection>({
    queryKey: ['forecastAdvisoriesGeo'],
    queryFn: () => routeApi.getForecastAdvisories(undefined, true),
    staleTime: 1000 * 60 * 5,
  });

  // 3. Fetch Static EEZ Boundary GeoJSON
  const { data: eezGeo } = useQuery<GeoJSONFeatureCollection>({
    queryKey: ['eezBoundaryGeo'],
    queryFn: async () => {
      const res = await fetch('/static/eez_india_boundary.geojson');
      return res.json();
    },
    staleTime: Infinity,
  });

  // 4. Fetch Available Forecast Time Steps
  const { data: timesData } = useQuery({
    queryKey: ['weatherTimes'],
    queryFn: fetchWeatherTimes,
    staleTime: 1000 * 60 * 2,
  });

  // Default to hour closest to now
  React.useEffect(() => {
    if (timesData?.valid_times && timesData.valid_times.length > 0 && !selectedTime) {
      const nowMs = Date.now();
      let bestTime = timesData.valid_times[0];
      let minDiff = Infinity;
      timesData.valid_times.forEach((t) => {
        const diff = Math.abs(new Date(t).getTime() - nowMs);
        if (diff < minDiff) {
          minDiff = diff;
          bestTime = t;
        }
      });
      setSelectedTime(bestTime);
    }
  }, [timesData, selectedTime]);

  // 5. Fetch Gridded Weather Forecast for selected valid_time
  const { data: weatherGridData } = useQuery<WeatherGridFeatureCollection>({
    queryKey: ['weatherGrid', selectedTime],
    queryFn: () => fetchWeatherGrid(selectedTime || undefined),
    enabled: activeWeatherMetric !== null,
    staleTime: 1000 * 60 * 2,
  });

  // 6. Fetch Marine Grid Forecast for selected valid_time
  const { data: marineGridData } = useQuery<WeatherGridFeatureCollection>({
    queryKey: ['marineGrid', selectedTime],
    queryFn: () => fetchMarineGrid(selectedTime || undefined),
    enabled: activeWeatherMetric === 'wave_height',
    staleTime: 1000 * 60 * 2,
  });

  const incidentFeatures = incidentsGeo?.features || [];
  const forecastFeatures = forecastGeo?.features || [];

  return (
    <div className="py-6">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between gap-4 flex-wrap rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-2xs">
            <div className="flex items-center space-x-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-md">
                <Globe className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                    National Weather & Maritime Map
                  </h1>
                  <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-[10px] font-extrabold text-indigo-800 uppercase tracking-wider">
                    All-India + EEZ Scope
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Unified operational view combining real-time verified incidents, IMD/NDMA cyclone track advisories, hazard density heatmaps, and India Exclusive Economic Zone boundaries.
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => refetchIncidents()}
                className="flex items-center space-x-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 transition-colors cursor-pointer"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isLoadingIncidents ? 'animate-spin' : ''}`} />
                <span>Refresh National View</span>
              </button>
            </div>
          </div>

          {/* Layer Control Bar */}
          <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs flex-wrap gap-3">
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-700">
              <Layers className="h-4 w-4 text-indigo-600" />
              <span>Map Layer Toggles:</span>
            </div>

            <div className="flex items-center space-x-4 text-xs font-semibold text-slate-700 flex-wrap gap-y-2">
              {/* Toggle Incidents */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showIncidents}
                  onChange={(e) => setShowIncidents(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-4 w-4 cursor-pointer"
                />
                <span className="flex items-center space-x-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-blue-600" />
                  <span>Verified Incidents ({incidentFeatures.length})</span>
                </span>
              </label>

              {/* Toggle Forecast Advisories */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showForecasts}
                  onChange={(e) => setShowForecasts(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 h-4 w-4 cursor-pointer"
                />
                <span className="flex items-center space-x-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-indigo-600" />
                  <span>IMD/NDMA Forecast Advisories ({forecastFeatures.length})</span>
                </span>
              </label>

              {/* Toggle Hazard Heatmap */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showHeatmap}
                  onChange={(e) => setShowHeatmap(e.target.checked)}
                  className="rounded border-slate-300 text-rose-600 focus:ring-rose-500 h-4 w-4 cursor-pointer"
                />
                <span className="flex items-center space-x-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-500 animate-pulse" />
                  <span>Hazard Density Heatmap (B5)</span>
                </span>
              </label>

              {/* Toggle EEZ Boundary */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showEEZ}
                  onChange={(e) => setShowEEZ(e.target.checked)}
                  className="rounded border-slate-300 text-cyan-600 focus:ring-cyan-500 h-4 w-4 cursor-pointer"
                />
                <span className="flex items-center space-x-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-cyan-500" />
                  <span>India EEZ Maritime Boundary</span>
                </span>
              </label>
            </div>

            {/* Toggleable Gridded Weather Forecast Layers */}
            <div className="w-full pt-3 mt-1 border-t border-slate-100 flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center space-x-2 text-xs font-bold text-slate-700">
                <Thermometer className="h-4 w-4 text-amber-500" />
                <span>Gridded Model Forecast Layers:</span>
              </div>
              <div className="flex items-center space-x-2 text-xs flex-wrap gap-y-1.5">
                <button
                  type="button"
                  onClick={() => setActiveWeatherMetric(null)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    activeWeatherMetric === null
                      ? "bg-slate-800 text-white shadow-xs"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  Off
                </button>
                <button
                  type="button"
                  onClick={() => setActiveWeatherMetric("temperature")}
                  className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    activeWeatherMetric === "temperature"
                      ? "bg-amber-500 text-white shadow-xs"
                      : "bg-amber-50 text-amber-800 hover:bg-amber-100 border border-amber-200"
                  }`}
                >
                  <Thermometer className="h-3.5 w-3.5" />
                  <span>Temperature</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveWeatherMetric("precipitation")}
                  className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    activeWeatherMetric === "precipitation"
                      ? "bg-blue-600 text-white shadow-xs"
                      : "bg-blue-50 text-blue-800 hover:bg-blue-100 border border-blue-200"
                  }`}
                >
                  <CloudRain className="h-3.5 w-3.5" />
                  <span>Rainfall</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveWeatherMetric("wind")}
                  className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    activeWeatherMetric === "wind"
                      ? "bg-teal-600 text-white shadow-xs"
                      : "bg-teal-50 text-teal-800 hover:bg-teal-100 border border-teal-200"
                  }`}
                >
                  <Wind className="h-3.5 w-3.5" />
                  <span>Wind Flow</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveWeatherMetric("wave_height")}
                  className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    activeWeatherMetric === "wave_height"
                      ? "bg-indigo-600 text-white shadow-xs"
                      : "bg-indigo-50 text-indigo-800 hover:bg-indigo-100 border border-indigo-200"
                  }`}
                >
                  <Waves className="h-3.5 w-3.5" />
                  <span>Wave Height (EEZ Sea)</span>
                </button>
              </div>
            </div>
          </div>

          {/* Map Container */}
          <div className="relative h-[620px] w-full rounded-2xl overflow-hidden border border-slate-200 shadow-sm bg-slate-900">
            <MapContainer
              center={[20.5937, 78.9629]} // All-India centroid
              zoom={5}
              scrollWheelZoom={true}
              className="h-full w-full"
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              />

              {/* EEZ GeoJSON Layer */}
              {showEEZ && eezGeo && (
                <GeoJSON
                  data={eezGeo as unknown as GeoJSON.GeoJsonObject}
                  style={{
                    color: '#06b6d4',
                    fillColor: '#0891b2',
                    fillOpacity: 0.05,
                    weight: 2,
                    dashArray: '6 6',
                  }}
                />
              )}

              {/* Forecast Advisories GeoJSON Layer */}
              {showForecasts && forecastFeatures.length > 0 && (
                <GeoJSON
                  key={JSON.stringify(forecastGeo)}
                  data={forecastGeo as unknown as GeoJSON.GeoJsonObject}
                  style={{
                    color: '#6366f1',
                    fillColor: '#818cf8',
                    fillOpacity: 0.25,
                    weight: 2.5,
                  }}
                  onEachFeature={(feature, layer) => {
                    const props = feature.properties;
                    layer.bindPopup(`
                      <div class="p-1 text-xs space-y-1">
                        <span class="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-bold text-indigo-800 uppercase">
                          ${props.category_code || 'ADVISORY'}
                        </span>
                        <h4 class="font-bold text-slate-900">${props.title}</h4>
                        <p class="text-slate-600 text-[11px]">${props.location_name || ''}</p>
                        <p class="text-indigo-900 bg-indigo-50 p-1.5 rounded font-medium text-[10px]">
                          ${props.credibility_reason || 'Official Bulletin'}
                        </p>
                      </div>
                    `);
                  }}
                />
              )}

              {/* Hazard Density Heatmap Layer (B5) */}
              {showHeatmap &&
                incidentFeatures.map((feat) => {
                  if (feat.geometry.type !== 'Point') return null;
                  const coords = feat.geometry.coordinates as [number, number];
                  const color = feat.properties.severity === 'SEVERE' ? '#ef4444' : feat.properties.severity === 'HIGH' ? '#f97316' : '#eab308';
                  return (
                    <Circle
                      key={`heat-${feat.properties.id}`}
                      center={[coords[1], coords[0]]}
                      radius={45000} // 45km density radius
                      pathOptions={{
                        color,
                        fillColor: color,
                        fillOpacity: 0.35,
                        weight: 1,
                      }}
                    />
                  );
                })}

              {/* Incident Markers */}
              {showIncidents &&
                incidentFeatures.map((feat) => {
                  if (feat.geometry.type !== 'Point') return null;
                  const coords = feat.geometry.coordinates as [number, number];
                  return (
                    <Marker
                      key={feat.properties.id}
                      position={[coords[1], coords[0]]}
                      icon={nationalIncidentIcon(feat.properties.severity)}
                    >
                      <Popup>
                        <div className="p-1 space-y-1 text-xs">
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700 uppercase">
                            {feat.properties.category_code}
                          </span>
                          {feat.properties.is_demo && (
                            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-extrabold text-amber-800 uppercase border border-amber-300 ml-1">
                              DEMO
                            </span>
                          )}
                          <h4 className="font-bold text-slate-900">{feat.properties.title}</h4>
                          <p className="text-slate-500 text-[11px]">{feat.properties.location_name || 'India Area'}</p>
                          {feat.properties.credibility_reason && (
                            <p className="text-blue-900 bg-blue-50 p-1.5 rounded font-medium text-[10px]">
                              {feat.properties.credibility_reason}
                            </p>
                          )}
                        </div>
                      </Popup>
                    </Marker>
                  );
                })}

              {/* Gridded Weather Forecast Canvas Layer */}
              <WeatherCanvasLayer
                weatherFeatures={weatherGridData?.features || []}
                marineFeatures={marineGridData?.features || []}
                activeMetric={activeWeatherMetric}
              />
            </MapContainer>

            {/* Weather Time Slider Overlay */}
            {activeWeatherMetric && timesData?.valid_times && timesData.valid_times.length > 0 && (
              <div className="absolute bottom-4 left-4 right-4 sm:left-auto sm:right-auto sm:left-1/2 sm:-translate-x-1/2 z-[490] flex justify-center">
                <WeatherTimeSlider
                  validTimes={timesData.valid_times}
                  selectedTime={selectedTime}
                  onSelectTime={setSelectedTime}
                  activeMetric={activeWeatherMetric}
                />
              </div>
            )}

            {/* Weather Color Legend Overlay */}
            {activeWeatherMetric && (
              <div className="absolute top-4 right-4 z-[490]">
                <WeatherColorLegend activeMetric={activeWeatherMetric} />
              </div>
            )}

            {/* Source Note on Map */}
            {activeWeatherMetric && (
              <div
                data-testid="weather-source-note"
                className="absolute top-4 left-14 z-[480] max-w-xs bg-slate-900/85 backdrop-blur-md border border-slate-700/70 rounded-xl px-3 py-1.5 text-[11px] text-slate-300 font-sans shadow-lg flex items-center space-x-2 pointer-events-none"
              >
                <span className="h-2 w-2 rounded-full bg-blue-400 shrink-0" />
                <span>
                  Open-Meteo model data (not station observations) - updated{" "}
                  {timesData?.latest_fetched_at
                    ? new Date(timesData.latest_fetched_at).toLocaleString()
                    : "recently"}
                </span>
              </div>
            )}
          </div>
        </div>
    </div>
  );
};
