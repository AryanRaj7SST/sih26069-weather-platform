// Hierarchical React Query Keys with Deterministic Normalization

export function normalizeParams<T extends Record<string, unknown>>(params?: T): Record<string, unknown> | undefined {
  if (!params) return undefined;
  const normalized: Record<string, unknown> = {};
  Object.keys(params)
    .sort()
    .forEach((key) => {
      const val = params[key];
      if (val !== undefined && val !== null && val !== '' && val !== 'ALL') {
        normalized[key] = val;
      }
    });
  return Object.keys(normalized).length > 0 ? normalized : undefined;
}

export const incidentKeys = {
  all: ['incidents'] as const,
  lists: () => [...incidentKeys.all, 'list'] as const,
  list: (params?: Record<string, unknown>) => [...incidentKeys.lists(), normalizeParams(params)] as const,
  details: () => [...incidentKeys.all, 'detail'] as const,
  detail: (id: string) => [...incidentKeys.details(), id] as const,
  credibility: (id: string) => [...incidentKeys.detail(id), 'credibility'] as const,
  intelligence: (id: string) => [...incidentKeys.detail(id), 'intelligence'] as const,
  evidence: (id: string, page?: number) => [...incidentKeys.detail(id), 'evidence', page || 1] as const,
  observations: (id: string, page?: number) => [...incidentKeys.detail(id), 'observations', page || 1] as const,
  cluster: (id: string) => [...incidentKeys.detail(id), 'cluster'] as const,
  geoAll: () => ['geo-incidents'] as const,
  geo: (bbox: string, params?: Record<string, unknown>) => [...incidentKeys.geoAll(), bbox, normalizeParams(params)] as const,
  verificationQueues: () => ['verification-queue'] as const,
  verificationQueueList: (params?: Record<string, unknown>) => [...incidentKeys.verificationQueues(), normalizeParams(params)] as const,
};

export const dashboardKeys = {
  all: ['dashboard'] as const,
  summaries: () => [...dashboardKeys.all, 'summary'] as const,
  summary: (params?: Record<string, unknown>) => [...dashboardKeys.summaries(), normalizeParams(params)] as const,
};

export const analyticsKeys = {
  all: ['analytics'] as const,
  trendsAll: () => [...analyticsKeys.all, 'trends'] as const,
  trends: (params?: Record<string, unknown>) => [...analyticsKeys.trendsAll(), normalizeParams(params)] as const,
  regionalAll: () => [...analyticsKeys.all, 'regional'] as const,
  regional: (params?: Record<string, unknown>) => [...analyticsKeys.regionalAll(), normalizeParams(params)] as const,
};
