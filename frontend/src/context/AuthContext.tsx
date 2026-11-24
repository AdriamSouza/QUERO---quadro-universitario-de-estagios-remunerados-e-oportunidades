import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient } from '../api/client';

export type UserRole = 'ESTUDANTE' | 'AVALIADOR' | 'PRO_REITOR';

export interface User {
  id: number;
  nome: string;
  email: string;
  perfil: UserRole;
  perfis: string[];
}

interface AuthContextType {
  user: User | null;
  role: UserRole;
  loading: boolean;
  switchProfile: (newRole: UserRole) => Promise<void>;
  loginWithCustomEmail: (email: string, targetRole: UserRole) => Promise<void>;
  logout: () => void;
}

const MOCK_PROFILES: Record<UserRole, { email: string; label: string }> = {
  ESTUDANTE: { email: 'estudante@faculdade.edu.br', label: 'João Silva (Estudante)' },
  AVALIADOR: { email: 'avaliador@faculdade.edu.br', label: 'Prof. Carlos (Avaliador)' },
  PRO_REITOR: { email: 'proreitor@faculdade.edu.br', label: 'Dra. Maria (Pró-Reitora)' },
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<UserRole>('ESTUDANTE');
  const [loading, setLoading] = useState(true);

  const loginWithEmail = async (email: string, targetRole: UserRole) => {
    try {
      const response = await apiClient.post('/auth/login', { email });
      const { access_token, user_id, nome, perfis } = response.data;
      localStorage.setItem('token', access_token);
      
      const loggedUser: User = {
        id: user_id,
        nome,
        email,
        perfil: targetRole,
        perfis: perfis || [targetRole],
      };
      setUser(loggedUser);
      setRole(targetRole);
      localStorage.setItem('active_role', targetRole);
      localStorage.setItem('user_info', JSON.stringify(loggedUser));
    } catch (err) {
      console.error('Falha ao autenticar usuário:', err);
      throw err;
    }
  };

  const switchProfile = async (newRole: UserRole) => {
    setLoading(true);
    await loginWithEmail(MOCK_PROFILES[newRole].email, newRole);
    setLoading(false);
  };

  const loginWithCustomEmail = async (email: string, targetRole: UserRole) => {
    setLoading(true);
    await loginWithEmail(email, targetRole);
    setLoading(false);
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('active_role');
    setUser(null);
  };

  useEffect(() => {
    const initAuth = async () => {
      const savedRole = (localStorage.getItem('active_role') as UserRole) || 'ESTUDANTE';
      const savedToken = localStorage.getItem('token');

      if (savedToken && localStorage.getItem('user_info')) {
        try {
          const parsed = JSON.parse(localStorage.getItem('user_info')!);
          setUser(parsed);
          setRole(parsed.perfil || savedRole);
          setLoading(false);
          return;
        } catch {
          // fallback se parse falhar
        }
      }

      // Login inicial automático para permitir navegação imediata
      try {
        await loginWithEmail(MOCK_PROFILES[savedRole].email, savedRole);
      } catch {
        // ignora se offline
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, role, loading, switchProfile, loginWithCustomEmail, logout }}>
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
