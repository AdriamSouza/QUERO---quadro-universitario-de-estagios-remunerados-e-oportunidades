import { apiClient } from './client';

export interface ArquivoInscricao {
  id: number;
  inscricao_id?: number;
  documento_exigido_id?: number;
  chave: string;
  nome_original: string;
  tamanho_bytes: number;
  content_type: string;
  versao: number;
  ativo: boolean;
  status_varredura: string;
  enviado_em: string;
}

export interface InscriptionDetail {
  id: number;
  protocolo: string;
  edital_id: number;
  estudante_id: number;
  status: 'PENDENTE_VALIDACAO_VINCULO' | 'HOMOLOGADA' | 'INDEFERIDA' | 'DESISTENTE';
  motivos_indeferimento?: string[];
  vinculo_ativo_congelado?: boolean;
  curso_congelado?: string;
  cr_congelado?: number;
  data_submissao_original: string;
  data_ultima_retificacao?: string;
  reanalisada_por?: number;
  justificativa_reanalise?: string;
  arquivos: ArquivoInscricao[];
  nome_estudante?: string;
  email_estudante?: string;
  titulo_edital?: string;
}

export const submeterInscricao = async (
  editalId: number,
  arquivosDict: { [docId: number]: File }
): Promise<InscriptionDetail> => {
  const formData = new FormData();
  Object.entries(arquivosDict).forEach(([docId, file]) => {
    formData.append(`doc_${docId}`, file);
  });

  const response = await apiClient.post<InscriptionDetail>(
    `/editais/${editalId}/inscricoes`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return response.data;
};

export const fetchMyApplications = async (): Promise<InscriptionDetail[]> => {
  const response = await apiClient.get<InscriptionDetail[]>('/inscricoes/me');
  return response.data;
};

export const fetchApplicationById = async (id: number): Promise<InscriptionDetail> => {
  const response = await apiClient.get<InscriptionDetail>(`/inscricoes/${id}`);
  return response.data;
};

export const retificarInscricao = async (
  id: number,
  arquivosDict: { [docId: number]: File }
): Promise<InscriptionDetail> => {
  const formData = new FormData();
  Object.entries(arquivosDict).forEach(([docId, file]) => {
    formData.append(`doc_${docId}`, file);
  });

  const response = await apiClient.put<InscriptionDetail>(
    `/inscricoes/${id}/retificar`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return response.data;
};

export const desistirInscricao = async (id: number, motivo?: string): Promise<InscriptionDetail> => {
  const response = await apiClient.post<InscriptionDetail>(`/inscricoes/${id}/desistir`, { motivo });
  return response.data;
};

export const downloadComprovante = async (id: number, protocolo: string): Promise<void> => {
  const response = await apiClient.get(`/inscricoes/${id}/comprovante`, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `comprovante_${protocolo}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
};
