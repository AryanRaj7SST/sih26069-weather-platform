import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { Plus, Minus, Compass, Locate } from 'lucide-react';
import { ReportDetailData } from '@/types';

interface RegionInfo {
  center: [number, number];
  zoom: number;
  bbox?: string;
}

interface LiveMapContainerProps {
  reports: ReportDetailData[];
  selectedReport: ReportDetailData | null;
  onSelectReport: (report: ReportDetailData) => void;
  targetRegion?: RegionInfo;
  onBoundsChange?: (bbox: string) => void;
}

interface IncidentLocationGroup {
  key: string;
  latitude: number;
  longitude: number;
  reports: ReportDetailData[];
  latestReport: ReportDetailData;
  hasSevere: boolean;
}

// Controller component to programmatically pan/zoom map on selection or region change
const MapController: React.FC<{
  selectedReport: ReportDetailData | null;
  targetRegion?: RegionInfo;
}> = ({ selectedReport, targetRegion }) => {
  const map = useMap();

  useEffect(() => {
    if (selectedReport?.location?.latitude && selectedReport?.location?.longitude) {
      map.flyTo([selectedReport.location.latitude, selectedReport.location.longitude], 11, {
        duration: 1.2,
      });
    }
  }, [selectedReport, map]);

  useEffect(() => {
    if (targetRegion) {
      map.flyTo(targetRegion.center, targetRegion.zoom, {
        duration: 1.2,
      });
    }
  }, [targetRegion, map]);

  return null;
};

// Viewport change detector to calculate bbox
const ViewportListener: React.FC<{ onBoundsChange?: (bbox: string) => void }> = ({
  onBoundsChange,
}) => {
  const map = useMapEvents({
    moveend: () => {
      if (!onBoundsChange) return;
      const bounds = map.getBounds();
      const southWest = bounds.getSouthWest();
      const northEast = bounds.getNorthEast();

      const minLon = Math.max(-180, Math.min(180, southWest.lng));
      const minLat = Math.max(-90, Math.min(90, southWest.lat));
      const maxLon = Math.max(-180, Math.min(180, northEast.lng));
      const maxLat = Math.max(-90, Math.min(90, northEast.lat));

      if (minLon <= maxLon && minLat <= maxLat) {
        const bbox = `${minLon.toFixed(4)},${minLat.toFixed(4)},${maxLon.toFixed(4)},${maxLat.toFixed(4)}`;
        onBoundsChange(bbox);
      }
    },
  });

  return null;
};

// Custom floating map controls
const MapControls: React.FC = () => {
  const map = useMap();

  const handleZoomIn = () => map.zoomIn();
  const handleZoomOut = () => map.zoomOut();
  const handleReset = () => map.flyTo([20.5937, 78.9629], 5, { duration: 1.2 });
  const handleLocate = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        map.flyTo([pos.coords.latitude, pos.coords.longitude], 11, { duration: 1.2 });
      });
    }
  };

  return (
    <div className="absolute right-4 bottom-8 z-[1000] flex flex-col space-y-2">
      {/* Zoom In / Out */}
      <div className="flex flex-col overflow-hidden rounded-xl border border-slate-200/80 bg-white/95 shadow-lg backdrop-blur-md">
        <button
          type="button"
          onClick={handleZoomIn}
          aria-label="Zoom in"
          className="flex h-9 w-9 items-center justify-center border-b border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors"
        >
          <Plus className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          aria-label="Zoom out"
          className="flex h-9 w-9 items-center justify-center text-slate-700 hover:bg-slate-50 transition-colors"
        >
          <Minus className="h-4 w-4" />
        </button>
      </div>

      {/* Reset India View */}
      <button
        type="button"
        onClick={handleReset}
        title="Reset to India View"
        aria-label="Reset India View"
        className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200/80 bg-white/95 text-slate-700 shadow-lg backdrop-blur-md hover:bg-slate-50 transition-colors"
      >
        <Compass className="h-4 w-4 text-blue-600" />
      </button>

      {/* Locate User */}
      <button
        type="button"
        onClick={handleLocate}
        title="My Location"
        aria-label="Locate my position"
        className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200/80 bg-white/95 text-slate-700 shadow-lg backdrop-blur-md hover:bg-slate-50 transition-colors"
      >
        <Locate className="h-4 w-4 text-slate-700" />
      </button>
    </div>
  );
};

// Create custom Leaflet DivIcon for single incident pins
const createHazardIcon = (severity: string, isSelected: boolean) => {
  const isSevere = severity === 'SEVERE' || severity === 'HIGH';
  const colorClass = isSevere ? 'bg-rose-600' : 'bg-emerald-600';
  const ringClass = isSelected ? 'ring-4 ring-blue-500 scale-125' : 'ring-2 ring-white';

  return L.divIcon({
    className: 'custom-hazard-marker',
    html: `
      <div class="relative flex items-center justify-center transition-transform ${ringClass}">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full ${
          isSevere ? 'bg-rose-400' : 'bg-emerald-400'
        } opacity-60"></span>
        <span class="relative inline-flex rounded-full h-4 w-4 ${colorClass} shadow-md border-2 border-white"></span>
      </div>
    `,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
};

// Create custom Leaflet DivIcon for overlapping cluster badges
const createClusterIcon = (count: number, hasSevere: boolean, isSelected: boolean) => {
  const colorClass = hasSevere ? 'bg-amber-600' : 'bg-blue-600';
  const ringClass = isSelected ? 'ring-4 ring-amber-400 scale-125' : 'ring-2 ring-white';

  return L.divIcon({
    className: 'custom-cluster-marker',
    html: `
      <div class="relative flex items-center justify-center transition-transform ${ringClass}">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full ${
          hasSevere ? 'bg-amber-400' : 'bg-blue-400'
        } opacity-60"></span>
        <span class="relative inline-flex items-center justify-center rounded-full h-7 w-7 ${colorClass} text-white text-xs font-bold shadow-md border-2 border-white">
          ${count > 99 ? '99+' : count}
        </span>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

export const LiveMapContainer: React.FC<LiveMapContainerProps> = ({
  reports,
  selectedReport,
  onSelectReport,
  targetRegion,
  onBoundsChange,
}) => {
  const defaultCenter: [number, number] = [20.5937, 78.9629];
  const defaultZoom = 5;

  // Group overlapping coordinates to handle identical test/incident coordinates cleanly
  const locationGroups = useMemo<IncidentLocationGroup[]>(() => {
    const groups: Record<string, IncidentLocationGroup> = {};

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
        // Prefer report with attached media for cluster spotlight if initial one had no media
        if (
          report.media &&
          report.media.length > 0 &&
          (!groups[key].latestReport.media || groups[key].latestReport.media.length === 0)
        ) {
          groups[key].latestReport = report;
        }
        if (report.severity === 'SEVERE' || report.severity === 'HIGH') {
          groups[key].hasSevere = true;
        }
      }
    }

    return Object.values(groups);
  }, [reports]);

  return (
    <div className="relative h-[calc(100vh-4rem)] w-full overflow-hidden bg-slate-100">
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        zoomControl={false}
        className="h-full w-full z-0"
        attributionControl={true}
      >
        {/* OpenStreetMap Standard Raster Basemap (Keyless Development) */}
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
          maxZoom={19}
        />

        <MapController selectedReport={selectedReport} targetRegion={targetRegion} />
        <ViewportListener onBoundsChange={onBoundsChange} />
        <MapControls />

        {/* Render markers for grouped location points */}
        {locationGroups.map((group) => {
          const isCluster = group.reports.length > 1;
          const isSelected = group.reports.some(
            (r) => r.tracking_id === selectedReport?.tracking_id
          );

          return (
            <Marker
              key={group.key}
              position={[group.latitude, group.longitude]}
              icon={
                isCluster
                  ? createClusterIcon(group.reports.length, group.hasSevere, isSelected)
                  : createHazardIcon(group.latestReport.severity, isSelected)
              }
              eventHandlers={{
                click: () => onSelectReport(group.latestReport),
              }}
            />
          );
        })}
      </MapContainer>
    </div>
  );
};
