import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { apiClient, SESSION_EXPIRED_EVENT, TOKEN_KEY } from '../api/client';

export type UserRole = 'ESTUDANTE' | 'AVALIADOR' | 'PRO_REITOR';

export interface User {
  id: number;
  nome: string;
  email: string;
  matricula?: string | null;
  perfis: UserRole[];
}

export interface CadastroPayload {
  nome: string;
  email: string;
  cpf: string;
  matricula: string;
  senha: string;
}

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  loading: boolean;
  sessionExpired: boolean;
  login: (email: string, senha: string) => Promise<User>;
  cadastrar: (payload: CadastroPayload) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const fetchMe = async (): Promise<User> => {
  const { data } = await apiClient.get<User>('/auth/me');
  return data;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  const startSession = useCallback(async (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    const me = await fetchMe();
    setUser(me);
    setSessionExpired(false);
    return me;
  }, []);

  const login = useCallback(
    async (email: string, senha: string) => {
      const { data } = await apiClient.post('/auth/login', { email, senha });
      return startSession(data.access_token);
    },
    [startSession]
  );

  const cadastrar = useCallback(
    async (payload: CadastroPayload) => {
      const { data } = await apiClient.post('/auth/cadastro', payload);
      return startSession(data.access_token);
    },
    [startSession]
  );

  const logout = useCallback(() => {
    apiClient.post('/auth/logout').catch(() => undefined);
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);

  useEffect(() => {
    // Limpa dados de sessões antigas (versão anterior do portal)
    ['token', 'user_info', 'active_role'].forEach((k) => localStorage.removeItem(k));

    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then(setUser)
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      setSessionExpired(true);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  const role = user?.perfis?.[0] ?? null;

  return (
    <AuthContext.Provider value={{ user, role, loading, sessionExpired, login, cadastrar, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser utilizado dentro de um AuthProvider');
  }
  return context;
};
