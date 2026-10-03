// @vitest-environment jsdom

import React from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SourceParityPage } from "@/pages/SourceParityPage";
import * as weatherGridApi from "@/services/weatherGridApi";

// Mock LocationContext
vi.mock("@/hooks", () => ({
  useLocationScope: () => ({
    currentLocation: {
      name: "Mumbai",
      displayName: "Mumbai, Maharashtra, India",
      lat: 19.076,
      lon: 72.877,
      bbox: "72.5,18.5,73.5,19.5",
    },
    isDefault: false,
    isDetecting: false,
    error: null,
    detectLocation: vi.fn(),
    setCoords: vi.fn(),
  }),
}));

// Mock react-leaflet
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: () => <div data-testid="marker" />,
  Polyline: () => <div data-testid="polyline" />,
  useMap: () => ({ setView: vi.fn(), getZoom: () => 6 }),
  useMapEvents: vi.fn(),
}));

describe("SourceParityPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  const mockHourly = [
    {
      valid_time: "2026-10-02T00:00:00+00:00",
      temperature_2m: 28.5,
      precipitation: 0.0,
      wind_speed_10m: 12.0,
      wind_direction_10m: 210.0,
      pressure_msl: 1012.0,
      wave_height: 1.2,
      wave_direction: 200.0,
      wave_period: 8.0,
    },
    {
      valid_time: "2026-10-02T01:00:00+00:00",
      temperature_2m: 28.0,
      precipitation: 0.2,
      wind_speed_10m: 11.5,
      wind_direction_10m: 215.0,
      pressure_msl: 1012.5,
      wave_height: 1.2,
      wave_direction: 200.0,
      wave_period: 8.0,
    },
  ];

  it("renders source parity header, map, and coordinates inputs", async () => {
    vi.spyOn(weatherGridApi, "fetchWeatherPoint").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      fetched_at: new Date().toISOString(),
      source_name: "OPEN_METEO",
      hourly: mockHourly,
    });

    vi.spyOn(weatherGridApi, "fetchWeatherLiveCheck").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      is_sea: true,
      live_fetched_at: new Date().toISOString(),
      hourly: mockHourly,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <SourceParityPage />
      </QueryClientProvider>
    );

    expect(screen.getByText("Source Parity Verification")).toBeDefined();
    expect(screen.getByTestId("map-container")).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText("110.08 km")).toBeDefined();
    });
  });

  it("fresh data (<6h) with matching values -> green and displays computed age", async () => {
    // Fetched 1 hour ago
    const oneHourAgo = new Date(Date.now() - 1 * 3600 * 1000).toISOString();

    vi.spyOn(weatherGridApi, "fetchWeatherPoint").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      fetched_at: oneHourAgo,
      source_name: "OPEN_METEO",
      hourly: mockHourly,
    });

    vi.spyOn(weatherGridApi, "fetchWeatherLiveCheck").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      is_sea: true,
      live_fetched_at: new Date().toISOString(),
      hourly: mockHourly,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <SourceParityPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Full Source Parity Confirmed")).toBeDefined();
    });

    const badge = screen.getByTestId("parity-badge");
    expect(badge.className).toContain("bg-emerald-950");

    const ageTexts = screen.getAllByText("Stored data age: 1.0 h");
    expect(ageTexts.length).toBeGreaterThan(0);
  });

  it("data older than 6h -> amber with upstream update notice", async () => {
    // Stored 8 hours ago
    const oldFetchTime = new Date(Date.now() - 8 * 3600 * 1000).toISOString();

    vi.spyOn(weatherGridApi, "fetchWeatherPoint").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      fetched_at: oldFetchTime,
      source_name: "OPEN_METEO",
      hourly: mockHourly,
    });

    vi.spyOn(weatherGridApi, "fetchWeatherLiveCheck").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      is_sea: true,
      live_fetched_at: new Date().toISOString(),
      hourly: mockHourly,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <SourceParityPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Source Parity Variance Notice")).toBeDefined();
      expect(
        screen.getByText("Stored data is older than 6 hours and may predate the latest upstream update.")
      ).toBeDefined();
    });

    const badge = screen.getByTestId("parity-badge");
    expect(badge.className).toContain("bg-amber-950");

    const ageTexts = screen.getAllByText("Stored data age: 8.0 h");
    expect(ageTexts.length).toBeGreaterThan(0);
  });

  it("a differing value beyond tolerance -> amber with the variable named", async () => {
    const freshFetchTime = new Date(Date.now() - 30 * 60 * 1000).toISOString(); // 30 mins ago

    // Stored has temperature 28.5 / 28.0, live has temperature 32.0 (difference > 0.5°C tolerance)
    const differingLiveHourly = mockHourly.map((item) => ({
      ...item,
      temperature_2m: 32.0,
    }));

    vi.spyOn(weatherGridApi, "fetchWeatherPoint").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      fetched_at: freshFetchTime,
      source_name: "OPEN_METEO",
      hourly: mockHourly,
    });

    vi.spyOn(weatherGridApi, "fetchWeatherLiveCheck").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      is_sea: true,
      live_fetched_at: new Date().toISOString(),
      hourly: differingLiveHourly,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <SourceParityPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Source Parity Variance Notice")).toBeDefined();
    });

    const badge = screen.getByTestId("parity-badge");
    expect(badge.className).toContain("bg-amber-950");

    // The variable 'temperature' must be named in the variance reason
    expect(screen.getByText(/tolerance in: temperature/i)).toBeDefined();
  });

  it("window start equals the current hour", async () => {
    const now = new Date();
    const closest = new Date(now);
    if (closest.getUTCMinutes() >= 30) {
      closest.setUTCHours(closest.getUTCHours() + 1);
    }
    closest.setUTCMinutes(0, 0, 0, 0);

    // 48 hours starting 10 hours ago and extending 38 hours ahead
    const extendedHourly = Array.from({ length: 48 }, (_, i) => {
      const d = new Date(closest.getTime() + (i - 10) * 3600 * 1000);
      return {
        valid_time: d.toISOString(),
        temperature_2m: 25.0,
        precipitation: 0.0,
        wind_speed_10m: 10.0,
        wind_direction_10m: 180.0,
        pressure_msl: 1012.0,
        wave_height: 1.0,
        wave_direction: 180.0,
        wave_period: 7.0,
      };
    });

    vi.spyOn(weatherGridApi, "fetchWeatherPoint").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      fetched_at: now.toISOString(),
      source_name: "OPEN_METEO",
      hourly: extendedHourly,
    });

    vi.spyOn(weatherGridApi, "fetchWeatherLiveCheck").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      is_sea: true,
      live_fetched_at: now.toISOString(),
      hourly: extendedHourly,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <SourceParityPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Full Source Parity Confirmed")).toBeDefined();
    });

    // Window start equals current UTC hour (closest hour to now)
    const expectedHourStr = `${String(closest.getUTCHours()).padStart(2, "0")}:${String(closest.getUTCMinutes()).padStart(2, "0")} UTC`;
    const timeCells = screen.getAllByText(/\d{2}:\d{2} UTC/);
    expect(timeCells[0].textContent).toContain(expectedHourStr);
  });

  it("labels past rows as earlier today when past hours are in the series", async () => {
    const now = new Date();
    const closest = new Date(now);
    if (closest.getUTCMinutes() >= 30) {
      closest.setUTCHours(closest.getUTCHours() + 1);
    }
    closest.setUTCMinutes(0, 0, 0, 0);

    // 24 rows where the first 10 rows are in the past relative to closest hour
    const pastHourly = Array.from({ length: 24 }, (_, i) => {
      const d = new Date(closest.getTime() + (i - 10) * 3600 * 1000);
      return {
        valid_time: d.toISOString(),
        temperature_2m: 28.0,
        precipitation: 0.0,
        wind_speed_10m: 10.0,
        wind_direction_10m: 180.0,
        pressure_msl: 1012.0,
        wave_height: 1.0,
        wave_direction: 180.0,
        wave_period: 7.0,
      };
    });

    vi.spyOn(weatherGridApi, "fetchWeatherPoint").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      fetched_at: now.toISOString(),
      source_name: "OPEN_METEO",
      hourly: pastHourly,
    });

    vi.spyOn(weatherGridApi, "fetchWeatherLiveCheck").mockResolvedValue({
      requested_latitude: 19.076,
      requested_longitude: 72.877,
      grid_latitude: 20.0,
      grid_longitude: 72.5,
      distance_km: 110.08,
      is_sea: true,
      live_fetched_at: now.toISOString(),
      hourly: pastHourly,
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <SourceParityPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Full Source Parity Confirmed")).toBeDefined();
    });

    const earlierBadges = screen.getAllByText("earlier today");
    expect(earlierBadges.length).toBeGreaterThan(0);
  });
});
