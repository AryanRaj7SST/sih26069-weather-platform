// @vitest-environment jsdom

import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from '@/App';
import { useAuth } from '@/context/AuthContext';
import type { UserProfile } from '@/services/authApi';

vi.mock('@/context/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: vi.fn(),
}));

if (typeof window !== 'undefined' && !window.ResizeObserver) {
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  window.ResizeObserver = ResizeObserver;
  global.ResizeObserver = ResizeObserver;
}

vi.mock('@/services/realtimeService', () => ({
  realtimeService: {
    initialize: vi.fn(),
    disconnect: vi.fn(),
    subscribe: vi.fn().mockReturnValue(() => {}),
  },
}));

vi.mock('@/services/incidentApi', () => ({
  incidentApi: {
    listIncidents: vi.fn().mockResolvedValue({ data: [], pagination: {} }),
    getGeoIncidents: vi.fn().mockResolvedValue({ type: 'FeatureCollection', features: [] }),
    getIncidentDetail: vi.fn().mockResolvedValue({ data: null }),
  },
}));

vi.mock('@/services/dashboardApi', () => ({
  dashboardApi: {
    getSummary: vi.fn().mockResolvedValue({
      data: {
        total_count: 0,
        count_24h: 0,
        last_24h_pct: 0,
        verification: {
          pending_count: 0,
          verified_count: 0,
          verified_rate: 0,
        },
        severity: {},
        category_distribution: [],
        diurnal_distribution: [],
      },
    }),
  },
}));

vi.mock('@/services/reportApi', () => ({
  fetchReportList: vi.fn().mockResolvedValue({ data: [], pagination: {} }),
}));

vi.mock('@/services/analyticsApi', () => ({
  analyticsApi: {
    getTrends: vi.fn().mockResolvedValue({ data: {} }),
    getRegional: vi.fn().mockResolvedValue({ data: [] }),
  },
}));

const mockedUseAuth = vi.mocked(useAuth);

function setAuthState(
  isAuthenticated: boolean,
  role?: 'CITIZEN' | 'OPERATOR' | 'ADMIN',
  logoutFn = vi.fn()
) {
  mockedUseAuth.mockReturnValue({
    token: isAuthenticated ? 'fake-token' : null,
    user: role ? ({ role } as UserProfile) : null,
    operator: null,
    isAuthenticated,
    isOperator: role === 'OPERATOR' || role === 'ADMIN',
    isCitizen: role === 'CITIZEN',
    isAdmin: role === 'ADMIN',
    isLoading: false,
    login: vi.fn(),
    signup: vi.fn(),
    logout: logoutFn,
    updateSavedLocation: vi.fn(),
  });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  window.history.pushState({}, '', '/');
});

describe('Role-based Shell & Route Matrix Tests', () => {
  it('(a) redirects guests visiting protected routes (/live-map, /dashboard, /citizen-dashboard) to /login', async () => {
    setAuthState(false);
    window.history.pushState({}, '', '/dashboard');

    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe('/login');
    });
  });

  it('(b) AuthLayout (/login & /signup) renders NO app route navigation links', async () => {
    setAuthState(false);
    window.history.pushState({}, '', '/login');

    render(<App />);

    expect(screen.queryByText('Live Map')).toBeNull();
    expect(screen.queryByText('Operations Dashboard')).toBeNull();
    expect(screen.queryByText('Verification Queue')).toBeNull();
  });

  it('(c) redirects CITIZEN visiting /dashboard or /admin/queue to /citizen-dashboard', async () => {
    setAuthState(true, 'CITIZEN');
    window.history.pushState({}, '', '/dashboard');

    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe('/citizen-dashboard');
    });
  });

  it('(d) redirects OPERATOR visiting /citizen-dashboard to /admin/queue', async () => {
    setAuthState(true, 'OPERATOR');
    window.history.pushState({}, '', '/citizen-dashboard');

    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe('/admin/queue');
    });
  });

  it('(e) redirects ADMIN visiting /citizen-dashboard to /dashboard', async () => {
    setAuthState(true, 'ADMIN');
    window.history.pushState({}, '', '/citizen-dashboard');

    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe('/dashboard');
    });
  });

  it('(f) StaffNavbar contains Audit Logs and no citizen-only links (My Reports)', async () => {
    setAuthState(true, 'ADMIN');
    window.history.pushState({}, '', '/dashboard');

    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText('Audit Logs').length).toBeGreaterThan(0);
      expect(screen.queryByText('My Reports')).toBeNull();
    });
  });

  it('(h) /welcome redirects to /', async () => {
    setAuthState(false);
    window.history.pushState({}, '', '/welcome');

    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe('/');
    });
  });
});
