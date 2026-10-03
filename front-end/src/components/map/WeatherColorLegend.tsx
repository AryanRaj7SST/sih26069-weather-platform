import React from "react";
import {
  Thermometer,
  CloudRain,
  Wind,
  Waves,
  Navigation,
} from "lucide-react";
import { WeatherMetric } from "./WeatherCanvasLayer";

interface WeatherColorLegendProps {
  activeMetric: WeatherMetric | null;
}

export const WeatherColorLegend: React.FC<WeatherColorLegendProps> = ({
  activeMetric,
}) => {
  if (!activeMetric) return null;

  return (
    <div
      data-testid="weather-color-legend"
      className="bg-slate-900/95 border border-slate-700/80 rounded-2xl p-3 shadow-xl backdrop-blur-md text-white text-xs font-mono space-y-2"
    >
      {/* Title & Metric */}
      <div className="flex items-center space-x-1.5 font-bold border-b border-slate-800 pb-1.5 text-slate-200">
        {activeMetric === "temperature" && (
          <>
            <Thermometer className="h-4 w-4 text-amber-400" />
            <span>2m Air Temperature (°C)</span>
          </>
        )}
        {activeMetric === "precipitation" && (
          <>
            <CloudRain className="h-4 w-4 text-cyan-400" />
            <span>1-Hour Precipitation (mm)</span>
          </>
        )}
        {activeMetric === "wind" && (
          <>
            <Wind className="h-4 w-4 text-teal-400" />
            <span>10m Wind Speed (km/h) & Flow</span>
          </>
        )}
        {activeMetric === "wave_height" && (
          <>
            <Waves className="h-4 w-4 text-blue-400" />
            <span>Significant Wave Height (m)</span>
          </>
        )}
      </div>

      {/* Swatches / Gradient Scale */}
      {activeMetric === "temperature" && (
        <div className="space-y-1">
          <div className="flex h-3 w-48 rounded-md overflow-hidden border border-slate-700">
            <div className="flex-1 bg-[#1e40af]" title="<= 10°C" />
            <div className="flex-1 bg-[#0284c7]" title="18°C" />
            <div className="flex-1 bg-[#10b981]" title="25°C" />
            <div className="flex-1 bg-[#f59e0b]" title="30°C" />
            <div className="flex-1 bg-[#f97316]" title="36°C" />
            <div className="flex-1 bg-[#ef4444]" title="> 36°C" />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>&le;10°C</span>
            <span>18°</span>
            <span>25°</span>
            <span>30°</span>
            <span>36°+</span>
          </div>
        </div>
      )}

      {activeMetric === "precipitation" && (
        <div className="space-y-1">
          <div className="flex h-3 w-48 rounded-md overflow-hidden border border-slate-700">
            <div className="flex-1 bg-[#94a3b8]/30" title="0 mm" />
            <div className="flex-1 bg-[#93c5fd]" title="0.1-1.0 mm" />
            <div className="flex-1 bg-[#3b82f6]" title="1-5 mm" />
            <div className="flex-1 bg-[#1d4ed8]" title="5-10 mm" />
            <div className="flex-1 bg-[#7c3aed]" title="10-25 mm" />
            <div className="flex-1 bg-[#db2777]" title="> 25 mm" />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>0</span>
            <span>1</span>
            <span>5</span>
            <span>10</span>
            <span>25+ mm</span>
          </div>
        </div>
      )}

      {activeMetric === "wind" && (
        <div className="space-y-1.5">
          <div className="flex h-3 w-48 rounded-md overflow-hidden border border-slate-700">
            <div className="flex-1 bg-[#2dd4bf]" title="< 10 km/h" />
            <div className="flex-1 bg-[#84cc16]" title="10-25 km/h" />
            <div className="flex-1 bg-[#eab308]" title="25-45 km/h" />
            <div className="flex-1 bg-[#f97316]" title="45-65 km/h" />
            <div className="flex-1 bg-[#ef4444]" title="> 65 km/h" />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>&lt;10</span>
            <span>25</span>
            <span>45</span>
            <span>65</span>
            <span>80+ km/h</span>
          </div>
          <div className="flex items-center space-x-1 text-[10px] text-slate-300 pt-0.5">
            <Navigation className="h-3 w-3 text-white transform rotate-45 inline" />
            <span>Arrow indicates downwind flow direction</span>
          </div>
        </div>
      )}

      {activeMetric === "wave_height" && (
        <div className="space-y-1">
          <div className="flex h-3 w-48 rounded-md overflow-hidden border border-slate-700">
            <div className="flex-1 bg-[#67e8f9]" title="< 0.5 m" />
            <div className="flex-1 bg-[#0284c7]" title="0.5-1.5 m" />
            <div className="flex-1 bg-[#4338ca]" title="1.5-2.5 m" />
            <div className="flex-1 bg-[#7e22ce]" title="2.5-4.0 m" />
            <div className="flex-1 bg-[#be123c]" title="> 4.0 m" />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>&lt;0.5m</span>
            <span>1.5m</span>
            <span>2.5m</span>
            <span>4.0m</span>
            <span>5m+</span>
          </div>
          <div className="text-[10px] text-cyan-300/80">
            Maritime EEZ sea points only
          </div>
        </div>
      )}
    </div>
  );
};
