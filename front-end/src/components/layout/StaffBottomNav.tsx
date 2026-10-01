import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LayoutDashboard, CheckSquare, Map, BarChart3, ShieldCheck } from 'lucide-react';
import { STAFF_BOTTOM_NAV } from '@/config/navigation';

const ICON_MAP: Record<string, React.ElementType> = {
  LayoutDashboard,
  CheckSquare,
  Map,
  BarChart3,
  ShieldCheck,
};

export const StaffBottomNav: React.FC = () => {
  const location = useLocation();
  const { t } = useTranslation();

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-200 bg-white/95 backdrop-blur-md md:hidden">
      <nav className="flex h-16 items-center justify-around px-2">
        {STAFF_BOTTOM_NAV.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.iconName ? ICON_MAP[item.iconName] || LayoutDashboard : LayoutDashboard;

          return (
            <Link
              key={item.id}
              to={item.path}
              className={`flex flex-col items-center justify-center space-y-1 px-2 py-1 text-[11px] font-medium transition-colors ${
                isActive
                  ? 'text-blue-600 font-bold'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <Icon
                className={`h-5 w-5 ${isActive ? 'text-blue-600' : 'text-slate-500'}`}
              />
              <span className="truncate max-w-[64px]">
                {t(item.labelKey, item.defaultLabel)}
              </span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
};
