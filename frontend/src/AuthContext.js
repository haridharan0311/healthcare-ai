import React, { createContext, useContext, useState, useEffect } from 'react';
import { login as apiLogin, fetchMe } from './api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const res = await fetchMe();
        setUser(res.data);
      } catch (err) {
        console.error("Session expired/invalid");
        localStorage.removeItem('token');
        setUser(null);
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    loadUser();
  }, []);

  const login = async (username, password) => {
    const res = await apiLogin(username, password);
    const { access, refresh } = res.data;
    localStorage.setItem('token', access);
    localStorage.setItem('refreshToken', refresh);
    await loadUser();
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
