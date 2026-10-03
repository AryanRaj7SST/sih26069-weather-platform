import React, { useState, useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Clock,
  History,
  TrendingUp,
} from "lucide-react";
import { fetchWeatherGrid, fetchMarineGrid } from "@/services/weatherGridApi";

interface WeatherTimeSliderProps {
  validTimes: string[];
  selectedTime: string | null;
  onSelectTime: (time: string) => void;
  activeMetric: string | null;
}

export const WeatherTimeSlider: React.FC<WeatherTimeSliderProps> = ({
  validTimes,
  selectedTime,
  onSelectTime,
  activeMetric,
}) => {
  const queryClient = useQueryClient();
  const [isPlaying, setIsPlaying] = useState(false);
  const playTimerRef = useRef<number | null>(null);

  // Determine current active index
  const currentIndex = validTimes.findIndex((t) => t === selectedTime);
  const activeIndex = currentIndex >= 0 ? currentIndex : 0;
  const activeIndexRef = useRef(activeIndex);
  activeIndexRef.current = activeIndex;

  // Closest hour to current UTC time
  const nowMs = Date.now();
  const closestUtcDate = new Date(nowMs);
  if (closestUtcDate.getUTCMinutes() >= 30) {
    closestUtcDate.setUTCHours(closestUtcDate.getUTCHours() + 1);
  }
  closestUtcDate.setUTCMinutes(0, 0, 0);
  const currentUtcHm = closestUtcDate.getTime();

  // Prefetch neighbouring hours using React Query
  const prefetchNeighbours = useCallback(
    (index: number) => {
      const neighbours = [index - 1, index + 1, index + 2];
      neighbours.forEach((idx) => {
        if (idx >= 0 && idx < validTimes.length) {
          const vt = validTimes[idx];
          queryClient.prefetchQuery({
            queryKey: ["weatherGrid", vt],
            queryFn: () => fetchWeatherGrid(vt),
            staleTime: 1000 * 60 * 2,
          });
          if (activeMetric === "wave_height") {
            queryClient.prefetchQuery({
              queryKey: ["marineGrid", vt],
              queryFn: () => fetchMarineGrid(vt),
              staleTime: 1000 * 60 * 2,
            });
          }
        }
      });
    },
    [validTimes, queryClient, activeMetric]
  );

  // Trigger prefetch whenever activeIndex changes
  useEffect(() => {
    if (validTimes.length > 0) {
      prefetchNeighbours(activeIndex);
    }
  }, [activeIndex, validTimes, prefetchNeighbours]);

  // Handle Play / Pause animation loop
  useEffect(() => {
    if (!isPlaying) {
      if (playTimerRef.current !== null) {
        window.clearInterval(playTimerRef.current);
        playTimerRef.current = null;
      }
      return;
    }

    playTimerRef.current = window.setInterval(() => {
      const nextIdx = (activeIndexRef.current + 1) % validTimes.length;
      onSelectTime(validTimes[nextIdx]);
    }, 1200);

    return () => {
      if (playTimerRef.current !== null) {
        window.clearInterval(playTimerRef.current);
        playTimerRef.current = null;
      }
    };
  }, [isPlaying, validTimes, onSelectTime]);

  if (!validTimes || validTimes.length === 0) return null;

  const currentValidTime = validTimes[activeIndex] || validTimes[0];
  const currentValidDate = new Date(currentValidTime);
  const currentValidMs = currentValidDate.getTime();

  // Past vs. Future label
  const isPastHour = currentValidMs < currentUtcHm;
  const isCurrentHour = Math.abs(currentValidMs - currentUtcHm) < 1800 * 1000;
  const hourDiff = Math.round((currentValidMs - currentUtcHm) / (3600 * 1000));

  // Format labels
  const utcHours = String(currentValidDate.getUTCHours()).padStart(2, "0");
  const utcMinutes = String(currentValidDate.getUTCMinutes()).padStart(2, "0");
  const utcDay = currentValidDate.getUTCDate();
  const utcMonth = currentValidDate.toLocaleString("en-US", {
    month: "short",
    timeZone: "UTC",
  });
  const timeFormatted = `${utcHours}:${utcMinutes} UTC (${utcDay} ${utcMonth})`;

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newIdx = parseInt(e.target.value, 10);
    if (!isNaN(newIdx) && newIdx >= 0 && newIdx < validTimes.length) {
      onSelectTime(validTimes[newIdx]);
    }
  };

  const handleStepPrev = () => {
    const prevIdx = Math.max(0, activeIndex - 1);
    onSelectTime(validTimes[prevIdx]);
  };

  const handleStepNext = () => {
    const nextIdx = Math.min(validTimes.length - 1, activeIndex + 1);
    onSelectTime(validTimes[nextIdx]);
  };

  return (
    <div
      data-testid="weather-time-slider"
      className="bg-slate-900/95 border border-slate-700/80 rounded-2xl p-3.5 shadow-2xl backdrop-blur-md text-white space-y-2.5 max-w-xl w-full"
    >
      {/* Header Info */}
      <div className="flex items-center justify-between gap-2 flex-wrap text-xs">
        <div className="flex items-center space-x-2">
          <Clock className="h-4 w-4 text-blue-400" />
          <span className="font-bold text-slate-100 font-mono text-sm">
            {timeFormatted}
          </span>
          {isCurrentHour ? (
            <span className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-bold border border-blue-500/40 text-[10px]">
              Current Hour
            </span>
          ) : isPastHour ? (
            <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 text-[10px] flex items-center space-x-1">
              <History className="h-3 w-3" />
              <span>earlier today</span>
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40 text-[10px] flex items-center space-x-1">
              <TrendingUp className="h-3 w-3" />
              <span>+{hourDiff}h future</span>
            </span>
          )}
        </div>

        <div className="text-[11px] text-slate-400 font-mono">
          Step {activeIndex + 1} of {validTimes.length}
        </div>
      </div>

      {/* Slider Controls */}
      <div className="flex items-center space-x-3">
        {/* Play/Pause Button */}
        <button
          type="button"
          onClick={() => setIsPlaying(!isPlaying)}
          aria-label={isPlaying ? "Pause timeline" : "Play timeline"}
          className={`p-2 rounded-xl border text-white transition-all cursor-pointer ${
            isPlaying
              ? "bg-amber-600 hover:bg-amber-700 border-amber-400/50 shadow-md shadow-amber-900/30"
              : "bg-blue-600 hover:bg-blue-700 border-blue-400/50 shadow-md shadow-blue-900/30"
          }`}
        >
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </button>

        {/* Step Prev */}
        <button
          type="button"
          onClick={handleStepPrev}
          disabled={activeIndex <= 0}
          aria-label="Previous hour"
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-700 text-slate-300 transition-colors"
        >
          <SkipBack className="h-3.5 w-3.5" />
        </button>

        {/* Discrete Range Slider */}
        <div className="flex-1 relative">
          <input
            type="range"
            min={0}
            max={validTimes.length - 1}
            step={1}
            value={activeIndex}
            onChange={handleSliderChange}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
        </div>

        {/* Step Next */}
        <button
          type="button"
          onClick={handleStepNext}
          disabled={activeIndex >= validTimes.length - 1}
          aria-label="Next hour"
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-700 text-slate-300 transition-colors"
        >
          <SkipForward className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
};
