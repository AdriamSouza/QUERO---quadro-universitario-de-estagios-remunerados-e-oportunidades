export interface EditalCurso {
  id?: number;
  codigo_curso: string;
  nome_curso: string;
}

export interface EditalDocumentoExigido {
  id: number;
  edital_id: number;
  nome: string;
  descricao?: string;
  obrigatorio: boolean;
}

export interface ComissaoMembro {
  id: number;
  edital_id: number;
  avaliador_id: number;
  avaliador_nome?: string;
  avaliador_email?: string;
  designado_em: string;
}

export interface Edital {
  id: number;
  titulo: string;
  descricao: string;
  categoria: 'ESTAGIO' | 'MONITORIA' | 'BOLSA';
  modalidade: string;
  valor_bolsa: number | string;
  carga_horaria_semanal: number;
  vagas: number;
  cr_minimo: number | string;
  prazo_recurso_horas: number;
  criterios_pontuacao?: Record<string, unknown> | unknown[];
  criterios_desempate?: string[];
  status: string;
  data_inicio_inscricao: string;
  data_fim_inscricao: string;
  data_inicio_avaliacao: string;
  data_resultado_preliminar: string;
  data_homologacao_final: string;
  justificativa_cancelamento?: string | null;
  data_publicacao_preliminar?: string | null;
  criado_por?: number;
  criado_em: string;
  cursos?: EditalCurso[];
  documentos_exigidos?: EditalDocumentoExigido[];
  comissao?: ComissaoMembro[];
}

export interface EditalListResponse {
  items: Edital[];
  total: number;
}
