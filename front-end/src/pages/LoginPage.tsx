import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  ShieldCheck,
  CheckSquare,
  ArrowRight,
  ArrowLeft,
  Building2,
  Radio,
  Lock,
  Mail,
  AlertCircle,
  Loader2,
  UserCheck,
  Key,
  Compass,
  FileText,
} from 'lucide-react';
import { Navbar } from '@/components/layout/Navbar';
import { useAuth } from '@/context/AuthContext';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, isAuthenticated } = useAuth();

  const [activeTab, setActiveTab] = useState<'OPERATOR' | 'CITIZEN'>('OPERATOR');
  const [email, setEmail] = useState('operator@weather-platform.gov.in');
  const [password, setPassword] = useState('EmergencyOps2026!');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const from = (location.state as { from?: { pathname?: string } })?.from?.pathname || '/admin/queue';

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const handleAutofill = () => {
    setEmail('operator@weather-platform.gov.in');
    setPassword('EmergencyOps2026!');
    setErrorMsg(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!email.trim() || !password) {
      setErrorMsg('Please enter both operator email and password.');
      return;
    }

    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Invalid operator credentials. Access denied.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans antialiased">
      <Navbar />

      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 md:p-8">
        <div className="w-full max-w-xl space-y-6">
          {/* Role Selection Tabs */}
          <div className="flex rounded-2xl bg-slate-200/80 p-1.5 border border-slate-300/60 shadow-2xs">
            <button
              type="button"
              onClick={() => setActiveTab('OPERATOR')}
              className={`flex-1 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'OPERATOR'
                  ? 'bg-white text-blue-900 shadow-sm border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <ShieldCheck className={`h-4 w-4 ${activeTab === 'OPERATOR' ? 'text-blue-600' : 'text-slate-400'}`} />
              <span>Control Room Operator (Admin)</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('CITIZEN')}
              className={`flex-1 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'CITIZEN'
                  ? 'bg-white text-emerald-900 shadow-sm border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <UserCheck className={`h-4 w-4 ${activeTab === 'CITIZEN' ? 'text-emerald-600' : 'text-slate-400'}`} />
              <span>Public Citizen Access</span>
            </button>
          </div>

          {/* Main Container Card */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs space-y-6">
            {activeTab === 'OPERATOR' ? (
              <>
                {/* Operator Header */}
                <div className="flex items-start space-x-3.5">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 border border-blue-100 shrink-0">
                    <ShieldCheck className="h-6 w-6" aria-hidden="true" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 border border-blue-200/80 px-2.5 py-0.5 rounded-full">
                        Admin / Operator Portal
                      </span>
                      <span className="flex items-center space-x-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-2 py-0.5 rounded-full">
                        <Radio className="h-2.5 w-2.5 text-emerald-500 animate-pulse" aria-hidden="true" />
                        <span>Control Room Live</span>
                      </span>
                    </div>
                    <h1 className="text-xl sm:text-2xl font-black text-slate-900 mt-1">
                      Emergency Operations Login
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
                      DEOC / SDRF / NDRF Disaster Management Verification Queue
                    </p>
                  </div>
                </div>

                {/* Error Banner */}
                {errorMsg && (
                  <div className="rounded-xl border border-rose-200 bg-rose-50/80 p-3.5 text-xs text-rose-800 flex items-start space-x-2.5">
                    <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                    <span className="font-semibold">{errorMsg}</span>
                  </div>
                )}

                {/* Login Form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                        Operator Email Address
                      </label>
                      <button
                        type="button"
                        onClick={handleAutofill}
                        className="inline-flex items-center space-x-1 text-[11px] font-bold text-blue-600 hover:text-blue-800 transition-colors"
                      >
                        <Key className="h-3 w-3" />
                        <span>1-Click Autofill Credentials</span>
                      </button>
                    </div>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="operator@weather-platform.gov.in"
                        className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 outline-none transition-all font-medium"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
                      <input
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••••••"
                        className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 outline-none transition-all font-medium"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full flex items-center justify-center space-x-2 px-5 py-3.5 rounded-xl bg-blue-600 text-white font-bold text-sm hover:bg-blue-700 shadow-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Authenticating Operator JWT Session...</span>
                      </>
                    ) : (
                      <>
                        <CheckSquare className="h-4 w-4" />
                        <span>Authenticate & Access Control Room</span>
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </form>

                {/* Protected Environment Note */}
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-xs text-slate-600 space-y-2">
                  <div className="flex items-center space-x-2 text-slate-900 font-bold">
                    <Building2 className="h-4 w-4 text-slate-600" aria-hidden="true" />
                    <span>Protected Operator Environment</span>
                  </div>
                  <p className="leading-relaxed text-[11px] text-slate-500">
                    Authorized operators can authenticate using default credentials (
                    <strong className="font-mono text-slate-800">operator@weather-platform.gov.in</strong> /{' '}
                    <strong className="font-mono text-slate-800">EmergencyOps2026!</strong>) to unlock report verification queues.
                  </p>
                </div>
              </>
            ) : (
              <>
                {/* Citizen Header */}
                <div className="flex items-start space-x-3.5">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 border border-emerald-100 shrink-0">
                    <UserCheck className="h-6 w-6" aria-hidden="true" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-2.5 py-0.5 rounded-full">
                        Public Citizen Access
                      </span>
                      <span className="text-[11px] font-medium text-slate-500">No Login Required</span>
                    </div>
                    <h1 className="text-xl sm:text-2xl font-black text-slate-900 mt-1">
                      Citizen Safety & Incident Portal
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
                      Hyper-local weather warnings, route blockage checks, and citizen reporting
                    </p>
                  </div>
                </div>

                {/* Quick Action Cards for Citizens */}
                <div className="space-y-3 pt-2">
                  <button
                    type="button"
                    onClick={() => navigate('/citizen-dashboard')}
                    className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-200 bg-white hover:border-emerald-500 hover:bg-emerald-50/40 transition-all text-left group cursor-pointer"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                        <Compass className="h-5 w-5" />
                      </div>
                      <div>
                        <h4 className="text-xs font-extrabold text-slate-900 group-hover:text-emerald-800">
                          My Area Citizen Dashboard
                        </h4>
                        <p className="text-[11px] text-slate-500">
                          View nearby verified weather hazards & evacuation shelters around your location
                        </p>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-emerald-600 shrink-0" />
                  </button>

                  <button
                    type="button"
                    onClick={() => navigate('/report')}
                    className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:bg-blue-50/40 transition-all text-left group cursor-pointer"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                        <FileText className="h-5 w-5" />
                      </div>
                      <div>
                        <h4 className="text-xs font-extrabold text-slate-900 group-hover:text-blue-800">
                          Report Severe Weather Event
                        </h4>
                        <p className="text-[11px] text-slate-500">
                          Submit citizen eyewitness report with geotagged photo or video evidence
                        </p>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600 shrink-0" />
                  </button>
                </div>
              </>
            )}

            {/* Back link */}
            <div className="pt-2 border-t border-slate-100 flex justify-center">
              <button
                type="button"
                onClick={() => navigate('/')}
                className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
              >
                <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Return to Public Home</span>
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

