import React from 'react';
import { Link } from 'react-router-dom';
import { PlusCircle, Compass } from 'lucide-react';

interface HeroSectionProps {
  onExploreMapClick?: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onExploreMapClick }) => {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-blue-50/70 via-indigo-50/30 to-white py-12 md:py-16 border-b border-slate-200">
      {/* Subtle background decoration */}
      <div className="absolute inset-0 bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:24px_24px] opacity-25 pointer-events-none" />

      <div className="relative mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
          Crowdsourcing Meteorological Intelligence
        </h1>

        <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Contribute to the nation&apos;s most comprehensive weather database. Report local conditions,
          track developing systems, and access verified analytical models in real-time.
        </p>

        {/* Action Buttons matching Stitch */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3.5">
          <Link
            to="/report"
            className="flex w-full sm:w-auto items-center justify-center space-x-2 rounded-xl bg-blue-600 px-6 py-3.5 text-sm font-bold text-white shadow-md transition-all hover:bg-blue-700 hover:shadow-blue-600/30 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
          >
            <PlusCircle className="h-4 w-4" />
            <span>Report a Weather Event</span>
          </Link>

          <button
            type="button"
            onClick={onExploreMapClick}
            className="flex w-full sm:w-auto items-center justify-center space-x-2 rounded-xl border border-blue-600 bg-white px-6 py-3.5 text-sm font-bold text-blue-700 shadow-sm transition-all hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
          >
            <Compass className="h-4 w-4 text-blue-600" />
            <span>Explore Live Map</span>
          </button>
        </div>
      </div>
    </section>
  );
};
