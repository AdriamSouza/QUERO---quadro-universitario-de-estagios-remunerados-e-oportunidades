import { apiClient } from './client';

export interface Usuario {
  id: number;
  nome: string;
  email: string;
  matricula?: string | null;
  perfil: 'ESTUDANTE' | 'AVALIADOR' | 'PRO_REITOR';
  ativo: boolean;
  criado_em: string;
}

export interface UsuarioCreatePayload {
  nome: string;
  email: string;
  cpf: string;
  matricula?: string;
  perfil: Usuario['perfil'];
  senha: string;
}

export interface Notificacao {
  id: number;
  tipo: string;
  titulo: string;
  mensagem: string;
  lida: boolean;
  criado_em: string;
}

export const fetchUsuarios = async (params: { perfil?: string; busca?: string } = {}): Promise<{ items: Usuario[]; total: number }> => {
  const response = await apiClient.get('/usuarios', { params: { perfil: params.perfil || undefined, busca: params.busca || undefined } });
  return response.data;
};

export const createUsuario = async (payload: UsuarioCreatePayload): Promise<Usuario> => {
  const response = await apiClient.post<Usuario>('/usuarios', payload);
  return response.data;
};

export const updateUsuario = async (id: number, payload: { ativo?: boolean; nova_senha?: string }): Promise<Usuario> => {
  const response = await apiClient.patch<Usuario>(`/usuarios/${id}`, payload);
  return response.data;
};

export const fetchNotificacoes = async (): Promise<{ items: Notificacao[]; total: number; nao_lidas: number }> => {
  const response = await apiClient.get('/notificacoes', { params: { limit: 20 } });
  return response.data;
};

export const markAllNotificationsRead = async (): Promise<void> => {
  await apiClient.put('/notificacoes/lidas');
};

export const changePassword = async (senhaAtual: string, novaSenha: string): Promise<void> => {
  await apiClient.put('/auth/senha', { senha_atual: senhaAtual, nova_senha: novaSenha });
};
