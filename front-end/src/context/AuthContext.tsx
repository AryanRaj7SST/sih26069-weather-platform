import React, { createContext, useContext, useState, useCallback } from 'react';
import { authApi, OperatorProfile } from '@/services/authApi';

const TOKEN_KEY = 'nwbda_auth_token';
const OPERATOR_KEY = 'nwbda_operator_profile';

interface AuthContextType {
  token: string | null;
  operator: OperatorProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    return typeof sessionStorage !== 'undefined' ? sessionStorage.getItem(TOKEN_KEY) : null;
  });

  const [operator, setOperator] = useState<OperatorProfile | null>(() => {
    if (typeof sessionStorage !== 'undefined') {
      const stored = sessionStorage.getItem(OPERATOR_KEY);
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch {
          return null;
        }
      }
    }
    return null;
  });

  const [isLoading, setIsLoading] = useState(false);

  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await authApi.login(username, password);
      const data = res.data;
      setToken(data.access_token);
      setOperator(data.operator);

      sessionStorage.setItem(TOKEN_KEY, data.access_token);
      sessionStorage.setItem(OPERATOR_KEY, JSON.stringify(data.operator));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setOperator(null);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(OPERATOR_KEY);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        operator,
        isAuthenticated: Boolean(token),
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
