// Comprehensive API Client, Transport, HTTP Boundary & Backward Compatibility Tests

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { incidentApi } from '../services/incidentApi';
import { ApiError } from '../services/client';
import { normalizeParams } from '../lib/queryKeys';
import {
  submitCitizenReport,
  fetchReportByTrackingId,
  fetchReportList,
  verifyReport,
  rejectReport,
  markDuplicateReport,
  placeReportUnderReview,
} from '../services/reportApi';

describe('1. API Client HTTP Boundary & Method Matrix', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('GET /api/v1/incidents - serializes query parameters and excludes ALL/empty filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: [],
        pagination: { page: 1, page_size: 20, total_records: 0, total_pages: 0, has_next: false, has_prev: false },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    await incidentApi.listIncidents({
      page: 2,
      page_size: 50,
      category: 'FLOOD_WATERLOGGING',
      severity: 'ALL',
      verification_status: 'VERIFIED',
      min_credibility: 0.75,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/incidents?');
    expect(calledUrl).toContain('page=2');
    expect(calledUrl).toContain('page_size=50');
    expect(calledUrl).toContain('category=FLOOD_WATERLOGGING');
    expect(calledUrl).toContain('verification_status=VERIFIED');
    expect(calledUrl).toContain('min_credibility=0.75');
    expect(calledUrl).not.toContain('severity=ALL');
  });

  it('GET /api/v1/incidents/{id} - encodes ID and parses public detail response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { id: 'rpt-101', tracking_id: 'RPT-20260829-0101', title: 'Heavy Rainfall' },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getIncidentDetail('rpt-101');
    expect(res.data.id).toBe('rpt-101');
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/incidents/rpt-101');
  });

  it('GET /api/v1/incidents/{id}/operator-detail - requests operator audit endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { id: 'rpt-101', verification_history: [] },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getIncidentOperatorDetail('rpt-101');
    expect(res.data.id).toBe('rpt-101');
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/incidents/rpt-101/operator-detail');
  });

  it('GET /api/v1/incidents/{id}/credibility - requests machine credibility sub-resource', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { incident_id: 'rpt-101', score: 0.88, is_machine_assessed: true },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getIncidentCredibility('rpt-101');
    expect(res.data.score).toBe(0.88);
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/incidents/rpt-101/credibility');
  });

  it('GET /api/v1/incidents/{id}/intelligence - requests orchestration readiness and stages', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { incident_id: 'rpt-101', overall_readiness: 'INTELLIGENCE_READY', stages: {} },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getIncidentIntelligence('rpt-101');
    expect(res.data.overall_readiness).toBe('INTELLIGENCE_READY');
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/incidents/rpt-101/intelligence');
  });

  it('GET /api/v1/incidents/{id}/evidence - paginates digital evidence items', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: [{ link_id: 'lnk-1', relationship: 'SUPPORTING' }],
        pagination: { page: 2, page_size: 10, total_records: 15, total_pages: 2, has_next: false, has_prev: true },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getIncidentEvidence('rpt-101', 2, 10);
    expect(res.data).toHaveLength(1);
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/incidents/rpt-101/evidence?page=2&page_size=10');
  });

  it('GET /api/v1/incidents/{id}/observations - paginates physical AWS sensor readings', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: [{ observation_id: 'obs-1', relationship: 'CORROBORATING' }],
        pagination: { page: 1, page_size: 10, total_records: 1, total_pages: 1, has_next: false, has_prev: false },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getIncidentObservations('rpt-101', 1, 10);
    expect(res.data).toHaveLength(1);
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/incidents/rpt-101/observations?page=1&page_size=10');
  });

  it('GET /api/v1/incidents/{id}/cluster - requests semantic duplicate cluster topology', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { cluster_id: 'cls-1', cluster_code: 'CLS-001', total_member_count: 3, members: [] },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getIncidentCluster('rpt-101');
    expect(res.data.cluster_code).toBe('CLS-001');
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/incidents/rpt-101/cluster');
  });

  it('GET /api/v1/geo/incidents - requests bounded GeoJSON FeatureCollection', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        type: 'FeatureCollection',
        features: [],
      }),
    });
    global.fetch = fetchMock;

    const res = await incidentApi.getGeoIncidents('72.8,18.9,73.0,19.2', { status: 'VERIFIED', hours_ago: 24 });
    expect(res.type).toBe('FeatureCollection');
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/geo/incidents?');
    expect(calledUrl).toContain('bbox=72.8%2C18.9%2C73.0%2C19.2');
    expect(calledUrl).toContain('status=VERIFIED');
    expect(calledUrl).toContain('hours_ago=24');
  });

  it('GET /api/v1/verification/queue - requests priority-ranked operator triage queue', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: [],
        pagination: { page: 1, page_size: 20, total_records: 0, total_pages: 0, has_next: false, has_prev: false },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    await incidentApi.getVerificationQueue({ priority: 'HIGH', page: 1, page_size: 20 });
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/verification/queue?page=1&page_size=20&priority=HIGH');
  });
});

describe('2. Operator Verification Mutations Matrix', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('POST /api/v1/verification/{id}/verify - executes verify action with broadcast toggle', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { id: 'rpt-001', verification: { status: 'VERIFIED' } },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    await incidentApi.verifyIncident('rpt-001', { notes: 'Confirmed by IMD', broadcast_alert: true });
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/verification/rpt-001/verify');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      notes: 'Confirmed by IMD',
      broadcast_alert: true,
    });
  });

  it('POST /api/v1/verification/{id}/reject - executes reject action with mandatory reason code', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { id: 'rpt-002', verification: { status: 'REJECTED' } },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    await incidentApi.rejectIncident('rpt-002', { rejection_reason: 'HOAX_SPAM', notes: 'Old stock photo' });
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/verification/rpt-002/reject');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      rejection_reason: 'HOAX_SPAM',
      notes: 'Old stock photo',
    });
  });

  it('POST /api/v1/verification/{id}/mark-duplicate - links to primary report anchor', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { id: 'rpt-003', verification: { status: 'DUPLICATE' } },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    await incidentApi.markDuplicateIncident('rpt-003', { primary_report_id: 'rpt-001', notes: 'Duplicate submission' });
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/verification/rpt-003/mark-duplicate');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      primary_report_id: 'rpt-001',
      notes: 'Duplicate submission',
    });
  });

  it('POST /api/v1/verification/{id}/review - claims triage into UNDER_REVIEW', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { id: 'rpt-004', verification: { status: 'UNDER_REVIEW' } },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    await incidentApi.reviewIncident('rpt-004', { notes: 'Claimed by Operator 5' });
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/verification/rpt-004/review');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ notes: 'Claimed by Operator 5' });
  });
});

describe('3. Standardized HTTP Status & Error Code Normalization', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  const testCases: { status: number; expectedCode: string }[] = [
    { status: 400, expectedCode: 'BAD_REQUEST' },
    { status: 404, expectedCode: 'RESOURCE_NOT_FOUND' },
    { status: 409, expectedCode: 'RESOURCE_CONFLICT' },
    { status: 422, expectedCode: 'VALIDATION_ERROR' },
    { status: 429, expectedCode: 'RATE_LIMITED' },
    { status: 500, expectedCode: 'INTERNAL_SERVER_ERROR' },
    { status: 503, expectedCode: 'SERVICE_UNAVAILABLE' },
  ];

  testCases.forEach(({ status, expectedCode }) => {
    it(`normalizes HTTP ${status} into ApiError with code '${expectedCode}'`, async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          error: { code: expectedCode, message: `Sample error for HTTP ${status}` },
        }),
      });

      try {
        await incidentApi.getIncidentDetail('test-id');
        expect.unreachable('Should have thrown ApiError');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(status);
        expect(apiErr.code).toBe(expectedCode);
      }
    });
  });

  it('handles 429 Rate Limiting with safe user message', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({}),
    });

    try {
      await incidentApi.listIncidents();
      expect.unreachable('Should have thrown ApiError');
    } catch (err: unknown) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(429);
      expect(apiErr.code).toBe('RATE_LIMITED');
      expect(apiErr.message).toContain('limit exceeded');
    }
  });
});

describe('4. Parameter Normalization Edge Cases (0, false, arrays, dates)', () => {
  it('preserves legitimate numeric 0 values without stripping them', () => {
    const params = { min_credibility: 0, page: 0 };
    const normalized = normalizeParams(params);
    expect(normalized).toEqual({ min_credibility: 0, page: 0 });
  });

  it('preserves legitimate boolean false values', () => {
    const params = { is_verified: false, broadcast: true };
    const normalized = normalizeParams(params);
    expect(normalized).toEqual({ broadcast: true, is_verified: false });
  });

  it('preserves ISO date strings and array values', () => {
    const params = { from_date: '2026-08-29T00:00:00.000Z', tags: ['flood', 'mumbai'] };
    const normalized = normalizeParams(params);
    expect(normalized).toEqual({ from_date: '2026-08-29T00:00:00.000Z', tags: ['flood', 'mumbai'] });
  });

  it('strips only undefined, null, empty string, and ALL', () => {
    const params = {
      validStr: 'valid',
      emptyStr: '',
      nullVal: null,
      undefVal: undefined,
      allVal: 'ALL',
    };
    const normalized = normalizeParams(params);
    expect(normalized).toEqual({ validStr: 'valid' });
  });
});

describe('5. Backward Compatibility Facade (reportApi)', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('submitCitizenReport posts multipart FormData to /api/v1/reports', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { id: 'rpt-sub-1', tracking_id: 'RPT-20260829-0001', submitted_at: '2026-08-29T12:00:00Z', media_count: 0 },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const res = await submitCitizenReport({
      latitude: 19.076,
      longitude: 72.8777,
      category_code: 'FLOOD_WATERLOGGING',
      severity: 'HIGH',
      title: 'Waterlogging in Kurla',
    });

    expect(res.success).toBe(true);
    expect(res.data.tracking_id).toBe('RPT-20260829-0001');
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/reports');
  });

  it('fetchReportByTrackingId looks up report by tracking ID', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { id: 'rpt-1', tracking_id: 'RPT-20260829-0001', title: 'Waterlogging in Kurla' },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    const res = await fetchReportByTrackingId('RPT-20260829-0001');
    expect(res.data.tracking_id).toBe('RPT-20260829-0001');
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/reports/RPT-20260829-0001');
  });

  it('fetchReportList requests /api/v1/reports with filter query string', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: [],
        pagination: { page: 1, page_size: 20, total_records: 0, total_pages: 0, has_next: false, has_prev: false },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    await fetchReportList({ category: 'HEAVY_RAINFALL', severity: 'SEVERE' });
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/reports?category=HEAVY_RAINFALL&severity=SEVERE');
  });

  it('getGeoIncidents requests /api/v1/geo/incidents with optional bbox and filter query params', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        type: 'FeatureCollection',
        features: [],
      }),
    });
    global.fetch = fetchMock;

    await incidentApi.getGeoIncidents(undefined, { category: 'FLOOD_WATERLOGGING', status: 'VERIFIED', hours_ago: 48 });
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/geo/incidents?status=VERIFIED&category=FLOOD_WATERLOGGING&hours_ago=48');
  });

  it('verifyReport, rejectReport, markDuplicateReport, placeReportUnderReview delegate seamlessly', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        data: { id: 'rpt-1', verification: { status: 'VERIFIED' } },
        meta: { timestamp: '2026-08-29T12:00:00Z' },
      }),
    });
    global.fetch = fetchMock;

    await verifyReport('rpt-1', 'Notes', true);
    await rejectReport('rpt-1', 'HOAX_SPAM', 'Notes');
    await markDuplicateReport('rpt-1', 'rpt-primary', 'Notes');
    await placeReportUnderReview('rpt-1', 'Notes');

    expect(fetchMock).toHaveBeenCalledTimes(4);
  });
});
