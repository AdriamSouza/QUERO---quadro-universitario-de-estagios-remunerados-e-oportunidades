import React, { useState, useEffect } from 'react';
import { ArrowLeft, Calendar, FileText, CheckCircle2, AlertCircle, Award, Users, DollarSign, Clock, Send } from 'lucide-react';
import { Edital } from '../types/edital';
import { fetchEditalById } from '../api/editais';
import { ApplicationModal } from '../components/ApplicationModal';

interface EditalDetailPageProps {
  editalId: number;
  onBack: () => void;
}

export const EditalDetailPage: React.FC<EditalDetailPageProps> = ({ editalId, onBack }) => {
  const [edital, setEdital] = useState<Edital | null>(null);
  const [loading, setLoading] = useState(true);
  const [showApplyModal, setShowApplyModal] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await fetchEditalById(editalId);
        setEdital(data);
      } catch (err) {
        console.error('Erro ao buscar detalhes do edital', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [editalId]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-slate-500 text-sm">Carregando detalhes da oportunidade...</p>
      </div>
    );
  }

  if (!edital) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <p className="text-red-600">Edital não encontrado.</p>
        <button onClick={onBack} className="mt-4 text-blue-600 underline text-sm">Voltar à lista</button>
      </div>
    );
  }

  const formatDateTime = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isAberto = edital.status === 'ABERTO';

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <button
        onClick={onBack}
        className="flex items-center text-sm font-medium text-slate-600 hover:text-slate-900 transition mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-1.5" />
        Voltar à Vitrine
      </button>

      {/* Cabeçalho */}
      <div className="bg-white rounded-xl border border-slate-200 p-8 shadow-sm mb-6">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-100">
            {edital.categoria} • {edital.modalidade}
          </span>
          <span className="text-sm font-mono text-slate-500">
            Edital #{edital.id}
          </span>
        </div>

        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mb-4">
          {edital.titulo}
        </h1>

        <p className="text-slate-700 text-sm leading-relaxed mb-8 whitespace-pre-line">
          {edital.descricao}
        </p>

        {/* Grade de Indicadores Rápidos */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
          <div>
            <span className="text-xs text-slate-500 flex items-center">
              <DollarSign className="h-3.5 w-3.5 mr-1 text-slate-400" />
              Bolsa / Auxílio
            </span>
            <p className="text-base font-bold text-slate-900 mt-0.5">
              R$ {Number(edital.valor_bolsa).toFixed(2)}
            </p>
          </div>

          <div>
            <span className="text-xs text-slate-500 flex items-center">
              <Users className="h-3.5 w-3.5 mr-1 text-slate-400" />
              Vagas
            </span>
            <p className="text-base font-bold text-slate-900 mt-0.5">
              {edital.vagas} vaga(s)
            </p>
          </div>

          <div>
            <span className="text-xs text-slate-500 flex items-center">
              <Clock className="h-3.5 w-3.5 mr-1 text-slate-400" />
              Carga Horária
            </span>
            <p className="text-base font-bold text-slate-900 mt-0.5">
              {edital.carga_horaria_semanal}h / semana
            </p>
          </div>

          <div>
            <span className="text-xs text-slate-500 flex items-center">
              <Award className="h-3.5 w-3.5 mr-1 text-slate-400" />
              CR Mínimo
            </span>
            <p className="text-base font-bold text-slate-900 mt-0.5">
              &ge; {Number(edital.cr_minimo).toFixed(2)}
            </p>
          </div>
        </div>

        {/* CTA Inscrição */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-100 pt-6">
          <div className="text-xs text-slate-500">
            {isAberto ? (
              <span className="text-emerald-600 font-medium flex items-center">
                <CheckCircle2 className="h-4 w-4 mr-1" />
                Inscrições abertas até {formatDateTime(edital.data_fim_inscricao)}
              </span>
            ) : (
              <span className="text-amber-600 font-medium flex items-center">
                <AlertCircle className="h-4 w-4 mr-1" />
                Edital com status: {edital.status}
              </span>
            )}
          </div>

          <button
            onClick={() => setShowApplyModal(true)}
            disabled={!isAberto}
            className={`w-full sm:w-auto px-6 py-2.5 rounded-lg text-sm font-semibold flex items-center justify-center transition shadow-sm ${
              isAberto
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-slate-200 text-slate-400 cursor-not-allowed'
            }`}
          >
            <Send className="h-4 w-4 mr-2" />
            Candidatar-se à Vaga
          </button>
        </div>
      </div>

      {/* Seção 2 Colunas: Cursos Elegíveis e Cronograma */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Cursos Autorizados */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 mr-2" />
            Cursos Elegíveis (RN-02)
          </h3>
          {edital.cursos && edital.cursos.length > 0 ? (
            <ul className="divide-y divide-slate-100 text-sm">
              {edital.cursos.map((c, idx) => (
                <li key={idx} className="py-2.5 flex items-center justify-between">
                  <span className="text-slate-800 font-medium">{c.nome_curso}</span>
                  <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                    {c.codigo_curso}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">Todos os cursos de graduação autorizados.</p>
          )}
        </div>

        {/* Cronograma Oficial */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center">
            <Calendar className="h-5 w-5 text-blue-600 mr-2" />
            Marcos do Cronograma
          </h3>
          <div className="space-y-3 text-xs">
            <div className="flex justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-600">Período de Inscrição:</span>
              <span className="font-semibold text-slate-900">
                {formatDateTime(edital.data_inicio_inscricao)} até {formatDateTime(edital.data_fim_inscricao)}
              </span>
            </div>
            <div className="flex justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-600">Início da Avaliação:</span>
              <span className="font-semibold text-slate-900">{formatDateTime(edital.data_inicio_avaliacao)}</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-600">Resultado Preliminar:</span>
              <span className="font-semibold text-slate-900">{formatDateTime(edital.data_resultado_preliminar)}</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-600">Janela de Recursos:</span>
              <span className="font-semibold text-slate-900">{edital.prazo_recurso_horas} horas após preliminar</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">Homologação Final:</span>
              <span className="font-semibold text-slate-900">{formatDateTime(edital.data_homologacao_final)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Documentos Exigidos */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center">
          <FileText className="h-5 w-5 text-blue-600 mr-2" />
          Documentos Obrigatórios (PDF, até 10 MB - RN-04)
        </h3>
        {edital.documentos_exigidos && edital.documentos_exigidos.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {edital.documentos_exigidos.map((doc) => (
              <div key={doc.id} className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-slate-900 text-sm">{doc.nome}</span>
                  {doc.obrigatorio && (
                    <span className="text-[10px] bg-red-50 text-red-700 font-bold px-1.5 py-0.5 rounded border border-red-200">
                      Obrigatório
                    </span>
                  )}
                </div>
                {doc.descricao && (
                  <p className="text-xs text-slate-600 mt-1">{doc.descricao}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Histórico Escolar e Declaração de Matrícula.</p>
        )}
      </div>

      {/* Modal de Submissão */}
      {showApplyModal && (
        <ApplicationModal
          edital={edital}
          onClose={() => setShowApplyModal(false)}
          onSuccess={() => {
            setShowApplyModal(false);
            alert('Candidatura submetida com sucesso no sistema QUERO!');
          }}
        />
      )}
    </div>
  );
};
