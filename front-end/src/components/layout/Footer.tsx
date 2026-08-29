import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto border-t border-slate-200 bg-white py-6 text-sm text-slate-600">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6 lg:px-8">
        <p className="text-center font-medium text-slate-700 sm:text-left">
          © {new Date().getFullYear()} National Weather Big Data Analytics Platform
        </p>

        <div className="flex flex-wrap items-center justify-center gap-6 text-sm font-medium text-slate-600">
          <a
            href="#data-sources"
            className="hover:text-blue-600 transition-colors"
          >
            Data Sources
          </a>
          <a
            href="#privacy-policy"
            className="hover:text-blue-600 transition-colors"
          >
            Privacy Policy
          </a>
          <a
            href="#methodology"
            className="hover:text-blue-600 transition-colors"
          >
            Methodology
          </a>
        </div>
      </div>
    </footer>
  );
};
