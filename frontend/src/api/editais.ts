import { apiClient } from './client';
import { ComissaoMembro, Edital, EditalListResponse } from '../types/edital';

export interface EditalFilters {
  status?: string;
  categoria?: string;
  busca?: string;
  somente_abertos?: boolean;
  skip?: number;
  limit?: number;
}

export const fetchEditais = async (filters: EditalFilters = {}): Promise<EditalListResponse> => {
  const response = await apiClient.get<EditalListResponse>('/editais', { params: { limit: 100, ...filters } });
  return response.data;
};

export const fetchEditalById = async (id: number): Promise<Edital> => {
  const response = await apiClient.get<Edital>(`/editais/${id}`);
  return response.data;
};

export const createEdital = async (data: Record<string, unknown>): Promise<Edital> => {
  const response = await apiClient.post<Edital>('/editais', data);
  return response.data;
};

export const publishEdital = async (id: number): Promise<Edital> => {
  const response = await apiClient.post<Edital>(`/editais/${id}/publicar`);
  return response.data;
};

export const closeRegistrations = async (id: number): Promise<Edital> => {
  const response = await apiClient.post<Edital>(`/editais/${id}/encerrar-inscricoes`);
  return response.data;
};

export const cancelEdital = async (id: number, justificativa: string): Promise<Edital> => {
  const response = await apiClient.post<Edital>(`/editais/${id}/cancelar`, { justificativa });
  return response.data;
};

export const assignCommittee = async (id: number, avaliadoresIds: number[]): Promise<ComissaoMembro[]> => {
  const response = await apiClient.post<ComissaoMembro[]>(`/editais/${id}/comissao`, { avaliadores_ids: avaliadoresIds });
  return response.data;
};

export const removeCommitteeMember = async (id: number, avaliadorId: number): Promise<ComissaoMembro[]> => {
  const response = await apiClient.delete<ComissaoMembro[]>(`/editais/${id}/comissao/${avaliadorId}`);
  return response.data;
};
