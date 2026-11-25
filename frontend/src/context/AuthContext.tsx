import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/api';
import type { UserRole } from '../types';

interface AuthUser {
  id: number;
  email?: string;
  name: string;
  role: UserRole;
  trainer_id?: number;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isTrainer: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUserContext: (data: Partial<AuthUser>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('gym_auth_token');
    const storedUser = localStorage.getItem('gym_user');

    if (storedToken && storedUser) {
      try {
        const parsed = JSON.parse(storedUser) as AuthUser;
        if (parsed.role !== 'TRAINER') throw new Error('Client sessions are no longer supported');
        setToken(storedToken);
        setUser(parsed);
      } catch {
        localStorage.removeItem('gym_auth_token');
        localStorage.removeItem('gym_user');
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const data = await authService.login(email, password);
    const authUser: AuthUser = {
      id: data.user_id,
      name: data.name,
      role: data.role,
      trainer_id: data.trainer_id,
    };
    setToken(data.access_token);
    setUser(authUser);
    localStorage.setItem('gym_auth_token', data.access_token);
    localStorage.setItem('gym_user', JSON.stringify(authUser));
  };

  const logout = async () => {
    await authService.logout();
    setToken(null);
    setUser(null);
  };

  const updateUserContext = (data: Partial<AuthUser>) => {
    if (user) {
      const updated = { ...user, ...data };
      setUser(updated);
      localStorage.setItem('gym_user', JSON.stringify(updated));
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        isTrainer: user?.role === 'TRAINER',
        login,
        logout,
        updateUserContext,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
