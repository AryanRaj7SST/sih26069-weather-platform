import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Navbar } from '@/components/layout/Navbar';
import { MobileBottomNav } from '@/components/layout/MobileBottomNav';
import { MapHeaderCard } from '@/features/map/MapHeaderCard';
import { MapFilterBar, MapFilters } from '@/features/map/MapFilterBar';
import { MapLegend } from '@/features/map/MapLegend';
import { SelectedIncidentCard } from '@/features/map/SelectedIncidentCard';
import { LiveMapContainer } from '@/features/map/LiveMapContainer';
import { fetchReportList } from '@/services/reportApi';
import { ReportDetailData, ReportListQueryParams } from '@/types';
import { Info, AlertTriangle, Loader2 } from 'lucide-react';

const REGION_BOUNDS: Record<string, { center: [number, number]; zoom: number; bbox?: string }> = {
  ALL: {
    center: [20.5937, 78.9629],
    zoom: 5,
  },
  MH: {
    center: [19.7515, 75.7139],
    zoom: 7,
    bbox: '72.6,15.6,80.9,22.0',
  },
  TN: {
    center: [11.1271, 78.6569],
    zoom: 7,
    bbox: '76.2,8.0,80.3,13.5',
  },
  DL: {
    center: [28.7041, 77.1025],
    zoom: 10,
    bbox: '76.8,28.4,77.4,28.9',
  },
  KA: {
    center: [15.3173, 75.7139],
    zoom: 7,
    bbox: '74.0,11.5,78.6,18.5',
  },
  KL: {
    center: [10.8505, 76.2711],
    zoom: 7,
    bbox: '74.8,8.3,77.4,12.8',
  },
  AS: {
    center: [26.2006, 92.9376],
    zoom: 7,
    bbox: '89.7,24.1,96.0,28.2',
  },
  RJ: {
    center: [27.0238, 74.2179],
    zoom: 6,
    bbox: '69.5,23.0,78.3,30.2',
  },
};

export const LiveMapPage: React.FC = () => {
  const [filters, setFilters] = useState<MapFilters>({
    timeRange: '24h',
    hazard: 'ALL',
    state: 'ALL',
    status: 'ALL',
  });

  const [selectedReport, setSelectedReport] = useState<ReportDetailData | null>(null);

  // Compute from_date based on timeRange filter
  const fromDate = useMemo(() => {
    const now = Date.now();
    if (filters.timeRange === '24h') {
      return new Date(now - 24 * 60 * 60 * 1000).toISOString();
    }
    if (filters.timeRange === '48h') {
      return new Date(now - 48 * 60 * 60 * 1000).toISOString();
    }
    if (filters.timeRange === '7d') {
      return new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString();
    }
    return undefined;
  }, [filters.timeRange]);

  // Construct query parameters matching the real backend GET /api/v1/reports
  const queryParams: ReportListQueryParams = useMemo(() => {
    const params: ReportListQueryParams = {
      page: 1,
      page_size: 100,
    };

    if (fromDate) {
      params.from_date = fromDate;
    }

    if (filters.hazard !== 'ALL') {
      params.category = filters.hazard;
    }

    if (filters.status !== 'ALL') {
      params.status = filters.status;
    }

    // Map regional filter to spatial bounding box
    const regionInfo = REGION_BOUNDS[filters.state];
    if (regionInfo?.bbox) {
      params.bbox = regionInfo.bbox;
    }

    return params;
  }, [filters, fromDate]);

  // Real React Query integration
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['live-map-reports', queryParams],
    queryFn: () => fetchReportList(queryParams),
    staleTime: 1000 * 30, // 30 seconds
    refetchOnWindowFocus: false,
  });

  const reports = useMemo(() => data?.data || [], [data]);
  const totalRecords = data?.pagination?.total_records ?? reports.length;
  const targetRegion = REGION_BOUNDS[filters.state];

  // Calculate unique coordinate locations
  const uniqueLocationsCount = useMemo(() => {
    const set = new Set<string>();
    for (const r of reports) {
      if (r.location?.latitude != null && r.location?.longitude != null) {
        set.add(`${r.location.latitude.toFixed(4)}_${r.location.longitude.toFixed(4)}`);
      }
    }
    return set.size;
  }, [reports]);

  // Transparent, truthful status message
  const statusLabel = useMemo(() => {
    if (isLoading) {
      return 'Loading incident reports...';
    }
    if (isError) {
      return error instanceof Error ? error.message : 'Failed to retrieve live reports';
    }
    if (totalRecords === 0) {
      return '0 Incidents in Selected View';
    }
    if (totalRecords > reports.length) {
      return `Showing ${reports.length} of ${totalRecords} Incidents (${uniqueLocationsCount} Locations on Map)`;
    }
    return `${reports.length} Incident${reports.length > 1 ? 's' : ''} on Map (${uniqueLocationsCount} Location${uniqueLocationsCount > 1 ? 's' : ''})`;
  }, [isLoading, isError, error, totalRecords, reports.length, uniqueLocationsCount]);

  return (
    <div className="relative flex h-screen w-screen flex-col overflow-hidden bg-slate-100 text-slate-900">
      {/* Navigation Header */}
      <Navbar />

      {/* Main Map Viewport */}
      <main className="relative flex-1 w-full overflow-hidden">
        {/* Fullscreen Map Layer */}
        <LiveMapContainer
          reports={reports}
          selectedReport={selectedReport}
          onSelectReport={(report) => setSelectedReport(report)}
          targetRegion={targetRegion}
        />

        {/* Floating Top Header & Filter Controls matching Stitch */}
        <div className="absolute top-4 left-4 z-[900] flex flex-col space-y-3 pointer-events-none max-w-[calc(100vw-2rem)] sm:max-w-xl">
          <div className="pointer-events-auto">
            <MapHeaderCard />
          </div>
          <div className="pointer-events-auto">
            <MapFilterBar filters={filters} onFilterChange={setFilters} />
          </div>
        </div>

        {/* Floating Data Status Banner */}
        <div className="absolute top-4 right-4 z-[900] hidden lg:block pointer-events-auto">
          <div className="flex items-center space-x-2 rounded-xl border border-slate-200/80 bg-white/95 px-3 py-2 text-xs font-semibold text-slate-700 shadow-md backdrop-blur-md">
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
                <span>{statusLabel}</span>
              </>
            ) : isError ? (
              <>
                <AlertTriangle className="h-4 w-4 text-rose-600" />
                <span className="text-rose-700">{statusLabel}</span>
              </>
            ) : (
              <>
                <Info className="h-4 w-4 text-blue-600 shrink-0" />
                <span>{statusLabel}</span>
              </>
            )}
          </div>
        </div>

        {/* Floating Legend (Bottom Left on Desktop) */}
        <div className="absolute bottom-6 left-4 z-[900] hidden sm:block pointer-events-auto">
          <MapLegend />
        </div>

        {/* Selected Incident Card (Floating Right on Desktop / Bottom Sheet on Mobile) */}
        {selectedReport && (
          <div className="absolute bottom-16 sm:bottom-6 right-4 sm:right-6 z-[1000] pointer-events-auto max-w-[calc(100vw-2rem)] sm:max-w-md">
            <SelectedIncidentCard
              report={selectedReport}
              onClose={() => setSelectedReport(null)}
            />
          </div>
        )}
      </main>

      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />
    </div>
  );
};
