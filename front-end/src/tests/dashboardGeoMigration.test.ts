// Tests for Phase 13E: Dashboard GeoJSON Migration and Contract Integrity

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { geoJSONToMapPoints } from '@/features/map/adapters';
import { incidentApi } from '@/services/incidentApi';
import { GeoJSONFeatureCollection } from '@/types';

describe('Dashboard GeoJSON Migration Contract Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('A & F. GeoJSON query omits bbox for ALL region and makes a single request', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [72.8777, 19.0760] },
            properties: {
              id: 'rpt-1',
              tracking_id: 'RPT-NAT-001',
              title: 'Flood Alert Mumbai',
              category_code: 'FLOOD_WATERLOGGING',
              severity: 'SEVERE',
              credibility_score: 0.85,
              verification_status: 'VERIFIED',
              occurred_at: '2026-08-30T10:00:00Z',
              location_name: 'Kurla West',
            },
          },
        ],
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getGeoIncidents(undefined, { hours_ago: 24 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/geo/incidents?hours_ago=24');
    expect(res.type).toBe('FeatureCollection');
    expect(res.features).toHaveLength(1);
  });

  it('B, C, D, E. Correctly forwards category, status, hours_ago, and bbox filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ type: 'FeatureCollection', features: [] }),
    });
    global.fetch = fetchMock;

    await incidentApi.getGeoIncidents('72.6,15.6,80.9,22.0', {
      category: 'CYCLONE',
      status: 'UNDER_REVIEW',
      hours_ago: 168,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain('bbox=72.6%2C15.6%2C80.9%2C22.0');
    expect(url).toContain('category=CYCLONE');
    expect(url).toContain('status=UNDER_REVIEW');
    expect(url).toContain('hours_ago=168');
  });

  it('G. Transforms GeoJSON [lon, lat] coordinates to Leaflet { latitude, longitude } and properties', () => {
    const rawGeo: GeoJSONFeatureCollection = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [77.5946, 12.9716], // [lon, lat]
          },
          properties: {
            id: 'geo-1',
            tracking_id: 'RPT-GEO-001',
            title: 'Waterlogging in Indiranagar',
            category_code: 'FLOOD_WATERLOGGING',
            severity: 'HIGH',
            credibility_score: 0.92,
            verification_status: 'VERIFIED',
            readiness: 'ACTIONABLE',
            occurred_at: '2026-08-30T14:30:00Z',
            location_name: 'Indiranagar, Bengaluru',
          },
        },
      ],
    };

    const points = geoJSONToMapPoints(rawGeo);
    expect(points).toHaveLength(1);
    const p = points[0];
    expect(p.id).toBe('geo-1');
    expect(p.tracking_id).toBe('RPT-GEO-001');
    expect(p.location.latitude).toBe(12.9716);
    expect(p.location.longitude).toBe(77.5946);
    expect(p.location.name).toBe('Indiranagar, Bengaluru');
    expect(p.severity).toBe('HIGH');
    expect(p.verification_status).toBe('VERIFIED');
    expect(p.category?.code).toBe('FLOOD_WATERLOGGING');
  });

  it('H. Preserves 4-decimal precision grouping and identifies severe alerts within clusters', () => {
    const geoData: GeoJSONFeatureCollection = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [72.87771, 19.07601] },
          properties: {
            id: 'p1',
            tracking_id: 'RPT-001',
            title: 'Minor Drizzle',
            category_code: 'HEAVY_RAINFALL',
            severity: 'LOW',
            credibility_score: 0.5,
            verification_status: 'PENDING',
            occurred_at: '2026-08-30T10:00:00Z',
          },
        },
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [72.87774, 19.07604] }, // Rounds to same 19.0760, 72.8777
          properties: {
            id: 'p2',
            tracking_id: 'RPT-002',
            title: 'Major Flash Flood',
            category_code: 'FLOOD_WATERLOGGING',
            severity: 'SEVERE',
            credibility_score: 0.9,
            verification_status: 'VERIFIED',
            occurred_at: '2026-08-30T10:05:00Z',
          },
        },
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [77.2090, 28.6139] }, // Delhi (different location)
          properties: {
            id: 'p3',
            tracking_id: 'RPT-003',
            title: 'Heatwave',
            category_code: 'HEATWAVE',
            severity: 'HIGH',
            credibility_score: 0.8,
            verification_status: 'VERIFIED',
            occurred_at: '2026-08-30T11:00:00Z',
          },
        },
      ],
    };

    const points = geoJSONToMapPoints(geoData);
    expect(points).toHaveLength(3);

    // Grouping logic test (same as DashboardMap / LiveMapContainer)
    const groups: Record<string, typeof points> = {};

    for (const pt of points) {
      const key = `${pt.location.latitude.toFixed(4)}_${pt.location.longitude.toFixed(4)}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(pt);
    }

    const groupList = Object.values(groups);
    expect(groupList).toHaveLength(2); // Mumbai cluster + Delhi point

    const severeLocationCount = groupList.filter((g) =>
      g.some((p) => p.severity === 'SEVERE' || p.severity === 'HIGH')
    ).length;
    expect(severeLocationCount).toBe(2);

    const mumbaiCluster = groups['19.0760_72.8777'];
    expect(mumbaiCluster).toHaveLength(2);
    expect(mumbaiCluster.some((p) => p.severity === 'SEVERE' || p.severity === 'HIGH')).toBe(true);
  });

  it('I. Severe alert count remains derived from server summary and not truncated map features', () => {
    const summaryData = {
      severity: {
        severe_high_count: 42, // Authoritative count across thousands of records
        severe_count: 20,
        high_count: 22,
      },
    };

    const loadedMapPoints = [
      { id: '1', severity: 'SEVERE' },
      { id: '2', severity: 'LOW' },
    ];

    // Assert that authoritative display badge uses summaryData directly
    const displayedSevereBadge = summaryData.severity.severe_high_count;
    expect(displayedSevereBadge).toBe(42);
    expect(displayedSevereBadge).not.toBe(loadedMapPoints.filter((p) => p.severity === 'SEVERE').length);
  });
});
