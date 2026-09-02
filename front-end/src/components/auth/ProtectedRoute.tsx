import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

export type UserRole = 'CITIZEN' | 'OPERATOR' | 'ADMIN';

interface ProtectedRouteProps {
  children: React.ReactElement;
  roles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, roles }) => {
  const { isAuthenticated, user, isOperator } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (roles && roles.length > 0 && user) {
    const userRole = (user.role || 'CITIZEN').toUpperCase() as UserRole;
    if (!roles.includes(userRole) && userRole !== 'ADMIN') {
      // Role unauthorized: redirect to appropriate user landing page
      const destination = isOperator ? '/admin/queue' : '/citizen-dashboard';
      return <Navigate to={destination} replace />;
    }
  }

  return children;
};
