import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Activity, CloudRain, ShieldCheck } from 'lucide-react';

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
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-6 text-foreground">
      <div className="w-full max-w-2xl rounded-xl border border-border bg-card p-8 shadow-sm">
        <div className="flex items-center space-x-3 text-primary">
          <CloudRain className="h-8 w-8 text-primary" />
          <span className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">
            Smart India Hackathon 2026 • SIH26069
          </span>
        </div>

        <h1 className="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          National Weather Big Data Analytics Platform
        </h1>

        <p className="mt-4 text-base leading-relaxed text-muted-foreground">
          Application foundation initialized. Multi-source meteorological ingestion, explainable
          credibility scoring, geospatial intelligence, and real-time situational awareness dashboard.
        </p>

        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="flex items-center space-x-3 rounded-lg border border-border bg-secondary/40 p-4">
            <Activity className="h-5 w-5 text-primary" />
            <div>
              <p className="text-xs text-muted-foreground">Backend API</p>
              <p className="text-sm font-medium text-foreground">FastAPI + Async</p>
            </div>
          </div>

          <div className="flex items-center space-x-3 rounded-lg border border-border bg-secondary/40 p-4">
            <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <div>
              <p className="text-xs text-muted-foreground">System Status</p>
              <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                Foundation Ready
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 rounded-lg border border-border bg-secondary/40 p-4">
            <CloudRain className="h-5 w-5 text-sky-600 dark:text-sky-400" />
            <div>
              <p className="text-xs text-muted-foreground">Architecture</p>
              <p className="text-sm font-medium text-foreground">Phase 1 Complete</p>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-border pt-4 text-center text-xs text-muted-foreground">
          Platform System of Record: PostgreSQL 16 + PostGIS • UI Framework: React 18 + Vite + Tailwind CSS
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
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
