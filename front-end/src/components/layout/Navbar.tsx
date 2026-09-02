import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Cloud, Bell, Menu, X, User, LogOut, Globe, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CitySearchBar } from '@/components/common/CitySearchBar';
import { useAuth } from '@/context/AuthContext';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const { i18n, t } = useTranslation();
  const { isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const currentLang = i18n.language || 'en';

  const toggleLanguage = () => {
    const nextLang = currentLang === 'en' ? 'hi' : 'en';
    i18n.changeLanguage(nextLang);
    localStorage.setItem('nwbda_lang', nextLang);
  };

  const navLinks = [
    { name: t('nav.home', 'Home'), path: '/' },
    { name: t('nav.citizenArea', 'Citizen Area'), path: '/citizen-dashboard' },
    { name: t('nav.nationalMap', 'National Map'), path: '/national-map' },
    { name: t('nav.incidents', 'Incidents'), path: '/incidents' },
    { name: t('nav.dashboard', 'Dashboard'), path: '/dashboard' },
    { name: t('nav.liveMap', 'Live Map'), path: '/live-map' },
    { name: t('nav.reportWeather', 'Report Event'), path: '/report' },
    { name: t('nav.trackReport', 'Track'), path: '/track-report' },
    { name: t('nav.analytics', 'Analytics'), path: '/analytics' },
  ];

  if (isAuthenticated) {
    navLinks.push({ name: t('nav.verificationQueue', 'Triage Queue'), path: '/admin/queue' });
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/95 backdrop-blur-sm shadow-2xs">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-3 sm:px-4 lg:px-6 gap-2">
        {/* Left: Mobile Hamburger & Brand Logo */}
        <div className="flex items-center space-x-2.5 shrink-0">
          <button
            type="button"
            className="rounded-md p-1.5 text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600 xl:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <Link to="/" className="flex items-center space-x-2 shrink-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
              <Cloud className="h-4.5 w-4.5" />
            </div>
            <div className="flex flex-col">
              <span className="hidden font-black tracking-tight text-blue-900 2xl:inline-block text-sm">
                National Weather Analytics
              </span>
              <span className="font-extrabold tracking-tight text-blue-900 2xl:hidden text-sm">
                NWBDA
              </span>
            </div>
          </Link>
        </div>

        {/* Center: Desktop Navigation Links */}
        <nav className="hidden xl:flex xl:h-full xl:items-center xl:space-x-1 2xl:space-x-2">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`relative flex h-full items-center px-1.5 2xl:px-2 text-xs font-semibold whitespace-nowrap transition-colors ${
                  isActive
                    ? 'text-blue-600 after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:bg-blue-600'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {link.name}
              </Link>
            );
          })}
        </nav>

        {/* Right: Language Switcher, Search & Auth Status */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
          {/* Language Switcher Toggle */}
          <button
            type="button"
            onClick={toggleLanguage}
            className="inline-flex items-center space-x-1 px-2 py-1 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 text-xs font-bold hover:bg-slate-100 transition-colors shrink-0"
            title="Switch Language (English / हिंदी)"
          >
            <Globe className="h-3.5 w-3.5 text-blue-600" />
            <span>{currentLang === 'en' ? 'HI' : 'EN'}</span>
          </button>

          {/* Desktop City Search Bar */}
          <div className="hidden sm:block w-36 md:w-40 lg:w-48 xl:w-52">
            <CitySearchBar isCompact />
          </div>

          {isAuthenticated ? (
            <div className="flex items-center space-x-1.5 shrink-0">
              <span className="hidden sm:inline-flex items-center space-x-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-2 py-0.5 rounded-full">
                <ShieldCheck className="h-3 w-3 text-emerald-600" />
                <span>OPERATOR</span>
              </span>
              <button
                type="button"
                onClick={logout}
                className="inline-flex items-center space-x-1 px-2 py-1 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold hover:bg-rose-100 transition-colors shrink-0 cursor-pointer"
                title="Logout Operator Session"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden md:inline">Logout</span>
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="hidden text-xs font-bold text-slate-700 hover:text-blue-600 sm:block shrink-0 px-1"
            >
              {t('nav.login', 'Operator Access')}
            </Link>
          )}

          <button
            type="button"
            className="rounded-full p-1.5 text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 shrink-0"
            aria-label="View notifications"
          >
            <Bell className="h-4 w-4" />
          </button>

          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 border border-slate-200 text-slate-600 shadow-2xs overflow-hidden shrink-0">
            <User className="h-3.5 w-3.5 text-slate-500" />
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu & Search */}
      {mobileMenuOpen && (
        <div className="border-b border-slate-200 bg-white px-4 py-3 md:hidden space-y-3">
          {/* Mobile City Search Bar */}
          <div className="w-full">
            <CitySearchBar placeholder="Search Indian city or district..." />
          </div>

          <nav className="flex flex-col space-y-1">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 font-semibold'
                      : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {link.name}
                </Link>
              );
            })}
            <div className="border-t border-slate-100 pt-2 flex items-center justify-between">
              {isAuthenticated ? (
                <button
                  type="button"
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="flex items-center space-x-1.5 text-sm font-bold text-rose-600 px-3 py-2"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Logout Operator Session</span>
                </button>
              ) : (
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Operator Access
                </Link>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
};
