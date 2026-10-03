import { apiClient } from "@/services/client";

export interface HourlyForecastItem {
  valid_time: string;
  temperature_2m: number | null;
  precipitation: number | null;
  wind_speed_10m: number | null;
  wind_direction_10m: number | null;
  pressure_msl: number | null;
  wave_height?: number | null;
  wave_direction?: number | null;
  wave_period?: number | null;
}

export interface WeatherPointResponse {
  grid_latitude: number;
  grid_longitude: number;
  requested_latitude: number;
  requested_longitude: number;
  distance_km: number;
  fetched_at: string;
  source_name: string;
  hourly: HourlyForecastItem[];
}

export interface WeatherLiveCheckResponse {
  requested_latitude: number;
  requested_longitude: number;
  grid_latitude: number;
  grid_longitude: number;
  distance_km: number;
  is_sea: boolean;
  live_fetched_at: string;
  hourly: HourlyForecastItem[];
}

export interface WeatherTimesResponse {
  valid_times: string[];
  latest_fetched_at: string | null;
  count: number;
}

export async function fetchWeatherPoint(lat: number, lon: number): Promise<WeatherPointResponse> {
  return apiClient<WeatherPointResponse>(`/weather/point?lat=${lat}&lon=${lon}`);
}

export async function fetchWeatherLiveCheck(lat: number, lon: number): Promise<WeatherLiveCheckResponse> {
  return apiClient<WeatherLiveCheckResponse>(`/weather/live-check?lat=${lat}&lon=${lon}`);
}

export interface WeatherGridFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [lon, lat]
  };
  properties: {
    latitude: number;
    longitude: number;
    valid_time: string;
    temperature_2m?: number | null;
    precipitation?: number | null;
    wind_speed_10m?: number | null;
    wind_direction_10m?: number | null;
    pressure_msl?: number | null;
    wave_height?: number | null;
    wave_direction?: number | null;
    wave_period?: number | null;
  };
}

export interface WeatherGridFeatureCollection {
  type: "FeatureCollection";
  features: WeatherGridFeature[];
}

export async function fetchWeatherTimes(): Promise<WeatherTimesResponse> {
  return apiClient<WeatherTimesResponse>("/weather/times");
}

export async function fetchWeatherGrid(validTime?: string, clip?: boolean): Promise<WeatherGridFeatureCollection> {
  const params = new URLSearchParams();
  if (validTime) params.append("valid_time", validTime);
  if (clip) params.append("clip", "true");
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiClient<WeatherGridFeatureCollection>(`/weather/grid${query}`);
}

export async function fetchMarineGrid(validTime?: string, clip?: boolean): Promise<WeatherGridFeatureCollection> {
  const params = new URLSearchParams();
  if (validTime) params.append("valid_time", validTime);
  if (clip) params.append("clip", "true");
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiClient<WeatherGridFeatureCollection>(`/weather/marine-grid${query}`);
}
