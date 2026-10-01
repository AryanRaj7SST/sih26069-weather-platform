import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LogOut } from 'lucide-react';
import { NavItem } from '@/config/navigation';
import { CitySearchBar } from '@/components/common/CitySearchBar';
import { useAuth } from '@/context/AuthContext';
import { useQueryClient } from '@tanstack/react-query';

interface MobileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  primaryItems: NavItem[];
  moreItems?: NavItem[];
  showCitySearch?: boolean;
}

export const MobileDrawer: React.FC<MobileDrawerProps> = ({
  isOpen,
  onClose,
  primaryItems,
  moreItems = [],
  showCitySearch = true,
}) => {
  const location = useLocation();
  const { t } = useTranslation();
  const { isAuthenticated, user, logout } = useAuth();
  const queryClient = useQueryClient();

  if (!isOpen) return null;

  const handleLogout = () => {
    queryClient.clear();
    logout();
    onClose();
  };

  const role = user?.role?.toUpperCase() || 'GUEST';

  return (
    <div className="border-b border-slate-200 bg-white px-4 py-3 lg:hidden space-y-3 shadow-lg">
      {showCitySearch && (
        <div className="w-full">
          <CitySearchBar placeholder="Search Indian city or district..." />
        </div>
      )}

      <nav className="flex flex-col space-y-1">
        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-3 pt-1">
          {t('nav.primaryNav', 'Primary Navigation')}
        </div>
        {primaryItems.map((link) => {
          const isActive = location.pathname === link.path;
          return (
            <Link
              key={link.id}
              to={link.path}
              onClick={onClose}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 font-bold'
                  : 'text-slate-700 hover:bg-slate-50'
              }`}
            >
              {t(link.labelKey, link.defaultLabel)}
            </Link>
          );
        })}

        {moreItems.length > 0 && (
          <>
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-3 pt-2">
              {t('nav.servicesTools', 'Services & Tools')}
            </div>
            {moreItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.id}
                  to={item.path}
                  onClick={onClose}
                  className={`flex items-center space-x-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 font-bold'
                      : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <span>{t(item.labelKey, item.defaultLabel)}</span>
                </Link>
              );
            })}
          </>
        )}

        <div className="border-t border-slate-100 pt-2 flex items-center justify-between">
          {isAuthenticated ? (
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center space-x-1.5 text-sm font-bold text-rose-600 px-3 py-2 cursor-pointer"
            >
              <LogOut className="h-4 w-4" />
              <span>{t('nav.logout', 'Logout')} ({role})</span>
            </button>
          ) : (
            <Link
              to="/login"
              onClick={onClose}
              className="block rounded-lg px-3 py-2 text-sm font-bold text-blue-600 hover:bg-blue-50"
            >
              {t('nav.login', 'Sign In')}
            </Link>
          )}
        </div>
      </nav>
    </div>
  );
};
