import React from 'react';
import { LogOut, User } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useQueryClient } from '@tanstack/react-query';

export const UserMenu: React.FC = () => {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();

  const handleLogout = () => {
    queryClient.clear();
    logout();
  };

  const role = user?.role?.toUpperCase() || 'CITIZEN';

  return (
    <div className="flex items-center space-x-1.5 shrink-0">
      <span
        className={`hidden md:inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider border ${
          role === 'ADMIN'
            ? 'bg-purple-50 text-purple-700 border-purple-200'
            : role === 'OPERATOR'
            ? 'bg-blue-50 text-blue-700 border-blue-200'
            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
        }`}
      >
        {role === 'ADMIN'
          ? '🛡️ ADMIN'
          : role === 'OPERATOR'
          ? '🛡️ OPERATOR'
          : '👤 CITIZEN'}
      </span>
      <button
        type="button"
        onClick={handleLogout}
        className="inline-flex items-center space-x-1 px-2 py-1 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold hover:bg-rose-100 transition-colors shrink-0 cursor-pointer"
        title="Logout Session"
      >
        <LogOut className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Logout</span>
      </button>
      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 border border-slate-200 text-slate-600 shadow-2xs overflow-hidden shrink-0">
        <User className="h-3.5 w-3.5 text-slate-500" />
      </div>
    </div>
  );
};
