import { apiClient } from './client';

export interface AtaHomologacaoResponse {
  id: number;
  edital_id: number;
  homologado_por: number;
  arquivo_pdf_id: number;
  arquivo_csv_id: number;
  eh_retificacao: boolean;
  justificativa_retificacao?: string;
  homologado_em: string;
}

export interface AuditLog {
  id: number;
  usuario_id?: number;
  acao: string;
  entidade: string;
  entidade_id: number;
  dados_antes?: any;
  dados_depois?: any;
  ip_origem?: string;
  criado_em: string;
}

export const executeFinalHomologation = async (editalId: number, justificativa?: string): Promise<AtaHomologacaoResponse> => {
  const response = await apiClient.post<AtaHomologacaoResponse>(`/editais/${editalId}/homologar-final`, {
    justificativa,
  });
  return response.data;
};

export const returnForAdjustments = async (editalId: number, justificativa: string): Promise<any> => {
  const response = await apiClient.post(`/editais/${editalId}/devolver-ajustes`, {
    justificativa,
  });
  return response.data;
};

export const fetchAuditLogs = async (
  entidade?: string,
  entidadeId?: number,
  skip: number = 0,
  limit: number = 50
): Promise<{ items: AuditLog[]; total: number }> => {
  const response = await apiClient.get('/auditoria', {
    params: {
      entidade: entidade || undefined,
      entidade_id: entidadeId || undefined,
      skip,
      limit,
    },
  });
  return response.data;
};
