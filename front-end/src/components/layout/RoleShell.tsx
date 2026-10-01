import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { isStaff } from '@/lib/roleRoutes';
import { StaffLayout } from './StaffLayout';
import { CitizenLayout } from './CitizenLayout';

export const RoleShell: React.FC = () => {
  const { user } = useAuth();
  if (isStaff(user?.role)) {
    return <StaffLayout />;
  }
  return <CitizenLayout />;
};
