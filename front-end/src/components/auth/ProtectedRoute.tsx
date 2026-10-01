import React from "react";
import { Navigate, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { getHomeRouteForRole, UserRole } from "@/lib/roleRoutes";

interface ProtectedRouteProps {
  children?: React.ReactElement;
  roles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  roles,
}) => {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (roles && roles.length > 0 && user) {
    const userRole = (user.role || "CITIZEN").toUpperCase() as UserRole;
    if (!roles.includes(userRole)) {
      // Role unauthorized: redirect to appropriate user landing page
      return <Navigate to={getHomeRouteForRole(userRole)} replace />;
    }
  }

  return children ? children : <Outlet />;
};
