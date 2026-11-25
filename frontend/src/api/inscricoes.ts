import { apiClient } from './client';
import { saveBlob } from '../utils/format';

export interface ArquivoInscricao {
  id: number;
  inscricao_id?: number;
  documento_exigido_id?: number;
  nome_original: string;
  tamanho_bytes: number;
  content_type: string;
  versao: number;
  ativo: boolean;
  enviado_em: string;
}

export interface AvaliacaoResumo {
  status: 'RASCUNHO' | 'CONFIRMADA' | 'RETIFICADA';
  parecer?: 'DEFERIDO' | 'INDEFERIDO' | null;
  nota_merito?: number | string | null;
  avaliador_id: number;
}

export type InscricaoStatus = 'PENDENTE_VALIDACAO_VINCULO' | 'HOMOLOGADA' | 'INDEFERIDA' | 'DESISTENTE';

export interface InscriptionDetail {
  id: number;
  protocolo: string;
  edital_id: number;
  estudante_id: number;
  status: InscricaoStatus;
  motivos_indeferimento?: string[] | null;
  vinculo_ativo_congelado?: boolean | null;
  curso_congelado?: string | null;
  cr_congelado?: number | string | null;
  data_submissao_original: string;
  data_ultima_retificacao?: string | null;
  justificativa_reanalise?: string | null;
  arquivos: ArquivoInscricao[];
  nome_estudante?: string | null;
  email_estudante?: string | null;
  matricula_estudante?: string | null;
  titulo_edital?: string | null;
  status_edital?: string | null;
  avaliacao_resumo?: AvaliacaoResumo | null;
  recurso_status?: string | null;
}

export interface DadosAcademicosDeclarados {
  curso_codigo?: string;
  cr_declarado?: string;
}

const buildForm = (arquivos: { [docId: number]: File }, extras: Record<string, string | undefined> = {}) => {
  const formData = new FormData();
  Object.entries(arquivos).forEach(([docId, file]) => formData.append(`doc_${docId}`, file));
  Object.entries(extras).forEach(([k, v]) => {
    if (v !== undefined && v !== '') formData.append(k, v);
  });
  return formData;
};

export const submeterInscricao = async (
  editalId: number,
  arquivos: { [docId: number]: File },
  dados: DadosAcademicosDeclarados
): Promise<InscriptionDetail> => {
  const response = await apiClient.post<InscriptionDetail>(
    `/editais/${editalId}/inscricoes`,
    buildForm(arquivos, { curso_codigo: dados.curso_codigo, cr_declarado: dados.cr_declarado })
  );
  return response.data;
};

export const fetchMyApplications = async (): Promise<InscriptionDetail[]> => {
  const response = await apiClient.get<InscriptionDetail[]>('/inscricoes/me');
  return response.data;
};

export const fetchEditalApplications = async (editalId: number, status?: string): Promise<InscriptionDetail[]> => {
  const response = await apiClient.get<InscriptionDetail[]>(`/editais/${editalId}/inscricoes`, {
    params: { status: status || undefined },
  });
  return response.data;
};

export const retificarInscricao = async (id: number, arquivos: { [docId: number]: File }): Promise<InscriptionDetail> => {
  const response = await apiClient.put<InscriptionDetail>(`/inscricoes/${id}/retificar`, buildForm(arquivos));
  return response.data;
};

export const desistirInscricao = async (id: number, motivo?: string): Promise<InscriptionDetail> => {
  const response = await apiClient.post<InscriptionDetail>(`/inscricoes/${id}/desistir`, { motivo });
  return response.data;
};

export const reanalisarInscricao = async (id: number, deferido: boolean, justificativa: string): Promise<InscriptionDetail> => {
  const response = await apiClient.post<InscriptionDetail>(`/inscricoes/${id}/reanalisar`, { deferido, justificativa });
  return response.data;
};

export const interporRecurso = async (id: number, texto: string) => {
  const response = await apiClient.post(`/inscricoes/${id}/recursos`, { texto });
  return response.data;
};

export const downloadComprovante = async (id: number, protocolo: string): Promise<void> => {
  const response = await apiClient.get(`/inscricoes/${id}/comprovante`, { responseType: 'blob' });
  saveBlob(response.data, `comprovante_${protocolo}.pdf`, 'application/pdf');
};

export const downloadArquivo = async (arquivo: ArquivoInscricao): Promise<void> => {
  const response = await apiClient.get(`/arquivos/${arquivo.id}/download`, { responseType: 'blob' });
  saveBlob(response.data, arquivo.nome_original, arquivo.content_type || 'application/pdf');
};
