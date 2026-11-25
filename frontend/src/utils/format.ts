export const EDITAL_STATUS_LABEL: Record<string, string> = {
  RASCUNHO: 'Rascunho',
  ABERTO: 'Inscrições abertas',
  INSCRICOES_ENCERRADAS: 'Inscrições encerradas',
  EM_AVALIACAO: 'Em avaliação',
  RESULTADO_PRELIMINAR: 'Resultado preliminar',
  EM_RECURSO: 'Prazo de recursos',
  EM_HOMOLOGACAO_FINAL: 'Aguardando homologação',
  ENCERRADO: 'Encerrado',
  CANCELADO: 'Cancelado',
};

export const EDITAL_STATUS_STYLE: Record<string, string> = {
  RASCUNHO: 'bg-slate-100 text-slate-600 border-slate-200',
  ABERTO: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  INSCRICOES_ENCERRADAS: 'bg-amber-50 text-amber-700 border-amber-200',
  EM_AVALIACAO: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  EM_RECURSO: 'bg-orange-50 text-orange-700 border-orange-200',
  EM_HOMOLOGACAO_FINAL: 'bg-purple-50 text-purple-700 border-purple-200',
  ENCERRADO: 'bg-slate-100 text-slate-700 border-slate-200',
  CANCELADO: 'bg-red-50 text-red-700 border-red-200',
};

export const INSCRICAO_STATUS_LABEL: Record<string, string> = {
  PENDENTE_VALIDACAO_VINCULO: 'Em análise',
  HOMOLOGADA: 'Homologada',
  INDEFERIDA: 'Indeferida',
  DESISTENTE: 'Desistente',
};

export const INSCRICAO_STATUS_STYLE: Record<string, string> = {
  PENDENTE_VALIDACAO_VINCULO: 'bg-amber-50 text-amber-700 border-amber-200',
  HOMOLOGADA: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  INDEFERIDA: 'bg-red-50 text-red-700 border-red-200',
  DESISTENTE: 'bg-slate-100 text-slate-500 border-slate-200',
};

export const CATEGORIA_LABEL: Record<string, string> = {
  ESTAGIO: 'Estágio',
  MONITORIA: 'Monitoria',
  BOLSA: 'Bolsa',
};

export const PERFIL_LABEL: Record<string, string> = {
  ESTUDANTE: 'Estudante',
  AVALIADOR: 'Avaliador(a)',
  PRO_REITOR: 'Pró-Reitoria',
};

export const formatDate = (value?: string | null): string =>
  value ? new Date(value).toLocaleDateString('pt-BR') : '-';

export const formatDateTime = (value?: string | null): string =>
  value
    ? new Date(value).toLocaleString('pt-BR', {
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : '-';

export const formatMoney = (value: number | string): string =>
  Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export const formatNumber = (value: number | string | null | undefined, digits = 2): string =>
  value === null || value === undefined || value === '' ? '-' : Number(value).toFixed(digits).replace('.', ',');

export const saveBlob = (data: BlobPart, filename: string, type: string) => {
  const url = window.URL.createObjectURL(new Blob([data], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => window.URL.revokeObjectURL(url), 1000);
};
