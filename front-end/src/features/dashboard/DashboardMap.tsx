import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Link } from 'react-router-dom';
import {
  Maximize2,
  Plus,
  Minus,
  Compass,
  Clock,
  Radio,
  X,
  ArrowRight,
} from 'lucide-react';
import { MapIncidentPoint } from '@/features/map/adapters';

export interface DashboardMapProps {
  reports: MapIncidentPoint[];
  selectedReport: MapIncidentPoint | null;
  onSelectReport: (report: MapIncidentPoint | null) => void;
  targetRegion?: { center: [number, number]; zoom: number };
  severeCount?: number;
}

interface IncidentGroup {
  key: string;
  latitude: number;
  longitude: number;
  reports: MapIncidentPoint[];
  latestReport: MapIncidentPoint;
  hasSevere: boolean;
}

// Custom map icon helpers
const createHazardIcon = (severity: string, isSelected: boolean, isVerified: boolean) => {
  let colorClass = 'bg-blue-600 border-white';
  if (isSelected) {
    colorClass = 'bg-blue-600 ring-4 ring-blue-300 border-white';
  } else if (severity === 'SEVERE' || severity === 'HIGH') {
    colorClass = 'bg-red-600 border-white';
  } else if (isVerified) {
    colorClass = 'bg-emerald-600 border-white';
  } else if (severity === 'MODERATE') {
    colorClass = 'bg-amber-600 border-white';
  }

  return L.divIcon({
    className: 'custom-hazard-marker',
    html: `
      <div class="relative flex items-center justify-center">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full ${
          severity === 'SEVERE' || severity === 'HIGH' ? 'bg-red-400' : 'bg-blue-400'
        } opacity-40"></span>
        <span class="relative inline-flex rounded-full h-4 w-4 ${colorClass} border-2 shadow-md"></span>
      </div>
    `,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
};

const createClusterIcon = (count: number, hasSevere: boolean, isSelected: boolean) => {
  const colorClass = isSelected
    ? 'bg-blue-600 ring-4 ring-blue-300'
    : hasSevere
    ? 'bg-amber-600'
    : 'bg-blue-600';

  return L.divIcon({
    className: 'custom-cluster-marker',
    html: `
      <div class="relative flex items-center justify-center">
        <span class="relative inline-flex items-center justify-center rounded-full h-6 w-6 ${colorClass} text-white text-[11px] font-bold shadow-md border-2 border-white">
          ${count > 99 ? '99+' : count}
        </span>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
};

// Map controller to handle pan/zoom
const MapController: React.FC<{
  selectedReport: MapIncidentPoint | null;
  targetRegion?: { center: [number, number]; zoom: number };
}> = ({ selectedReport, targetRegion }) => {
  const map = useMap();

  useEffect(() => {
    if (selectedReport?.location?.latitude != null && selectedReport?.location?.longitude != null) {
      map.flyTo([selectedReport.location.latitude, selectedReport.location.longitude], 11, {
        duration: 1.2,
      });
    } else if (targetRegion) {
      map.flyTo(targetRegion.center, targetRegion.zoom, { duration: 1.2 });
    }
  }, [selectedReport, targetRegion, map]);

  return null;
};

// Custom map controls inside map container
const MapControls: React.FC = () => {
  const map = useMap();

  return (
    <div className="absolute right-3 top-3 z-[400] flex flex-col space-y-1.5 shadow-md">
      <button
        type="button"
        onClick={() => map.zoomIn()}
        aria-label="Zoom in"
        className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-slate-700 hover:bg-slate-50 hover:text-blue-600 shadow-sm border border-slate-200 transition-colors"
      >
        <Plus className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => map.zoomOut()}
        aria-label="Zoom out"
        className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-slate-700 hover:bg-slate-50 hover:text-blue-600 shadow-sm border border-slate-200 transition-colors"
      >
        <Minus className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => map.setView([20.5937, 78.9629], 5)}
        aria-label="Reset India view"
        className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-slate-700 hover:bg-slate-50 hover:text-blue-600 shadow-sm border border-slate-200 transition-colors"
      >
        <Compass className="h-4 w-4" />
      </button>
    </div>
  );
};

export const DashboardMap: React.FC<DashboardMapProps> = ({
  reports,
  severeCount,
  selectedReport,
  onSelectReport,
  targetRegion,
}) => {
  const defaultCenter: [number, number] = [20.5937, 78.9629];
  const defaultZoom = 5;

  // Group coordinates to handle repeated coordinates cleanly (4-decimal precision)
  const locationGroups = useMemo<IncidentGroup[]>(() => {
    const groups: Record<string, IncidentGroup> = {};

    for (const report of reports) {
      if (report.location?.latitude != null && report.location?.longitude != null) {
        const latKey = report.location.latitude.toFixed(4);
        const lngKey = report.location.longitude.toFixed(4);
        const key = `${latKey}_${lngKey}`;

        if (!groups[key]) {
          groups[key] = {
            key,
            latitude: report.location.latitude,
            longitude: report.location.longitude,
            reports: [],
            latestReport: report,
            hasSevere: false,
          };
        }
        groups[key].reports.push(report);
        if (report.severity === 'SEVERE' || report.severity === 'HIGH') {
          groups[key].hasSevere = true;
        }
      }
    }

    return Object.values(groups);
  }, [reports]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col h-full">
      {/* Map Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-white">
        <div className="flex items-center space-x-2">
          <div className="flex h-2.5 w-2.5 rounded-full bg-blue-600 animate-pulse" />
          <h3 className="text-sm font-bold text-slate-900">Situational Incident Map</h3>
          <span className="text-xs text-slate-500 font-medium">({locationGroups.length} Active Locations)</span>
        </div>
        <Link
          to="/live-map"
          className="flex items-center space-x-1.5 text-xs font-bold text-blue-600 hover:text-blue-700 transition-colors"
        >
          <span>View Full Map</span>
          <Maximize2 className="h-3.5 w-3.5" />
        </Link>
      </div>

      {/* Leaflet Map Container */}
      <div className="relative h-[380px] sm:h-[440px] w-full bg-slate-100">
        <MapContainer
          center={defaultCenter}
          zoom={defaultZoom}
          zoomControl={false}
          className="h-full w-full z-0"
          attributionControl={true}
        >
          <TileLayer
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
            maxZoom={19}
          />

          <MapController selectedReport={selectedReport} targetRegion={targetRegion} />
          <MapControls />

          {/* Render markers */}
          {locationGroups.map((group) => {
            const isCluster = group.reports.length > 1;
            const isSelected = group.reports.some(
              (r) => r.tracking_id === selectedReport?.tracking_id
            );
            const isVerified = group.latestReport.verification_status === 'VERIFIED';

            return (
              <Marker
                key={group.key}
                position={[group.latitude, group.longitude]}
                icon={
                  isCluster
                    ? createClusterIcon(group.reports.length, group.hasSevere, isSelected)
                    : createHazardIcon(group.latestReport.severity, isSelected, isVerified)
                }
                eventHandlers={{
                  click: () => onSelectReport(group.latestReport),
                }}
              />
            );
          })}
        </MapContainer>

        {/* Top-Left Situational Badge Overlay */}
        <div className="absolute left-3 top-3 z-[400] pointer-events-none">
          <div className="rounded-xl border border-slate-200/90 bg-white/95 p-2.5 shadow-md backdrop-blur-sm pointer-events-auto">
            <h4 className="text-xs font-bold text-slate-900">National Weather Radar</h4>
            <div className="mt-1 flex items-center space-x-1.5">
              <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-bold text-red-700">
                <span className="mr-1 h-1.5 w-1.5 rounded-full bg-red-600 animate-ping" />
                {severeCount != null ? `${severeCount.toLocaleString()} Severe Alerts` : '— Severe Alerts'}
              </span>
            </div>
          </div>
        </div>

        {/* Bottom Selected Incident Overlay Card (matching desktop reference) */}
        {selectedReport && (
          <div className="absolute bottom-3 left-3 right-3 sm:right-auto sm:max-w-sm z-[400] animate-in fade-in slide-in-from-bottom-2 duration-200">
            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xl">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600">
                    {selectedReport.location?.name || `${selectedReport.location?.latitude?.toFixed(2)}, ${selectedReport.location?.longitude?.toFixed(2)}`}
                  </span>
                  <h4 className="text-xs font-bold text-slate-900 mt-0.5">
                    {selectedReport.title}
                  </h4>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="inline-flex rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700">
                    {selectedReport.verification_status || 'PENDING'}
                  </span>
                  <button
                    type="button"
                    onClick={() => onSelectReport(null)}
                    className="p-0.5 text-slate-400 hover:text-slate-700 rounded-full"
                    aria-label="Close card"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              <div className="mt-2 space-y-1 text-[11px] text-slate-500">
                <div className="flex items-center space-x-1.5">
                  <Clock className="h-3 w-3 text-slate-400" />
                  <span>
                    {selectedReport.occurred_at
                      ? new Date(selectedReport.occurred_at).toLocaleString([], {
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                        }) + ' IST'
                      : 'Recent'}
                  </span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <Radio className="h-3 w-3 text-slate-400" />
                  <span>Source: Citizen Report (ID: #{selectedReport.tracking_id})</span>
                </div>
              </div>

              <div className="mt-3">
                <Link
                  to={`/track-report?id=${encodeURIComponent(selectedReport.tracking_id)}`}
                  className="flex w-full items-center justify-center space-x-1.5 rounded-lg bg-blue-600 py-1.5 text-xs font-bold text-white hover:bg-blue-700 transition-colors shadow-sm"
                >
                  <span>View Details</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Legend Footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 border-t border-slate-100 bg-slate-50/60 text-xs text-slate-600">
        <div className="flex flex-wrap items-center gap-4 text-[11px] font-medium">
          <span className="font-bold text-slate-700">Legend:</span>
          <div className="flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-red-600" />
            <span>Severe Warning</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-600" />
            <span>Moderate Watch</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-600" />
            <span>Verified Event</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-blue-600 ring-2 ring-blue-300" />
            <span>Selected</span>
          </div>
        </div>
      </div>
    </div>
  );
};
