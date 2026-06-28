import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI, userAPI } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  /* ── Bootstrap: reload user from stored token ── */
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) { setLoading(false); return; }
    userAPI.me()
      .then(u => setUser(u))
      .catch(() => localStorage.clear())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async ({ email, password }) => {
    const data = await authAPI.login({ email, password });
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(async ({ username, email, password }) => {
    const newUser = await authAPI.register({ username, email, password });
    // auto-login after register
    return login({ email, password }).then(() => newUser);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.clear();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const u = await userAPI.me();
    setUser(u);
    return u;
  }, []);

  const completeOnboarding = useCallback(async (data) => {
    const u = await userAPI.onboarding(data);
    setUser(u);
    return u;
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser, completeOnboarding }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);