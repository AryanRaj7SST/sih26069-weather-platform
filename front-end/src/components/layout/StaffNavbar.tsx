import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Menu, X, ChevronDown } from 'lucide-react';
import {
  STAFF_ADMIN_PRIMARY_NAV,
  STAFF_OPERATOR_PRIMARY_NAV,
  STAFF_ADMIN_MORE_NAV,
} from '@/config/navigation';
import { BrandLogo } from './parts/BrandLogo';
import { LanguageToggle } from './parts/LanguageToggle';
import { UserMenu } from './parts/UserMenu';
import { NavLinkItem } from './parts/NavLinkItem';
import { MobileDrawer } from './parts/MobileDrawer';
import { CitySearchBar } from '@/components/common/CitySearchBar';
import { useAuth } from '@/context/AuthContext';

export const StaffNavbar: React.FC = () => {
  const location = useLocation();
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [toolsDropdownOpen, setToolsDropdownOpen] = useState(false);
  const toolsRef = useRef<HTMLDivElement>(null);

  const primaryItems = isAdmin
    ? STAFF_ADMIN_PRIMARY_NAV
    : STAFF_OPERATOR_PRIMARY_NAV;
  const moreItems = isAdmin ? STAFF_ADMIN_MORE_NAV : [];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (toolsRef.current && !toolsRef.current.contains(e.target as Node)) {
        setToolsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isMoreActive = moreItems.some((item) => location.pathname === item.path);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/95 backdrop-blur-md shadow-2xs">
      <div className="w-full max-w-[1720px] mx-auto flex h-16 items-center justify-between px-3 sm:px-4 lg:px-6 gap-2">
        {/* Left: Mobile Hamburger & Brand Logo */}
        <div className="flex items-center space-x-2.5 shrink-0">
          <button
            type="button"
            className="rounded-lg p-1.5 text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600 lg:hidden cursor-pointer"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <BrandLogo />
        </div>

        {/* Center: Primary Links + Optional More Dropdown */}
        <nav className="hidden lg:flex lg:h-full lg:items-center lg:space-x-0.5 xl:space-x-1">
          {primaryItems.map((item) => (
            <NavLinkItem key={item.id} item={item} />
          ))}

          {moreItems.length > 0 && (
            <div ref={toolsRef} className="relative h-full flex items-center">
              <button
                type="button"
                onClick={() => setToolsDropdownOpen(!toolsDropdownOpen)}
                className={`relative flex h-full items-center space-x-1 px-1.5 2xl:px-2.5 py-1 text-xs 2xl:text-sm font-semibold whitespace-nowrap transition-colors cursor-pointer ${
                  isMoreActive
                    ? 'text-blue-600 after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:bg-blue-600'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50/80 rounded-md'
                }`}
              >
                <span>{t('nav.tools', 'More')}</span>
                <ChevronDown
                  className={`h-3 w-3 transition-transform ${
                    toolsDropdownOpen ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {toolsDropdownOpen && (
                <div className="absolute left-0 top-[calc(100%-4px)] z-50 w-56 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl space-y-1">
                  {moreItems.map((item) => {
                    const isActive = location.pathname === item.path;
                    return (
                      <Link
                        key={item.id}
                        to={item.path}
                        onClick={() => setToolsDropdownOpen(false)}
                        className={`block rounded-xl px-3 py-2 text-xs font-bold transition-colors ${
                          isActive
                            ? 'bg-blue-50 text-blue-700'
                            : 'text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        {t(item.labelKey, item.defaultLabel)}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </nav>

        {/* Right: Language, City Search & User Menu */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
          <LanguageToggle />

          <div className="hidden sm:block w-32 md:w-36 lg:w-40 xl:w-44">
            <CitySearchBar isCompact />
          </div>

          <UserMenu />
        </div>
      </div>

      <MobileDrawer
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        primaryItems={primaryItems}
        moreItems={moreItems}
      />
    </header>
  );
};
