import React from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';

export const LanguageToggle: React.FC = () => {
  const { i18n } = useTranslation();
  const currentLang = i18n.language || 'en';

  const toggleLanguage = () => {
    const nextLang = currentLang === 'en' ? 'hi' : 'en';
    i18n.changeLanguage(nextLang);
    localStorage.setItem('nwbda_lang', nextLang);
  };

  return (
    <button
      type="button"
      onClick={toggleLanguage}
      className="inline-flex items-center space-x-1 px-2 py-1 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 text-xs font-bold hover:bg-slate-100 transition-colors shrink-0 cursor-pointer"
      title="Switch Language (English / हिंदी)"
    >
      <Globe className="h-3.5 w-3.5 text-blue-600" />
      <span>{currentLang === 'en' ? 'HI' : 'EN'}</span>
    </button>
  );
};
