import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Activity, CloudRain, ShieldCheck, ArrowRight, Search } from 'lucide-react';
import { CitizenReportPage } from '@/pages/CitizenReportPage';
import { TrackReportPage } from '@/pages/TrackReportPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

function HomePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6 text-slate-900">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex items-center space-x-3 text-blue-600">
          <CloudRain className="h-8 w-8 text-blue-600" />
          <span className="text-xs font-bold tracking-wider uppercase text-slate-500">
            Smart India Hackathon 2026 • SIH26069
          </span>
        </div>

        <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          National Weather Big Data Analytics Platform
        </h1>

        <p className="mt-4 text-base leading-relaxed text-slate-600">
          AI-augmented meteorological ingestion, explainable credibility scoring, geospatial
          intelligence, and real-time situational awareness dashboard.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to="/report"
            className="flex items-center space-x-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white shadow-md hover:bg-blue-700 transition-colors"
          >
            <span>Report Weather Event</span>
            <ArrowRight className="h-4 w-4" />
          </Link>

          <Link
            to="/track-report"
            className="flex items-center space-x-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
          >
            <Search className="h-4 w-4 text-slate-500" />
            <span>Track Existing Report</span>
          </Link>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="flex items-center space-x-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <Activity className="h-5 w-5 text-blue-600" />
            <div>
              <p className="text-xs text-slate-500">Backend API</p>
              <p className="text-sm font-semibold text-slate-900">FastAPI + PostGIS</p>
            </div>
          </div>

          <div className="flex items-center space-x-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <ShieldCheck className="h-5 w-5 text-emerald-600" />
            <div>
              <p className="text-xs text-slate-500">Citizen Ingestion</p>
              <p className="text-sm font-semibold text-emerald-600">
                Active & Verified
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <CloudRain className="h-5 w-5 text-sky-600" />
            <div>
              <p className="text-xs text-slate-500">Public Tracking</p>
              <p className="text-sm font-semibold text-slate-900">Live & Ready</p>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-slate-100 pt-4 text-center text-xs text-slate-400">
          Platform System of Record: PostgreSQL 16 + PostGIS • MinIO S3 Media Storage
        </div>
      </div>
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/report" element={<CitizenReportPage />} />
          <Route path="/track-report" element={<TrackReportPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
