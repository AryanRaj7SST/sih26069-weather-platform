import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient } from '@tanstack/react-query';
import { incidentApi } from '@/services/incidentApi';
import { incidentKeys } from '@/lib/queryKeys';
import { geoJSONToMapPoints } from '@/features/map/adapters';

describe('LiveMap GeoJSON & Lazy Detail Loading Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('J. LiveMap queries GeoJSON layer with active viewport / region bounding box', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [75.7139, 19.7515] },
            properties: {
              id: 'inc-mh-1',
              tracking_id: 'RPT-MH-001',
              title: 'Heavy Rainfall in Aurangabad',
              category_code: 'HEAVY_RAINFALL',
              severity: 'HIGH',
              credibility_score: 0.88,
              verification_status: 'VERIFIED',
              occurred_at: '2026-08-30T09:00:00Z',
              location_name: 'Aurangabad, MH',
            },
          },
        ],
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getGeoIncidents('72.6,15.6,80.9,22.0', {
      category: 'HEAVY_RAINFALL',
      hours_ago: 24,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(res.type).toBe('FeatureCollection');
    expect(res.features).toHaveLength(1);

    const points = geoJSONToMapPoints(res);
    expect(points[0].location.latitude).toBe(19.7515);
    expect(points[0].location.longitude).toBe(75.7139);
    expect(points[0].title).toBe('Heavy Rainfall in Aurangabad');
  });

  it('K & L. Selecting a marker triggers detail query and populates multimedia and description', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: {
          id: 'inc-mh-1',
          tracking_id: 'RPT-MH-001',
          title: 'Heavy Rainfall in Aurangabad',
          description: 'Flash flooding recorded on Jalna road with 2 feet water accumulation.',
          severity: 'HIGH',
          verification_status: 'VERIFIED',
          occurred_at: '2026-08-30T09:00:00Z',
          location: {
            latitude: 19.7515,
            longitude: 75.7139,
            name: 'Aurangabad, MH',
          },
          category: {
            code: 'HEAVY_RAINFALL',
            title: 'Heavy Rainfall',
          },
          media: [
            {
              id: 'med-1',
              url: 'https://minio.sih.gov.in/weather-media/aurangabad_flood.jpg',
              media_type: 'IMAGE',
              mime_type: 'image/jpeg',
            },
          ],
        },
        meta: { timestamp: '2026-08-30T09:05:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const detail = await incidentApi.getIncidentDetail('inc-mh-1');
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/incidents/inc-mh-1'),
      expect.anything()
    );
    expect(detail.data.media).toHaveLength(1);
    expect(detail.data.media[0].url).toContain('aurangabad_flood.jpg');
    expect(detail.data.description).toContain('Flash flooding recorded on Jalna road');
  });

  it('M. Handles detail fetch failure safely with initial MapIncidentPoint fallback and no uncaught crash', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Don't retry in unit tests
        },
      },
    });

    // A. Mock successful GeoJSON loading
    const geoResponse = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [76.1320, 11.6854] },
          properties: {
            id: 'inc-err-1',
            tracking_id: 'RPT-ERR-001',
            title: 'Landslide Warning',
            category_code: 'LANDSLIDE',
            severity: 'SEVERE',
            credibility_score: 0.92,
            verification_status: 'UNDER_REVIEW',
            occurred_at: '2026-08-30T08:00:00Z',
            location_name: 'Wayanad, KL',
          },
        },
      ],
    };

    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes('/geo/incidents')) {
        return {
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => geoResponse,
        };
      }
      if (url.includes('/incidents/inc-err-1')) {
        // D. Mock getIncidentDetail() to reject
        return {
          ok: false,
          status: 500,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            error: {
              code: 'INTERNAL_SERVER_ERROR',
              message: 'Failed to retrieve detailed incident record',
            },
          }),
        };
      }
      throw new Error(`Unhandled url: ${url}`);
    });
    global.fetch = fetchMock;

    // B. Load GeoJSON through QueryClient
    const geoData = await queryClient.fetchQuery({
      queryKey: incidentKeys.geo('', {}),
      queryFn: () => incidentApi.getGeoIncidents(),
    });
    const mapPoints = geoJSONToMapPoints(geoData);
    expect(mapPoints).toHaveLength(1);

    // C. Select a marker
    const selectedPoint = mapPoints[0];
    expect(selectedPoint.id).toBe('inc-err-1');

    // E. Execute lazy detail query via QueryClient (simulating LiveMapPage useQuery)
    let detailError = null;
    try {
      await queryClient.fetchQuery({
        queryKey: incidentKeys.detail(selectedPoint.id),
        queryFn: () => incidentApi.getIncidentDetail(selectedPoint.id),
      });
    } catch (err) {
      detailError = err;
    }

    // F. Verify error handling and state stability
    expect(detailError).not.toBeNull();

    // Query state in cache is recorded as error and NOT left in fetching state (no infinite loading)
    const queryState = queryClient.getQueryState(incidentKeys.detail(selectedPoint.id));
    expect(queryState?.status).toBe('error');
    expect(queryState?.fetchStatus).toBe('idle');

    // LiveMap selectedReport fallback logic evaluates safely
    const detailResponse = queryClient.getQueryData<{ data?: unknown }>(
      incidentKeys.detail(selectedPoint.id)
    );
    const selectedReport = (detailResponse?.data as typeof selectedPoint) || selectedPoint;

    // Verify all essential card fields remain intact and usable
    expect(selectedReport.id).toBe('inc-err-1');
    expect(selectedReport.tracking_id).toBe('RPT-ERR-001');
    expect(selectedReport.title).toBe('Landslide Warning');
    expect(selectedReport.location.latitude).toBe(11.6854);
    expect(selectedReport.location.longitude).toBe(76.1320);
    expect(selectedReport.location.name).toBe('Wayanad, KL');
    expect(selectedReport.severity).toBe('SEVERE');
    expect(selectedReport.verification_status).toBe('UNDER_REVIEW');
    expect(selectedReport.category?.code).toBe('LANDSLIDE');
  });
});
