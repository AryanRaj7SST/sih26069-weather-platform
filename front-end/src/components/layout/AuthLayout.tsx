import React from 'react';
import { Outlet } from 'react-router-dom';
import { BrandLogo } from './parts/BrandLogo';
import { LanguageToggle } from './parts/LanguageToggle';

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans antialiased">
      <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/95 backdrop-blur-md shadow-2xs">
        <div className="w-full max-w-[1720px] mx-auto flex h-16 items-center justify-between px-3 sm:px-4 lg:px-6">
          <BrandLogo />
          <div className="flex items-center space-x-2">
            <LanguageToggle />
          </div>
        </div>
      </header>
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 md:p-8">
        <Outlet />
      </main>
    </div>
  );
};
