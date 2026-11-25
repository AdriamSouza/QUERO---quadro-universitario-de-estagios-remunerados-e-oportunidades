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
  matricula?: string | null;
  curso: string;
  cr: number | string;
  nota_merito: number | string;
  resultado: 'CONTEMPLADO' | 'SUPLENTE' | 'INDEFERIDO';
}

export interface ResultadoPreliminarResponse {
  edital_id: number;
  titulo: string;
  status_edital?: string;
  publicado_em?: string | null;
  prazo_recurso_ate?: string | null;
  total_homologadas: number;
  total_deferidas: number;
  total_indeferidas: number;
  vagas_totais: number;
  contemplados: ClassificacaoItem[];
  suplentes: ClassificacaoItem[];
  indeferidos: ClassificacaoItem[];
}

export interface Recurso {
  id: number;
  inscricao_id: number;
  texto: string;
  status: 'ABERTO' | 'EM_ANALISE' | 'DEFERIDO' | 'INDEFERIDO';
  julgado_por?: number | null;
  justificativa_decisao?: string | null;
  criado_em: string;
  julgado_em?: string | null;
  protocolo?: string | null;
  nome_estudante?: string | null;
  nota_original?: number | string | null;
  avaliador_original_id?: number | null;
}

export const fetchEvaluationQueue = async (editalId: number): Promise<InscriptionDetail[]> => {
  const response = await apiClient.get<InscriptionDetail[]>(`/editais/${editalId}/avaliacoes`);
  return response.data;
};

export const submitEvaluation = async (inscricaoId: number, payload: AvaliacaoInputPayload) => {
  const response = await apiClient.put(`/inscricoes/${inscricaoId}/avaliacao`, payload);
  return response.data;
};

export const publishPreliminaryResults = async (editalId: number): Promise<ResultadoPreliminarResponse> => {
  const response = await apiClient.post<ResultadoPreliminarResponse>(`/editais/${editalId}/resultado-preliminar`);
  return response.data;
};

export const fetchResults = async (editalId: number): Promise<ResultadoPreliminarResponse> => {
  const response = await apiClient.get<ResultadoPreliminarResponse>(`/editais/${editalId}/resultado-preliminar`);
  return response.data;
};

export const fetchAppeals = async (editalId: number): Promise<Recurso[]> => {
  const response = await apiClient.get<Recurso[]>(`/editais/${editalId}/recursos`);
  return response.data;
};

export const judgeAppeal = async (
  recursoId: number,
  decisao: 'DEFERIDO' | 'INDEFERIDO',
  justificativa: string,
  novaNota?: number
): Promise<Recurso> => {
  const response = await apiClient.post<Recurso>(`/recursos/${recursoId}/julgar`, {
    decisao,
    justificativa_decisao: justificativa,
    nova_nota_merito: novaNota,
  });
  return response.data;
};
