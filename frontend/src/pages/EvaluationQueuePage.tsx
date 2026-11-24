import React, { useState, useEffect } from 'react';
import { Award, UserCheck, Star, Download, CheckCircle2, AlertCircle, Loader2, ShieldAlert } from 'lucide-react';
import { fetchEditais } from '../api/editais';
import { fetchEvaluationQueue, submitEvaluation } from '../api/avaliacoes';
import { InscriptionDetail } from '../api/inscricoes';
import { Edital } from '../types/edital';

export const EvaluationQueuePage: React.FC = () => {
  const [editais, setEditais] = useState<Edital[]>([]);
  const [selectedEdital, setSelectedEdital] = useState<Edital | null>(null);
  const [fila, setFila] = useState<InscriptionDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [evaluatingInscricao, setEvaluatingInscricao] = useState<InscriptionDetail | null>(null);

  // Form states
  const [declaracaoSemImpedimento, setDeclaracaoSemImpedimento] = useState(false);
  const [notaMerito, setNotaMerito] = useState<number>(8.0);
  const [parecer, setParecer] = useState<'DEFERIDO' | 'INDEFERIDO'>('DEFERIDO');
  const [justificativa, setJustificativa] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchEditais();
        setEditais(res.items);
        if (res.items.length > 0) {
          setSelectedEdital(res.items[0]);
        }
      } catch (err) {
        console.error(err);
      }
    };
    load();
  }, []);

  const loadQueue = async () => {
    if (!selectedEdital) return;
    setLoading(true);
    try {
      const res = await fetchEvaluationQueue(selectedEdital.id);
      setFila(res);
    } catch (err) {
      console.error(err);
      setFila([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [selectedEdital]);

  const openEvaluationModal = (insc: InscriptionDetail) => {
    setEvaluatingInscricao(insc);
    setDeclaracaoSemImpedimento(false);
    setNotaMerito(8.0);
    setParecer('DEFERIDO');
    setJustificativa('');
  };

  const handleSaveEvaluation = async (confirmar: boolean) => {
    if (!evaluatingInscricao) return;
    if (!declaracaoSemImpedimento) {
      alert('É obrigatório assinalar a declaração de ausência de impedimento ou suspeição (RN-07).');
      return;
    }
    if (notaMerito < 0 || notaMerito > 10) {
      alert('A nota de mérito deve variar de 0,00 a 10,00 (RN-08).');
      return;
    }
    if (parecer === 'INDEFERIDO' && justificativa.trim().length < 15) {
      alert('Justificativa técnica obrigatória com pelo menos 15 caracteres para parecer indeferido (RN-08).');
      return;
    }

    setSubmitting(true);
    try {
      await submitEvaluation(evaluatingInscricao.id, {
        declaracao_sem_impedimento: declaracaoSemImpedimento,
        nota_merito: notaMerito,
        parecer,
        justificativa: parecer === 'INDEFERIDO' ? justificativa : undefined,
        confirmar,
      });

      alert(confirmar ? 'Avaliação confirmada com sucesso!' : 'Rascunho de avaliação salvo.');
      setEvaluatingInscricao(null);
      loadQueue();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao registrar avaliação.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Avaliação de Mérito (QUERO)</h2>
        <p className="mt-2 text-slate-600 text-sm">
          Fila exclusiva da comissão avaliadora &mdash; Inscrições homologadas do edital designado (AVA-01, RN-06, RN-07).
        </p>
      </div>

      {/* Seletor de Edital */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="w-full sm:w-auto">
          <label className="block text-xs font-semibold text-slate-500 mb-1">Selecionar Edital Designado:</label>
          <select
            value={selectedEdital?.id || ''}
            onChange={(e) => {
              const id = Number(e.target.value);
              const found = editais.find((item) => item.id === id);
              setSelectedEdital(found || null);
            }}
            className="w-full sm:w-96 py-2 px-3 border border-slate-300 rounded-lg text-sm bg-white font-medium text-slate-800"
          >
            {editais.map((e) => (
              <option key={e.id} value={e.id}>
                Edital #{e.id} &mdash; {e.titulo} ({e.status})
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs text-slate-500 font-medium">
          Candidaturas Homologadas na fila: <strong className="text-slate-900">{fila.length}</strong>
        </div>
      </div>

      {/* Fila de Inscrições */}
      {loading ? (
        <div className="text-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-500 text-sm">Carregando candidatos da banca...</p>
        </div>
      ) : fila.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <CheckCircle2 className="h-12 w-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-slate-900">Nenhuma candidatura pendente</h3>
          <p className="text-sm text-slate-500 mt-1">Todas as inscrições homologadas já foram avaliadas ou aguardam homologação.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {fila.map((insc) => (
            <div
              key={insc.id}
              className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                    {insc.protocolo}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold">
                    HOMOLOGADA
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900">
                  {insc.nome_estudante || `Candidato #${insc.estudante_id}`}
                </h3>

                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                  <span>Curso: <strong className="text-slate-700">{insc.curso_congelado}</strong></span>
                  <span>CR Congelado: <strong className="text-slate-700">{Number(insc.cr_congelado).toFixed(2)}</strong></span>
                  <span>Documentos anexados: <strong className="text-slate-700">{insc.arquivos?.length || 0} PDF(s)</strong></span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => openEvaluationModal(insc)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition flex items-center shadow-sm"
                >
                  <Star className="h-3.5 w-3.5 mr-1.5" />
                  Avaliar Mérito
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal de Lançamento de Notas */}
      {evaluatingInscricao && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full border border-slate-200 p-6 my-8">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Avaliação de Mérito Acadêmico</h3>
            <p className="text-xs text-slate-500 mb-4">
              Candidato: {evaluatingInscricao.nome_estudante || evaluatingInscricao.protocolo} &mdash; Curso: {evaluatingInscricao.curso_congelado} (CR {Number(evaluatingInscricao.cr_congelado).toFixed(2)})
            </p>

            {/* Declaração de Ausência de Impedimento (RN-07) */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl mb-4">
              <label className="flex items-start space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={declaracaoSemImpedimento}
                  onChange={(e) => setDeclaracaoSemImpedimento(e.target.checked)}
                  className="mt-0.5 rounded text-blue-600 focus:ring-blue-500 h-4 w-4"
                />
                <span className="text-xs text-amber-900 leading-tight">
                  <strong>Declaração Obrigatória (RN-07):</strong> Declaro não possuir impedimento legal, suspeição, parentesco ou vínculo direto de orientação com este candidato.
                </span>
              </label>
            </div>

            {/* Nota de Mérito (RN-08) */}
            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Nota de Mérito (0,00 a 10,00):
              </label>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={notaMerito}
                onChange={(e) => setNotaMerito(parseFloat(e.target.value) || 0)}
                className="w-full p-2.5 border border-slate-300 rounded-lg text-sm font-bold text-slate-900 focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Parecer */}
            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-700 mb-1">Parecer da Comissão:</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setParecer('DEFERIDO')}
                  className={`py-2 rounded-lg text-xs font-bold transition border ${
                    parecer === 'DEFERIDO'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-300 shadow-sm'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  Deferido
                </button>
                <button
                  type="button"
                  onClick={() => setParecer('INDEFERIDO')}
                  className={`py-2 rounded-lg text-xs font-bold transition border ${
                    parecer === 'INDEFERIDO'
                      ? 'bg-red-50 text-red-700 border-red-300 shadow-sm'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  Indeferido
                </button>
              </div>
            </div>

            {/* Justificativa (se indeferido) */}
            {parecer === 'INDEFERIDO' && (
              <div className="mb-4">
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Justificativa Técnica do Indeferimento (RN-08):
                </label>
                <textarea
                  rows={3}
                  value={justificativa}
                  onChange={(e) => setJustificativa(e.target.value)}
                  placeholder="Informe a motivação técnica formal com pelo menos 15 caracteres..."
                  className="w-full p-2.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            {/* Ações */}
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEvaluatingInscricao(null)}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs text-slate-700 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => handleSaveEvaluation(false)}
                disabled={submitting}
                className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-200"
              >
                Salvar Rascunho
              </button>
              <button
                type="button"
                onClick={() => handleSaveEvaluation(true)}
                disabled={submitting}
                className="px-5 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 flex items-center"
              >
                {submitting && <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />}
                Confirmar Avaliação
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
