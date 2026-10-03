// @vitest-environment jsdom

import React from "react";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NationalMapPage } from "@/pages/NationalMapPage";
import { WeatherTimeSlider } from "@/components/map/WeatherTimeSlider";
import { WeatherColorLegend } from "@/components/map/WeatherColorLegend";
import * as weatherGridApi from "@/services/weatherGridApi";
import { incidentApi } from "@/services/incidentApi";
import { routeApi } from "@/services/routeApi";
import { GeoJSONFeatureCollection } from "@/types";

// Mock canvas getContext in jsdom
HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
  clearRect: vi.fn(),
  beginPath: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  stroke: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  translate: vi.fn(),
  rotate: vi.fn(),
  scale: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  fillText: vi.fn(),
  strokeText: vi.fn(),
  measureText: vi.fn().mockReturnValue({ width: 20 }),
}) as unknown as typeof HTMLCanvasElement.prototype.getContext;

// Mock react-leaflet
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children }: { children?: React.ReactNode }) => <div data-testid="incident-marker">{children}</div>,
  Popup: ({ children }: { children?: React.ReactNode }) => <div data-testid="popup">{children}</div>,
  GeoJSON: () => <div data-testid="geojson-layer" />,
  Circle: () => <div data-testid="circle-layer" />,
  useMap: () => ({
    getPanes: () => ({
      overlayPane: document.createElement("div"),
    }),
    latLngToLayerPoint: (coords: [number, number]) => ({ x: coords[1] * 10, y: coords[0] * 10 }),
    latLngToContainerPoint: () => ({ x: 100, y: 100 }),
    on: vi.fn(),
    off: vi.fn(),
    getSize: () => ({ x: 1000, y: 800 }),
    getZoom: () => 5,
  }),
}));

describe("NationalMapPage Weather Layers & Components", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  const mockTimes: weatherGridApi.WeatherTimesResponse = {
    valid_times: [
      "2026-10-01T20:00:00+00:00",
      "2026-10-02T00:00:00+00:00",
      "2026-10-02T06:00:00+00:00",
      "2026-10-02T12:00:00+00:00",
    ],
    latest_fetched_at: "2026-10-01T22:30:00+00:00",
    count: 4,
  };

  const mockWeatherFeatures: weatherGridApi.WeatherGridFeatureCollection = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [72.5, 19.0] },
        properties: {
          latitude: 19.0,
          longitude: 72.5,
          valid_time: "2026-10-02T00:00:00+00:00",
          temperature_2m: 29.2,
          precipitation: 2.5,
          wind_speed_10m: 18.0,
          wind_direction_10m: 230,
          pressure_msl: 1011.5,
        },
      },
    ],
  };

  const mockMarineFeatures: weatherGridApi.WeatherGridFeatureCollection = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [70.0, 18.0] },
        properties: {
          latitude: 18.0,
          longitude: 70.0,
          valid_time: "2026-10-02T00:00:00+00:00",
          wave_height: 2.1,
          wave_direction: 240,
          wave_period: 7.5,
        },
      },
    ],
  };

  const mockIncidents: GeoJSONFeatureCollection = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [77.2, 28.6] },
        properties: {
          id: "inc-1",
          tracking_id: "TRK-001",
          title: "Delhi Severe Waterlogging",
          category_code: "FLOOD",
          severity: "SEVERE",
          verification_status: "VERIFIED",
          credibility_score: 0.92,
          credibility_reason: "Verified by 3 AWS stations",
          occurred_at: "2026-10-01T12:00:00Z",
        },
      },
    ],
  };

  const mockAdvisories: GeoJSONFeatureCollection = {
    type: "FeatureCollection",
    features: [],
  };

  function renderNationalMapPage() {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    vi.spyOn(incidentApi, "getGeoIncidents").mockResolvedValue(mockIncidents);
    vi.spyOn(routeApi, "getForecastAdvisories").mockResolvedValue(mockAdvisories);
    vi.spyOn(weatherGridApi, "fetchWeatherTimes").mockResolvedValue(mockTimes);
    vi.spyOn(weatherGridApi, "fetchWeatherGrid").mockResolvedValue(mockWeatherFeatures);
    vi.spyOn(weatherGridApi, "fetchMarineGrid").mockResolvedValue(mockMarineFeatures);

    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("eez_india_boundary.geojson")) {
        return Promise.resolve({
          json: () => Promise.resolve({ type: "FeatureCollection", features: [] }),
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    });

    return render(
      <QueryClientProvider client={queryClient}>
        <NationalMapPage />
      </QueryClientProvider>
    );
  }

  it("renders gridded weather forecast layer toggle buttons without removing incident or advisory toggles", async () => {
    renderNationalMapPage();

    // Check existing toggles
    expect(screen.getAllByText(/Verified Incidents/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/IMD\/NDMA Forecast Advisories/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/India EEZ Maritime Boundary/i).length).toBeGreaterThan(0);

    // Check weather forecast toggle buttons
    expect(screen.getByText(/Gridded Model Forecast Layers:/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /Off/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Temperature/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Rainfall/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Wind Flow/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Wave Height/i })).toBeDefined();

    // Verify existing incident marker is rendered
    await waitFor(() => {
      expect(screen.getByTestId("incident-marker")).toBeDefined();
    });
  });

  it("shows source note on map with Open-Meteo model attribution and fetched_at time", async () => {
    renderNationalMapPage();

    await waitFor(() => {
      const sourceNote = screen.getByText(/Open-Meteo model data \(not station observations\) - updated/i);
      expect(sourceNote).toBeDefined();
    });
  });

  it("switches weather metric to Rainfall, Wind Flow, and Wave Height upon toggle click", async () => {
    renderNationalMapPage();

    // Initially temperature is active by default
    await waitFor(() => {
      expect(screen.getByText("2m Air Temperature (°C)")).toBeDefined();
    });

    // Switch to Rainfall
    fireEvent.click(screen.getByRole("button", { name: /Rainfall/i }));
    await waitFor(() => {
      expect(screen.getByText("1-Hour Precipitation (mm)")).toBeDefined();
    });

    // Switch to Wind Flow
    fireEvent.click(screen.getByRole("button", { name: /Wind Flow/i }));
    await waitFor(() => {
      expect(screen.getByText("10m Wind Speed (km/h) & Flow")).toBeDefined();
      expect(screen.getByText(/Arrow indicates downwind flow direction/i)).toBeDefined();
    });

    // Switch to Wave Height
    fireEvent.click(screen.getByRole("button", { name: /Wave Height/i }));
    await waitFor(() => {
      expect(screen.getByText("Significant Wave Height (m)")).toBeDefined();
      expect(screen.getByText(/Maritime EEZ sea points only/i)).toBeDefined();
    });

    // Switch to Off
    fireEvent.click(screen.getByRole("button", { name: /Off/i }));
    await waitFor(() => {
      expect(screen.queryByText("Significant Wave Height (m)")).toBeNull();
      expect(screen.queryByTestId("weather-time-slider")).toBeNull();
    });
  });

  it("WeatherTimeSlider labels past hours as earlier today and future hours with future offset", () => {
    const now = new Date();
    const pastTime = new Date(now.getTime() - 4 * 3600 * 1000).toISOString();
    const currentTime = new Date(now.getTime()).toISOString();
    const futureTime = new Date(now.getTime() + 12 * 3600 * 1000).toISOString();
    const testValidTimes = [pastTime, currentTime, futureTime];

    const onSelectTime = vi.fn();
    const queryClient = new QueryClient();

    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <WeatherTimeSlider
          validTimes={testValidTimes}
          selectedTime={testValidTimes[0]}
          onSelectTime={onSelectTime}
          activeMetric="temperature"
        />
      </QueryClientProvider>
    );

    // Selected past time should have "earlier today" badge
    expect(screen.getByText("earlier today")).toBeDefined();

    // Rerender with future time
    rerender(
      <QueryClientProvider client={queryClient}>
        <WeatherTimeSlider
          validTimes={testValidTimes}
          selectedTime={testValidTimes[2]}
          onSelectTime={onSelectTime}
          activeMetric="temperature"
        />
      </QueryClientProvider>
    );

    // Future time should display future label
    expect(screen.getByText(/future/i)).toBeDefined();
  });

  it("WeatherTimeSlider prefetches neighbouring valid_time forecasts with React Query", async () => {
    const testValidTimes = [
      "2026-10-02T00:00:00+00:00",
      "2026-10-02T01:00:00+00:00",
      "2026-10-02T02:00:00+00:00",
      "2026-10-02T03:00:00+00:00",
    ];

    const queryClient = new QueryClient();
    const prefetchSpy = vi.spyOn(queryClient, "prefetchQuery");

    render(
      <QueryClientProvider client={queryClient}>
        <WeatherTimeSlider
          validTimes={testValidTimes}
          selectedTime={testValidTimes[1]}
          onSelectTime={vi.fn()}
          activeMetric="temperature"
        />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(prefetchSpy).toHaveBeenCalled();
    });

    const prefetchKeys = prefetchSpy.mock.calls.map((call) => call[0].queryKey);
    const hasPreviousHour = prefetchKeys.some(
      (k) => Array.isArray(k) && k[0] === "weatherGrid" && k[1] === testValidTimes[0]
    );
    const hasNextHour = prefetchKeys.some(
      (k) => Array.isArray(k) && k[0] === "weatherGrid" && k[1] === testValidTimes[2]
    );
    expect(hasPreviousHour).toBe(true);
    expect(hasNextHour).toBe(true);
  });

  it("WeatherColorLegend renders accurate unit legends for all metrics", () => {
    const { rerender } = render(<WeatherColorLegend activeMetric="temperature" />);
    expect(screen.getByText("2m Air Temperature (°C)")).toBeDefined();
    expect(screen.getByText("36°+")).toBeDefined();

    rerender(<WeatherColorLegend activeMetric="precipitation" />);
    expect(screen.getByText("1-Hour Precipitation (mm)")).toBeDefined();
    expect(screen.getByText("25+ mm")).toBeDefined();

    rerender(<WeatherColorLegend activeMetric="wind" />);
    expect(screen.getByText("10m Wind Speed (km/h) & Flow")).toBeDefined();
    expect(screen.getByText("80+ km/h")).toBeDefined();

    rerender(<WeatherColorLegend activeMetric="wave_height" />);
    expect(screen.getByText("Significant Wave Height (m)")).toBeDefined();
    expect(screen.getByText("5m+")).toBeDefined();
  });
});
