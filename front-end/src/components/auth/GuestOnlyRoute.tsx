import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { getHomeRouteForRole } from '@/lib/roleRoutes';

export const GuestOnlyRoute: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (isAuthenticated) {
    const from = (location.state as { from?: { pathname?: string } })?.from?.pathname;
    const target = from || getHomeRouteForRole(user?.role);
    return <Navigate to={target} replace />;
  }

  return <Outlet />;
};
