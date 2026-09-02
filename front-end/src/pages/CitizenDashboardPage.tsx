import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapContainer, TileLayer, Marker, Popup, Circle, GeoJSON } from 'react-leaflet';
import L from 'leaflet';
import { ShieldCheck, AlertTriangle, MapPin, Radio, Compass, Navigation, RefreshCw } from 'lucide-react';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { useLocationScope } from '@/hooks/useLocationScope';
import { LocationGateModal } from '@/components/location/LocationGateModal';
import { RouteBlockageChecker } from '@/components/route/RouteBlockageChecker';
import { routeApi, RouteCheckResponseData } from '@/services/routeApi';
import { GeoJSONFeatureCollection } from '@/types';

// Custom Leaflet marker icons
const userLocationIcon = L.divIcon({
  className: 'user-location-marker',
  html: `<div class="relative flex h-6 w-6 items-center justify-center">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-4 w-4 bg-blue-600 border-2 border-white shadow-md"></span>
        </div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const hazardMarkerIcon = (severity: string) => {
  const colorClass =
    severity === 'SEVERE'
      ? 'bg-rose-600'
      : severity === 'HIGH'
      ? 'bg-orange-500'
      : severity === 'MODERATE'
      ? 'bg-amber-500'
      : 'bg-blue-500';

  return L.divIcon({
    className: 'hazard-marker',
    html: `<div class="flex h-7 w-7 items-center justify-center rounded-full ${colorClass} text-white font-extrabold text-[10px] shadow-lg border-2 border-white ring-2 ring-slate-900/10">
            !
          </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

export const CitizenDashboardPage: React.FC = () => {
  const { currentLocation } = useLocationScope();
  const [showLocationGate, setShowLocationGate] = useState(currentLocation.name === 'All India');
  const [radiusKm, setRadiusKm] = useState(25.0);
  const [routeCheckResult, setRouteCheckResult] = useState<RouteCheckResponseData | null>(null);

  const userLat = currentLocation.lat || 12.9716;
  const userLng = currentLocation.lon || 77.5946;

  // Query nearby verified incidents
  const { data: nearbyGeo, isLoading, refetch } = useQuery<GeoJSONFeatureCollection>({
    queryKey: ['nearbyIncidents', userLat, userLng, radiusKm],
    queryFn: () => routeApi.getNearbyIncidents(userLat, userLng, radiusKm, 'VERIFIED'),
    staleTime: 1000 * 60, // 1 min
  });

  const features = nearbyGeo?.features || [];
  const totalNearby = features.length;

  // Calculate nearest hazard distance
  let minDist: number | null = null;
  let highestSeverity = 'NONE';
  const severityRank: Record<string, number> = { SEVERE: 4, HIGH: 3, MODERATE: 2, LOW: 1 };
  let maxRank = 0;

  features.forEach((feat) => {
    const geom = feat.geometry as { type: string; coordinates?: unknown };
    if (geom && geom.type === 'Point' && Array.isArray(geom.coordinates)) {
      const coords = geom.coordinates as [number, number];
      const dLat = (coords[1] - userLat) * 111.0;
      const dLng = (coords[0] - userLng) * 111.0 * Math.cos((userLat * Math.PI) / 180);
      const dist = Math.sqrt(dLat * dLat + dLng * dLng);
      if (minDist === null || dist < minDist) {
        minDist = dist;
      }
    }
    const r = severityRank[feat.properties.severity] || 1;
    if (r > maxRank) {
      maxRank = r;
      highestSeverity = feat.properties.severity;
    }
  });

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 font-sans text-slate-900 antialiased">
      <Navbar />

      <main className="flex-1 py-6">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-6">
          {/* Header Banner */}
          <div className="flex items-center justify-between gap-4 flex-wrap rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-2xs">
            <div className="flex items-center space-x-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-md">
                <Compass className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                    My Area Citizen Dashboard
                  </h1>
                  <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-extrabold text-emerald-800 uppercase tracking-wider">
                    Verified Public Feed
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5 flex items-center space-x-1">
                  <MapPin className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                  <span>
                    Location: <strong className="text-slate-800 font-bold">{currentLocation.name}</strong> ({userLat.toFixed(4)}, {userLng.toFixed(4)})
                  </span>
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setShowLocationGate(true)}
                className="flex items-center space-x-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <Navigation className="h-3.5 w-3.5 text-blue-600" />
                <span>Change Location</span>
              </button>

              <button
                type="button"
                onClick={() => refetch()}
                className="flex items-center space-x-1.5 rounded-xl bg-blue-600 px-3.5 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-700 transition-colors cursor-pointer"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                <span>Refresh Feed</span>
              </button>
            </div>
          </div>

          {/* KPI Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Active Hazards in Radius */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider">Active Hazards Nearby</span>
                <Radio className="h-4 w-4 text-blue-600" />
              </div>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {totalNearby}
                </span>
                <span className="text-xs font-semibold text-slate-400">within {radiusKm} km</span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500 line-clamp-1">
                Verified disaster & weather alerts
              </p>
            </div>

            {/* Nearest Hazard Distance */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider">Nearest Incident</span>
                <MapPin className="h-4 w-4 text-amber-600" />
              </div>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {minDist !== null ? (minDist as number).toFixed(1) : '—'}
                </span>
                <span className="text-xs font-semibold text-slate-400">
                  {minDist !== null ? 'km away' : 'No hazards'}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500 line-clamp-1">
                Proximity to nearest active report
              </p>
            </div>

            {/* Highest Severity Nearby */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider">Peak Severity Level</span>
                <AlertTriangle className="h-4 w-4 text-rose-600" />
              </div>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className={`text-2xl font-extrabold tracking-tight ${
                  highestSeverity === 'SEVERE' ? 'text-rose-600' : highestSeverity === 'HIGH' ? 'text-orange-600' : 'text-slate-900'
                }`}>
                  {highestSeverity}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500 line-clamp-1">
                Highest risk level in your area
              </p>
            </div>

            {/* Public Safety Status */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider">Area Status</span>
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
              </div>
              <div className="mt-2 flex items-center space-x-1.5">
                <span className={`text-xl font-extrabold ${totalNearby > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                  {totalNearby > 0 ? 'Advisory Active' : 'Normal / Safe'}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500 line-clamp-1">
                {totalNearby > 0 ? 'Stay alert for local hazards' : 'No active alerts in immediate radius'}
              </p>
            </div>
          </div>

          {/* Route Blockage Checker Component */}
          <RouteBlockageChecker onRouteChecked={(data) => setRouteCheckResult(data)} />

          {/* Map & List Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Main Interactive Proximity Map */}
            <div className="lg:col-span-8 rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 flex items-center space-x-1.5">
                  <MapPin className="h-4 w-4 text-blue-600" />
                  <span>Proximity Map ({radiusKm} km Radius)</span>
                </h3>

                {/* Radius selector buttons */}
                <div className="flex items-center space-x-1 text-xs font-bold">
                  <span className="text-slate-400 mr-1 text-[11px]">Radius:</span>
                  {[10, 25, 50, 100].map((r) => (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setRadiusKm(r)}
                      className={`rounded-lg px-2.5 py-1 transition-colors ${
                        radiusKm === r ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {r}km
                    </button>
                  ))}
                </div>
              </div>

              <div className="relative h-[480px] w-full rounded-xl overflow-hidden border border-slate-200">
                <MapContainer
                  center={[userLat, userLng]}
                  zoom={11}
                  scrollWheelZoom={true}
                  className="h-full w-full"
                >
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  />

                  {/* Citizen location marker */}
                  <Marker position={[userLat, userLng]} icon={userLocationIcon}>
                    <Popup>
                      <div className="p-1 text-xs">
                        <strong className="font-bold text-blue-900">Your Location</strong>
                        <p className="text-slate-600 mt-0.5">{currentLocation.name}</p>
                      </div>
                    </Popup>
                  </Marker>

                  {/* Proximity Circle */}
                  <Circle
                    center={[userLat, userLng]}
                    radius={radiusKm * 1000}
                    pathOptions={{ color: '#2563eb', fillColor: '#3b82f6', fillOpacity: 0.08, weight: 1.5, dashArray: '4 4' }}
                  />

                  {/* Hazard markers */}
                  {features.map((feat) => {
                    if (feat.geometry.type !== 'Point') return null;
                    const coords = feat.geometry.coordinates as [number, number];
                    return (
                      <Marker
                        key={feat.properties.id}
                        position={[coords[1], coords[0]]}
                        icon={hazardMarkerIcon(feat.properties.severity)}
                      >
                        <Popup>
                          <div className="p-1 space-y-1 text-xs">
                            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-extrabold text-slate-700 uppercase">
                              {feat.properties.category_code}
                            </span>
                            <h4 className="font-bold text-slate-900">{feat.properties.title}</h4>
                            <p className="text-slate-500 text-[11px]">{feat.properties.location_name || 'Nearby Area'}</p>
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

                  {/* Route corridor GeoJSON overlay */}
                  {routeCheckResult && routeCheckResult.path_geojson && (
                    <GeoJSON
                      key={JSON.stringify(routeCheckResult.path_geojson)}
                      data={routeCheckResult.path_geojson as unknown as GeoJSON.GeoJsonObject}
                      style={(feature) => {
                        if (feature?.properties?.type === 'CORRIDOR_BUFFER') {
                          return {
                            color: routeCheckResult.is_blocked ? '#e11d48' : '#10b981',
                            fillColor: routeCheckResult.is_blocked ? '#f43f5e' : '#34d399',
                            fillOpacity: 0.2,
                            weight: 2,
                            dashArray: '5 5',
                          };
                        }
                        return {
                          color: routeCheckResult.is_blocked ? '#be123c' : '#059669',
                          weight: 4,
                        };
                      }}
                    />
                  )}
                </MapContainer>
              </div>
            </div>

            {/* Sidebar Nearby Hazards List */}
            <div className="lg:col-span-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4">
              <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-500">
                Verified Nearby Incidents ({totalNearby})
              </h3>

              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-20 rounded-xl bg-slate-100 animate-pulse" />
                  ))}
                </div>
              ) : features.length === 0 ? (
                <div className="py-12 text-center text-slate-400 space-y-2">
                  <ShieldCheck className="h-8 w-8 text-emerald-500 mx-auto" />
                  <p className="text-xs font-semibold text-slate-700">No verified hazards in this radius.</p>
                  <p className="text-[11px] text-slate-400">Try expanding the radius to 50 km or 100 km.</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[440px] overflow-y-auto pr-1">
                  {features.map((feat) => (
                    <div
                      key={feat.properties.id}
                      className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-2xs hover:border-slate-300 transition-all space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="font-extrabold text-blue-700 uppercase tracking-wider">
                          {feat.properties.category_code}
                        </span>
                        <span className="rounded bg-rose-100 px-1.5 py-0.2 font-extrabold text-rose-800">
                          {feat.properties.severity}
                        </span>
                      </div>

                      <h4 className="text-xs font-bold text-slate-900 line-clamp-1">{feat.properties.title}</h4>

                      <p className="text-[11px] text-slate-500 flex items-center space-x-1">
                        <MapPin className="h-3 w-3 text-slate-400 shrink-0" />
                        <span className="truncate">{feat.properties.location_name || 'Reported Area'}</span>
                      </p>

                      {feat.properties.credibility_reason && (
                        <p className="text-[10px] text-slate-600 bg-slate-50 p-2 rounded-lg border border-slate-100 italic line-clamp-2">
                          {feat.properties.credibility_reason}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <Footer />

      {/* Location Gate Onboarding Modal */}
      <LocationGateModal isOpen={showLocationGate} onClose={() => setShowLocationGate(false)} />
    </div>
  );
};
