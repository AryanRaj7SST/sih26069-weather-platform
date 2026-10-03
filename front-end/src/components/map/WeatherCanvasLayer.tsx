import React, { useEffect, useRef, useState, useCallback } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";

import { WeatherGridFeature as WeatherFeature } from "@/services/weatherGridApi";

export type WeatherMetric = "temperature" | "precipitation" | "wind" | "wave_height";
export type { WeatherFeature };

interface WeatherCanvasLayerProps {
  weatherFeatures: WeatherFeature[];
  marineFeatures?: WeatherFeature[];
  activeMetric: WeatherMetric | null;
  opacity?: number;
  onSelectPoint?: (feature: WeatherFeature) => void;
}

function getTemperatureColor(temp: number | null | undefined): string {
  if (temp == null || isNaN(temp)) return "rgba(148, 163, 184, 0.4)";
  if (temp <= 10) return "#1e40af"; // Deep blue
  if (temp <= 18) return "#0284c7"; // Sky blue
  if (temp <= 25) return "#10b981"; // Emerald
  if (temp <= 30) return "#f59e0b"; // Amber
  if (temp <= 36) return "#f97316"; // Orange
  return "#ef4444"; // Red
}

function getPrecipitationColor(precip: number | null | undefined): string {
  if (precip == null || isNaN(precip) || precip <= 0.05) return "rgba(148, 163, 184, 0.25)";
  if (precip <= 1.0) return "#93c5fd"; // light blue
  if (precip <= 5.0) return "#3b82f6"; // blue
  if (precip <= 10.0) return "#1d4ed8"; // dark blue
  if (precip <= 25.0) return "#7c3aed"; // violet
  return "#db2777"; // magenta
}

function getWindColor(speed: number | null | undefined): string {
  if (speed == null || isNaN(speed)) return "rgba(148, 163, 184, 0.4)";
  if (speed < 10) return "#2dd4bf"; // teal
  if (speed < 25) return "#84cc16"; // lime
  if (speed < 45) return "#eab308"; // yellow
  if (speed < 65) return "#f97316"; // orange
  return "#ef4444"; // red
}

function getWaveColor(wave: number | null | undefined): string {
  if (wave == null || isNaN(wave)) return "rgba(148, 163, 184, 0.2)";
  if (wave < 0.5) return "#67e8f9"; // cyan
  if (wave < 1.5) return "#0284c7"; // ocean blue
  if (wave < 2.5) return "#4338ca"; // indigo
  if (wave < 4.0) return "#7e22ce"; // purple
  return "#be123c"; // deep rose
}

export const WeatherCanvasLayer: React.FC<WeatherCanvasLayerProps> = ({
  weatherFeatures,
  marineFeatures = [],
  activeMetric,
  opacity = 0.85,
  onSelectPoint,
}) => {
  const map = useMap();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{
    x: number;
    y: number;
    feature: WeatherFeature;
  } | null>(null);

  // Combine marine features into a coordinate lookup for sea wave height
  const marineLookup = useRef<Map<string, WeatherFeature>>(new Map());
  useEffect(() => {
    const mapObj = new Map<string, WeatherFeature>();
    marineFeatures.forEach((f) => {
      const key = `${f.properties.latitude.toFixed(2)},${f.properties.longitude.toFixed(2)}`;
      mapObj.set(key, f);
    });
    marineLookup.current = mapObj;
  }, [marineFeatures]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !map || !activeMetric) {
      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      return;
    }

    const size = map.getSize();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size.x * dpr;
    canvas.height = size.y * dpr;
    canvas.style.width = `${size.x}px`;
    canvas.style.height = `${size.y}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, size.x, size.y);
    ctx.globalAlpha = opacity;

    const zoom = map.getZoom();
    const radius = Math.max(7, Math.min(18, 6 + (zoom - 4) * 2.5));

    // Choose features to render: for wave_height, use marineFeatures; otherwise weatherFeatures
    const targetFeatures = activeMetric === "wave_height" ? marineFeatures : weatherFeatures;

    targetFeatures.forEach((feat) => {
      const [lon, lat] = feat.geometry.coordinates;
      const point = map.latLngToContainerPoint(L.latLng(lat, lon));

      // Viewport culling
      if (point.x < -radius * 2 || point.x > size.x + radius * 2 ||
          point.y < -radius * 2 || point.y > size.y + radius * 2) {
        return;
      }

      // Render based on active metric
      if (activeMetric === "temperature") {
        const temp = feat.properties.temperature_2m;
        const color = getTemperatureColor(temp);

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
        ctx.fill();
        ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
        ctx.lineWidth = 1;
        ctx.stroke();

        if (zoom >= 5 && temp != null) {
          ctx.fillStyle = "#ffffff";
          ctx.font = `bold ${Math.max(9, radius - 2)}px monospace`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(`${Math.round(temp)}°`, point.x, point.y);
        }
      } else if (activeMetric === "precipitation") {
        const precip = feat.properties.precipitation;
        const color = getPrecipitationColor(precip);

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
        ctx.fill();
        ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
        ctx.lineWidth = 1;
        ctx.stroke();

        if (zoom >= 5 && precip != null && precip > 0) {
          ctx.fillStyle = "#ffffff";
          ctx.font = `bold ${Math.max(8, radius - 3)}px monospace`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(`${precip.toFixed(1)}`, point.x, point.y);
        }
      } else if (activeMetric === "wind") {
        const speed = feat.properties.wind_speed_10m;
        const dir = feat.properties.wind_direction_10m;
        const color = getWindColor(speed);

        // Circle base
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
        ctx.fill();
        ctx.strokeStyle = "rgba(255, 255, 255, 0.5)";
        ctx.lineWidth = 1;
        ctx.stroke();

        // Direction arrow
        if (dir != null && !isNaN(dir)) {
          // dir = angle where wind comes from. Arrow points in direction of wind flow
          const flowAngleRad = ((dir + 180 - 90) * Math.PI) / 180;
          const arrowLen = radius + 6;

          ctx.save();
          ctx.translate(point.x, point.y);
          ctx.rotate(flowAngleRad);

          // Arrow shaft
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(-radius * 0.4, 0);
          ctx.lineTo(arrowLen, 0);
          ctx.stroke();

          // Arrowhead
          ctx.fillStyle = "#ffffff";
          ctx.beginPath();
          ctx.moveTo(arrowLen, 0);
          ctx.lineTo(arrowLen - 5, -4);
          ctx.lineTo(arrowLen - 5, 4);
          ctx.closePath();
          ctx.fill();

          ctx.restore();
        }

        if (zoom >= 6 && speed != null) {
          ctx.fillStyle = "#ffffff";
          ctx.font = `bold ${Math.max(8, radius - 4)}px monospace`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(`${Math.round(speed)}`, point.x, point.y);
        }
      } else if (activeMetric === "wave_height") {
        const wave = feat.properties.wave_height;
        if (wave == null || isNaN(wave)) return; // sea points only

        const color = getWaveColor(wave);
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
        ctx.fill();
        ctx.strokeStyle = "rgba(255, 255, 255, 0.5)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        if (zoom >= 5) {
          ctx.fillStyle = "#ffffff";
          ctx.font = `bold ${Math.max(9, radius - 3)}px monospace`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(`${wave.toFixed(1)}m`, point.x, point.y);
        }
      }
    });
  }, [map, activeMetric, weatherFeatures, marineFeatures, opacity]);

  // Hook map events to redraw canvas
  useEffect(() => {
    if (!map) return;
    draw();

    const onMapChange = () => draw();
    map.on("move", onMapChange);
    map.on("moveend", onMapChange);
    map.on("zoom", onMapChange);
    map.on("zoomend", onMapChange);
    map.on("resize", onMapChange);

    return () => {
      map.off("move", onMapChange);
      map.off("moveend", onMapChange);
      map.off("zoom", onMapChange);
      map.off("zoomend", onMapChange);
      map.off("resize", onMapChange);
    };
  }, [map, draw]);

  // Handle click / hover interaction on canvas points
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!map || !activeMetric) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const targetFeatures = activeMetric === "wave_height" ? marineFeatures : weatherFeatures;
    let closestFeature: WeatherFeature | null = null;
    let minDistance = 20; // 20px hit tolerance

    targetFeatures.forEach((feat) => {
      const [lon, lat] = feat.geometry.coordinates;
      const pt = map.latLngToContainerPoint(L.latLng(lat, lon));
      const dist = Math.hypot(pt.x - clickX, pt.y - clickY);
      if (dist < minDistance) {
        minDistance = dist;
        closestFeature = feat;
      }
    });

    if (closestFeature) {
      if (onSelectPoint) onSelectPoint(closestFeature);
      setHoveredPoint({ x: clickX, y: clickY, feature: closestFeature });
    } else {
      setHoveredPoint(null);
    }
  };

  if (!activeMetric) return null;

  return (
    <>
      <canvas
        ref={canvasRef}
        data-testid="weather-canvas-layer"
        onClick={handleCanvasClick}
        className="absolute inset-0 z-[420] cursor-pointer"
        style={{ pointerEvents: "auto" }}
      />
      {hoveredPoint && (
        <div
          className="absolute z-[430] bg-slate-900/90 text-white border border-slate-700 p-2.5 rounded-xl shadow-xl text-xs font-mono pointer-events-none transform -translate-x-1/2 -translate-y-full mb-2"
          style={{ left: hoveredPoint.x, top: hoveredPoint.y }}
        >
          <div className="font-bold text-blue-300">
            Grid: ({hoveredPoint.feature.properties.latitude.toFixed(1)}°, {hoveredPoint.feature.properties.longitude.toFixed(1)}°)
          </div>
          {hoveredPoint.feature.properties.temperature_2m != null && (
            <div>Temp: {hoveredPoint.feature.properties.temperature_2m}°C</div>
          )}
          {hoveredPoint.feature.properties.precipitation != null && (
            <div>Precip: {hoveredPoint.feature.properties.precipitation} mm</div>
          )}
          {hoveredPoint.feature.properties.wind_speed_10m != null && (
            <div>
              Wind: {hoveredPoint.feature.properties.wind_speed_10m} km/h (
              {hoveredPoint.feature.properties.wind_direction_10m ?? 0}°)
            </div>
          )}
          {hoveredPoint.feature.properties.wave_height != null && (
            <div>Wave Height: {hoveredPoint.feature.properties.wave_height} m</div>
          )}
        </div>
      )}
    </>
  );
};
