import React, { useState, useEffect } from 'react';
import { FileText, Clock, AlertTriangle, CheckCircle, Download, CornerUpRight, Loader2, Ban } from 'lucide-react';
import { fetchMyApplications, downloadComprovante, desistirInscricao, InscriptionDetail } from '../api/inscricoes';
import { apiClient } from '../api/client';

export const MyApplicationsPage: React.FC = () => {
  const [inscrições, setInscricoes] = useState<InscriptionDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedForResource, setSelectedForResource] = useState<InscriptionDetail | null>(null);
  const [recursoTexto, setRecursoTexto] = useState('');
  const [submittingResource, setSubmittingResource] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchMyApplications();
      setInscricoes(data);
    } catch (err) {
      console.error('Erro ao carregar inscrições', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSendResource = async () => {
    if (!selectedForResource) return;
    if (recursoTexto.trim().length < 20) {
      alert('A argumentação do recurso deve possuir no mínimo 20 caracteres (RN-10).');
      return;
    }
    setSubmittingResource(true);
    try {
      await apiClient.post(`/inscricoes/${selectedForResource.id}/recursos`, {
        texto: recursoTexto,
      });
      alert('Recurso protocolado com sucesso na seleção!');
      setSelectedForResource(null);
      setRecursoTexto('');
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao submeter recurso.');
    } finally {
      setSubmittingResource(false);
    }
  };

  const handleDesistir = async (id: number) => {
    if (!confirm('Deseja realmente registrar a desistência desta candidatura? Esta ação é definitiva (INS-07).')) return;
    try {
      await desistirInscricao(id, 'Desistência voluntária pelo estudante.');
      alert('Inscrição cancelada com sucesso.');
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Não foi possível registrar a desistência.');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'HOMOLOGADA':
        return <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-0.5 rounded-full text-xs font-semibold">Homologada</span>;
      case 'INDEFERIDA':
        return <span className="bg-red-50 text-red-700 border border-red-200 px-2.5 py-0.5 rounded-full text-xs font-semibold">Indeferida</span>;
      case 'PENDENTE_VALIDACAO_VINCULO':
        return <span className="bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-0.5 rounded-full text-xs font-semibold">Pendente Vínculo</span>;
      case 'DESISTENTE':
        return <span className="bg-slate-100 text-slate-500 border border-slate-200 px-2.5 py-0.5 rounded-full text-xs font-semibold">Desistente</span>;
      default:
        return <span className="bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-full text-xs font-semibold">{status}</span>;
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Minhas Candidaturas (QUERO)</h2>
        <p className="mt-2 text-slate-600 text-sm">
          Acompanhe em tempo real a situação formal, o comprovante oficial e a interposição de recursos.
        </p>
      </div>

      {loading ? (
        <div className="text-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-500 text-sm">Consultando suas inscrições...</p>
        </div>
      ) : inscrições.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <FileText className="h-12 w-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-slate-900">Você ainda não possui inscrições</h3>
          <p className="text-sm text-slate-500 mt-1">Navegue pelas oportunidades na Vitrine para se candidatar.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {inscrições.map((insc) => (
            <div
              key={insc.id}
              className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                    {insc.protocolo}
                  </span>
                  {getStatusBadge(insc.status)}
                </div>

                <h3 className="text-base font-bold text-slate-900">
                  {insc.titulo_edital || `Edital #${insc.edital_id}`}
                </h3>

                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                  <span>Curso: <strong className="text-slate-700">{insc.curso_congelado}</strong></span>
                  <span>CR Congelado: <strong className="text-slate-700">{Number(insc.cr_congelado).toFixed(2)}</strong></span>
                  <span>Submetido em: {new Date(insc.data_submissao_original).toLocaleDateString('pt-BR')}</span>
                </div>

                {insc.motivos_indeferimento && insc.motivos_indeferimento.length > 0 && (
                  <div className="mt-2 text-xs text-red-600 bg-red-50 p-2.5 rounded-lg border border-red-100">
                    <p className="font-semibold">Motivo(s) do indeferimento:</p>
                    <ul className="list-disc list-inside mt-0.5">
                      {insc.motivos_indeferimento.map((m, idx) => (
                        <li key={idx}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2 pt-2 md:pt-0">
                <button
                  onClick={() => downloadComprovante(insc.id, insc.protocolo)}
                  className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 transition flex items-center"
                >
                  <Download className="h-3.5 w-3.5 mr-1 text-slate-500" />
                  Comprovante
                </button>

                {insc.status === 'HOMOLOGADA' && (
                  <button
                    onClick={() => setSelectedForResource(insc)}
                    className="px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg text-xs font-semibold text-blue-700 hover:bg-blue-100 transition flex items-center"
                  >
                    <CornerUpRight className="h-3.5 w-3.5 mr-1" />
                    Interpor Recurso
                  </button>
                )}

                {insc.status !== 'DESISTENTE' && (
                  <button
                    onClick={() => handleDesistir(insc.id)}
                    className="px-3 py-1.5 border border-red-100 rounded-lg text-xs font-medium text-red-600 hover:bg-red-50 transition flex items-center"
                  >
                    <Ban className="h-3.5 w-3.5 mr-1" />
                    Desistir
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Interposição de Recurso */}
      {selectedForResource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full border border-slate-200 p-6">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Interposição de Recurso (RN-10)</h3>
            <p className="text-xs text-slate-500 mb-4">
              Inscrição: {selectedForResource.protocolo} &mdash; Até 5000 caracteres.
            </p>

            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Justificativa e Fundamentação Técnica:
              </label>
              <textarea
                rows={5}
                value={recursoTexto}
                onChange={(e) => setRecursoTexto(e.target.value)}
                placeholder="Exponha com clareza as razões do seu pedido de reavaliação..."
                className="w-full p-3 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setSelectedForResource(null)}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs text-slate-700 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleSendResource}
                disabled={submittingResource}
                className="px-5 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 flex items-center disabled:opacity-50"
              >
                {submittingResource && <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />}
                Protocolar Recurso
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
