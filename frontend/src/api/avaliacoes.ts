import { apiClient } from './client';
import { InscriptionDetail } from './inscricoes';

export interface AvaliacaoInputPayload {
  declaracao_sem_impedimento: boolean;
  nota_merito: number;
  parecer: 'DEFERIDO' | 'INDEFERIDO';
  justificativa?: string;
  confirmar?: boolean;
  justificativa_retificacao?: string;
}

export interface ClassificacaoItem {
  posicao: number;
  inscricao_id: number;
  protocolo: string;
  nome_estudante: string;
  matricula?: string;
  curso: string;
  cr: number;
  nota_merito: number;
  resultado: 'CONTEMPLADO' | 'SUPLENTE' | 'INDEFERIDO';
}

export interface ResultadoPreliminarResponse {
  edital_id: number;
  titulo: string;
  total_homologadas: number;
  total_deferidas: number;
  total_indeferidas: number;
  vagas_totais: number;
  contemplados: ClassificacaoItem[];
  suplentes: ClassificacaoItem[];
  indeferidos: ClassificacaoItem[];
}

export const fetchEvaluationQueue = async (editalId: number): Promise<InscriptionDetail[]> => {
  const response = await apiClient.get<InscriptionDetail[]>(`/editais/${editalId}/avaliacoes`);
  return response.data;
};

export const submitEvaluation = async (inscricaoId: number, payload: AvaliacaoInputPayload): Promise<any> => {
  const response = await apiClient.put(`/inscricoes/${inscricaoId}/avaliacao`, payload);
  return response.data;
};

export const publishPreliminaryResults = async (editalId: number): Promise<ResultadoPreliminarResponse> => {
  const response = await apiClient.post<ResultadoPreliminarResponse>(`/editais/${editalId}/resultado-preliminar`);
  return response.data;
};

export const judgeResource = async (
  recursoId: number,
  decisao: 'DEFERIDO' | 'INDEFERIDO',
  justificativa: string,
  novaNota?: number
): Promise<any> => {
  const response = await apiClient.post(`/recursos/${recursoId}/julgar`, {
    decisao,
    justificativa_decisao: justificativa,
    nova_nota_merito: novaNota,
  });
  return response.data;
};
