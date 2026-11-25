import { apiClient } from './client';
import { saveBlob } from '../utils/format';
import { Edital } from '../types/edital';

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
  usuario_id?: number | null;
  acao: string;
  entidade: string;
  entidade_id: number;
  dados_antes?: Record<string, unknown> | null;
  dados_depois?: Record<string, unknown> | null;
  ip_origem?: string | null;
  criado_em: string;
}

export const executeFinalHomologation = async (editalId: number, justificativa?: string): Promise<AtaHomologacaoResponse> => {
  const response = await apiClient.post<AtaHomologacaoResponse>(`/editais/${editalId}/homologar-final`, { justificativa });
  return response.data;
};

export const returnForAdjustments = async (editalId: number, justificativa: string): Promise<Edital> => {
  const response = await apiClient.post<Edital>(`/editais/${editalId}/devolver-ajustes`, { justificativa });
  return response.data;
};

export const downloadAtaPdf = async (editalId: number): Promise<void> => {
  const response = await apiClient.get(`/editais/${editalId}/ata-pdf`, { responseType: 'blob' });
  saveBlob(response.data, `ata_homologacao_edital_${editalId}.pdf`, 'application/pdf');
};

export const downloadFolhaCsv = async (editalId: number): Promise<void> => {
  const response = await apiClient.get(`/editais/${editalId}/folha-csv`, { responseType: 'blob' });
  saveBlob(response.data, `lista_aprovados_edital_${editalId}.csv`, 'text/csv;charset=utf-8');
};

export const fetchAuditLogs = async (
  entidade?: string,
  skip: number = 0,
  limit: number = 50
): Promise<{ items: AuditLog[]; total: number }> => {
  const response = await apiClient.get('/auditoria', {
    params: { entidade: entidade || undefined, skip, limit },
  });
  return response.data;
};
