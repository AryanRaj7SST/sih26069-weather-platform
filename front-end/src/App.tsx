import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/i18n";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { GuestOnlyRoute } from "@/components/auth/GuestOnlyRoute";
import { LocationProvider } from "@/context/LocationContext";
import { realtimeService } from "@/services/realtimeService";
import { getHomeRouteForRole } from "@/lib/roleRoutes";

import { AuthLayout } from "@/components/layout/AuthLayout";
import { CitizenLayout } from "@/components/layout/CitizenLayout";
import { StaffLayout } from "@/components/layout/StaffLayout";
import { RoleShell } from "@/components/layout/RoleShell";

// O5: Route-level lazy loading — each page becomes a separate async chunk.
const DashboardPage = lazy(() =>
  import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage }))
);
const LiveMapPage = lazy(() =>
  import("@/pages/LiveMapPage").then((m) => ({ default: m.LiveMapPage }))
);
const CitizenReportPage = lazy(() =>
  import("@/pages/CitizenReportPage").then((m) => ({
    default: m.CitizenReportPage,
  }))
);
const TrackReportPage = lazy(() =>
  import("@/pages/TrackReportPage").then((m) => ({
    default: m.TrackReportPage,
  }))
);
const IncidentListPage = lazy(() =>
  import("@/pages/IncidentListPage").then((m) => ({
    default: m.IncidentListPage,
  }))
);
const IncidentDetailPage = lazy(() =>
  import("@/pages/IncidentDetailPage").then((m) => ({
    default: m.IncidentDetailPage,
  }))
);
const CitizenDashboardPage = lazy(() =>
  import("@/pages/CitizenDashboardPage").then((m) => ({
    default: m.CitizenDashboardPage,
  }))
);
const NationalMapPage = lazy(() =>
  import("@/pages/NationalMapPage").then((m) => ({
    default: m.NationalMapPage,
  }))
);
const AdminVerificationQueuePage = lazy(() =>
  import("@/pages/AdminVerificationQueuePage").then((m) => ({
    default: m.AdminVerificationQueuePage,
  }))
);
const AdminAuditLogPage = lazy(() =>
  import("@/pages/AdminAuditLogPage").then((m) => ({
    default: m.AdminAuditLogPage,
  }))
);
const AnalyticsPage = lazy(() =>
  import("@/pages/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage }))
);
const LoginPage = lazy(() =>
  import("@/pages/LoginPage").then((m) => ({ default: m.LoginPage }))
);
const SignupPage = lazy(() =>
  import("@/pages/SignupPage").then((m) => ({ default: m.SignupPage }))
);
const MyReportsPage = lazy(() =>
  import("@/pages/MyReportsPage").then((m) => ({ default: m.MyReportsPage }))
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

function PageFallback() {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
        background: "#0f172a",
        color: "#94a3b8",
        fontSize: "1rem",
      }}
    >
      Loading…
    </div>
  );
}

export function AuthGate() {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return (
      <Suspense fallback={<PageFallback />}>
        <LoginPage />
      </Suspense>
    );
  }

  return <Navigate to={getHomeRouteForRole(user?.role)} replace />;
}

export function App() {
  useEffect(() => {
    realtimeService.initialize(queryClient);
    return () => {
      realtimeService.disconnect();
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <LocationProvider>
            <Routes>
                {/* Guest / Auth Layout Routes */}
                <Route element={<GuestOnlyRoute />}>
                  <Route element={<AuthLayout />}>
                    <Route path="/" element={<AuthGate />} />
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/signup" element={<SignupPage />} />
                  </Route>
                </Route>

                {/* Redirects */}
                <Route path="/welcome" element={<Navigate to="/" replace />} />
                <Route
                  path="/verification"
                  element={<Navigate to="/admin/queue" replace />}
                />

                {/* Citizen Only (CitizenLayout) */}
                <Route element={<ProtectedRoute roles={["CITIZEN"]} />}>
                  <Route element={<CitizenLayout />}>
                    <Route
                      path="/citizen-dashboard"
                      element={<CitizenDashboardPage />}
                    />
                  </Route>
                </Route>

                {/* Staff Only: OPERATOR & ADMIN (StaffLayout) */}
                <Route element={<ProtectedRoute roles={["OPERATOR", "ADMIN"]} />}>
                  <Route element={<StaffLayout />}>
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route
                      path="/admin/queue"
                      element={<AdminVerificationQueuePage />}
                    />
                    <Route
                      path="/admin/audit-logs"
                      element={<AdminAuditLogPage />}
                    />
                  </Route>
                </Route>

                {/* Shared CITIZEN + ADMIN (RoleShell) */}
                <Route element={<ProtectedRoute roles={["CITIZEN", "ADMIN"]} />}>
                  <Route element={<RoleShell />}>
                    <Route path="/report" element={<CitizenReportPage />} />
                    <Route path="/track-report" element={<TrackReportPage />} />
                    <Route path="/my-reports" element={<MyReportsPage />} />
                  </Route>
                </Route>

                {/* Shared All Roles (RoleShell) */}
                <Route
                  element={
                    <ProtectedRoute roles={["CITIZEN", "OPERATOR", "ADMIN"]} />
                  }
                >
                  <Route element={<RoleShell />}>
                    <Route path="/live-map" element={<LiveMapPage />} />
                    <Route path="/national-map" element={<NationalMapPage />} />
                    <Route path="/incidents" element={<IncidentListPage />} />
                    <Route
                      path="/incidents/:id"
                      element={<IncidentDetailPage />}
                    />
                    <Route path="/analytics" element={<AnalyticsPage />} />
                  </Route>
                </Route>

                {/* Catch-all */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
          </LocationProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
