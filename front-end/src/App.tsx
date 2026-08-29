import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HomePage } from '@/pages/HomePage';
import { DashboardPage } from '@/pages/DashboardPage';
import { LiveMapPage } from '@/pages/LiveMapPage';
import { CitizenReportPage } from '@/pages/CitizenReportPage';
import { TrackReportPage } from '@/pages/TrackReportPage';
import { IncidentListPage } from '@/pages/IncidentListPage';
import { IncidentDetailPage } from '@/pages/IncidentDetailPage';
import { AdminVerificationQueuePage } from '@/pages/AdminVerificationQueuePage';
import { AnalyticsPage } from '@/pages/AnalyticsPage';
import { LoginPage } from '@/pages/LoginPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/incidents" element={<IncidentListPage />} />
          <Route path="/incidents/:id" element={<IncidentDetailPage />} />
          <Route path="/live-map" element={<LiveMapPage />} />
          <Route path="/report" element={<CitizenReportPage />} />
          <Route path="/track-report" element={<TrackReportPage />} />
          <Route path="/admin/queue" element={<AdminVerificationQueuePage />} />
          <Route path="/verification" element={<AdminVerificationQueuePage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
