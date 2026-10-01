import React from 'react';
import { Link } from 'react-router-dom';
import { Cloud } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { getHomeRouteForRole } from '@/lib/roleRoutes';

export const BrandLogo: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const target = isAuthenticated ? getHomeRouteForRole(user?.role) : '/';

  return (
    <Link to={target} className="flex items-center space-x-2 shrink-0">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
        <Cloud className="h-4.5 w-4.5" />
      </div>
      <div className="flex flex-col">
        <span className="font-black tracking-tight text-blue-900 text-sm whitespace-nowrap">
          NWBDA <span className="hidden xl:inline font-bold text-slate-500 text-xs">Platform</span>
        </span>
      </div>
    </Link>
  );
};
