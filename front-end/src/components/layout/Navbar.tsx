import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Cloud, Bell, Menu, X, User } from 'lucide-react';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { name: 'Home', path: '/' },
    { name: 'Live Map', path: '/map' },
    { name: 'Report Weather Event', path: '/report' },
    { name: 'Track Report', path: '/track' },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Left: Mobile Hamburger & Brand Logo */}
        <div className="flex items-center space-x-3">
          <button
            type="button"
            className="rounded-md p-1.5 text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600 md:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>

          <Link to="/" className="flex items-center space-x-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
              <Cloud className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <span className="hidden font-bold tracking-tight text-blue-900 md:inline-block text-lg">
                National Weather Big Data Analytics Platform
              </span>
              <span className="font-bold tracking-tight text-blue-900 md:hidden text-lg">
                NWBDA
              </span>
            </div>
          </Link>
        </div>

        {/* Center: Desktop Navigation Links */}
        <nav className="hidden md:flex md:h-full md:items-center md:space-x-1 lg:space-x-6">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`relative flex h-full items-center px-3 text-sm font-medium transition-colors ${
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

        {/* Right: Auth, Notifications & Profile */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          <Link
            to="/login"
            className="hidden text-sm font-medium text-slate-700 hover:text-blue-600 md:block"
          >
            Login
          </Link>

          <button
            type="button"
            className="rounded-full p-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600"
            aria-label="View notifications"
          >
            <Bell className="h-5 w-5" />
          </button>

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 border border-slate-200 text-slate-600 shadow-sm overflow-hidden">
            <User className="h-5 w-5 text-slate-500" />
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="border-b border-slate-200 bg-white px-4 py-3 md:hidden">
          <nav className="flex flex-col space-y-2">
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
            <div className="border-t border-slate-100 pt-2">
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="block rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Login to Portal
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
};
