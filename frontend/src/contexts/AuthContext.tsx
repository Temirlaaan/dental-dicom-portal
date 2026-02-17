import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import api from '../services/api';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: () => void;
  logout: () => void;
  handleCallback: (code: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'http://10.121.245.146:8180';
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'dental-portal';
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'dental-frontend';
const REDIRECT_URI = `${window.location.origin}/auth/callback`;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: true,
  });

  const setTokens = useCallback((accessToken: string, refreshToken: string) => {
    sessionStorage.setItem('access_token', accessToken);
    sessionStorage.setItem('refresh_token', refreshToken);
    // Also set in localStorage for the api interceptor
    localStorage.setItem('access_token', accessToken);
  }, []);

  const clearTokens = useCallback(() => {
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    localStorage.removeItem('access_token');
  }, []);

  const fetchUser = useCallback(async (token: string): Promise<User | null> => {
    try {
      const resp = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return {
        id: resp.data.id,
        name: resp.data.name,
        email: resp.data.email,
        role: resp.data.roles?.includes('admin') ? 'admin' : 'doctor',
      };
    } catch {
      return null;
    }
  }, []);

  const refreshAccessToken = useCallback(async (rToken: string): Promise<string | null> => {
    try {
      const resp = await api.post('/auth/refresh', null, {
        params: { refresh_token: rToken },
      });
      const { access_token, refresh_token } = resp.data;
      setTokens(access_token, refresh_token);
      return access_token;
    } catch (error) {
      // Clear invalid tokens on refresh failure
      clearTokens();
      return null;
    }
  }, [setTokens, clearTokens]);

  // On mount: check for existing tokens
  useEffect(() => {
    const init = async () => {
      const token = sessionStorage.getItem('access_token');
      const rToken = sessionStorage.getItem('refresh_token');

      if (token) {
        const user = await fetchUser(token);
        if (user) {
          setState({ user, accessToken: token, refreshToken: rToken, isAuthenticated: true, isLoading: false });
          return;
        }
        // Token expired, try refresh
        if (rToken) {
          const newToken = await refreshAccessToken(rToken);
          if (newToken) {
            const user = await fetchUser(newToken);
            if (user) {
              setState({ user, accessToken: newToken, refreshToken: rToken, isAuthenticated: true, isLoading: false });
              return;
            }
          }
        }
      }
      clearTokens();
      setState({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isLoading: false });
    };
    init();
  }, [fetchUser, refreshAccessToken, clearTokens]);

  // Auto-refresh token before expiry
  useEffect(() => {
    if (!state.accessToken || !state.refreshToken) return;

    // Refresh every 4 minutes (tokens typically last 5 min)
    const interval = setInterval(async () => {
      if (state.refreshToken) {
        const newToken = await refreshAccessToken(state.refreshToken);
        if (newToken) {
          setState(prev => ({ ...prev, accessToken: newToken }));
        }
      }
    }, 4 * 60 * 1000);

    return () => clearInterval(interval);
  }, [state.accessToken, state.refreshToken, refreshAccessToken]);

  const login = () => {
    const params = new URLSearchParams({
      client_id: KEYCLOAK_CLIENT_ID,
      response_type: 'code',
      scope: 'openid profile email',
      redirect_uri: REDIRECT_URI,
    });
    window.location.href = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?${params}`;
  };

  const logout = () => {
    clearTokens();
    setState({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isLoading: false });
    const params = new URLSearchParams({
      client_id: KEYCLOAK_CLIENT_ID,
      post_logout_redirect_uri: window.location.origin,
    });
    window.location.href = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/logout?${params}`;
  };

  const handleCallback = async (code: string) => {
    const resp = await api.get('/auth/callback', {
      params: { code, redirect_uri: REDIRECT_URI },
    });
    const { access_token, refresh_token } = resp.data;
    setTokens(access_token, refresh_token);

    const user = await fetchUser(access_token);
    setState({
      user,
      accessToken: access_token,
      refreshToken: refresh_token,
      isAuthenticated: !!user,
      isLoading: false,
    });
  };

  return (
    <AuthContext.Provider value={{ ...state, login, logout, handleCallback }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
