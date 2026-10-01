import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { NavItem } from '@/config/navigation';

interface NavLinkItemProps {
  item: NavItem;
  onClick?: () => void;
}

export const NavLinkItem: React.FC<NavLinkItemProps> = ({ item, onClick }) => {
  const location = useLocation();
  const { t } = useTranslation();
  const isActive = location.pathname === item.path;

  return (
    <Link
      to={item.path}
      onClick={onClick}
      className={`relative flex h-full items-center px-1.5 2xl:px-2.5 py-1 text-xs 2xl:text-sm font-semibold whitespace-nowrap transition-colors ${
        isActive
          ? 'text-blue-600 after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:bg-blue-600'
          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50/80 rounded-md'
      }`}
    >
      {t(item.labelKey, item.defaultLabel)}
    </Link>
  );
};
