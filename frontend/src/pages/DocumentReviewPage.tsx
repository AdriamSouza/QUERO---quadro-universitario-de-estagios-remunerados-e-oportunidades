import React, { useState, useEffect } from 'react';
import { ShieldCheck, CheckCircle2, XCircle, FileText, Download, AlertCircle, Loader2 } from 'lucide-react';
import { fetchEditais } from '../api/editais';
import { apiClient } from '../api/client';
import { InscriptionDetail } from '../api/inscricoes';
import { Edital } from '../types/edital';

export const DocumentReviewPage: React.FC = () => {
  const [editais, setEditais] = useState<Edital[]>([]);
  const [selectedEditalId, setSelectedEditalId] = useState<number | null>(null);
  const [inscrições, setInscricoes] = useState<InscriptionDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedInscricao, setSelectedInscricao] = useState<InscriptionDetail | null>(null);
  const [justificativa, setJustificativa] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const loadEditais = async () => {
      try {
        const res = await fetchEditais();
        setEditais(res.items);
        if (res.items.length > 0) {
          setSelectedEditalId(res.items[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadEditais();
  }, []);

  const loadInscricoes = async () => {
    if (!selectedEditalId) return;
    setLoading(true);
    try {
      // Busca inscrições deste edital
      const res = await apiClient.get<any>(`/editais/${selectedEditalId}`);
      // As inscrições podem ser carregadas pelo endpoint de avaliacoes ou geral
      const avRes = await apiClient.get<InscriptionDetail[]>(`/editais/${selectedEditalId}/avaliacoes`);
      setInscricoes(avRes.data);
    } catch (err) {
      setInscricoes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInscricoes();
  }, [selectedEditalId]);

  const handleReanalisar = async (deferido: boolean) => {
    if (!selectedInscricao) return;
    if (justificativa.trim().length < 20) {
      alert('A justificativa de reanálise deve possuir pelo menos 20 caracteres (RN-05).');
      return;
    }

    setSaving(true);
    try {
      await apiClient.post(`/inscricoes/${selectedInscricao.id}/reanalisar`, {
        deferido,
        justificativa,
      });
      alert(deferido ? 'Inscrição homologada em reanálise manual!' : 'Indeferimento mantido.');
      setSelectedInscricao(null);
      setJustificativa('');
      loadInscricoes();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao reanalisar inscrição.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Reanálise de Inscrições (Pró-Reitoria)</h2>
        <p className="mt-2 text-slate-600 text-sm">
          Reanálise manual de indeferimentos de candidaturas até a data de início da avaliação de mérito (RN-05, RN-14).
        </p>
      </div>

      {/* Seletor de Edital */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="w-full sm:w-auto">
          <label className="block text-xs font-semibold text-slate-500 mb-1">Selecionar Edital:</label>
          <select
            value={selectedEditalId || ''}
            onChange={(e) => setSelectedEditalId(Number(e.target.value))}
            className="w-full sm:w-96 py-2 px-3 border border-slate-300 rounded-lg text-sm bg-white font-medium text-slate-800"
          >
            {editais.map((e) => (
              <option key={e.id} value={e.id}>
                Edital #{e.id} &mdash; {e.titulo}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-500 text-sm">Carregando inscrições...</p>
        </div>
      ) : inscrições.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <ShieldCheck className="h-12 w-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-slate-900">Nenhuma inscrição com pendência de reanálise</h3>
          <p className="text-sm text-slate-500 mt-1">Todas as candidaturas foram validadas pelo processamento formal automático.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {inscrições.map((insc) => (
            <div
              key={insc.id}
              className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                    {insc.protocolo}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded font-semibold bg-emerald-50 text-emerald-700">
                    {insc.status}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900">{insc.nome_estudante || `Estudante #${insc.estudante_id}`}</h3>
                <p className="text-xs text-slate-500">Curso: {insc.curso_congelado} | CR: {Number(insc.cr_congelado).toFixed(2)}</p>
              </div>

              <button
                onClick={() => setSelectedInscricao(insc)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition"
              >
                Reanalisar Candidatura
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Modal Reanálise */}
      {selectedInscricao && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full border border-slate-200 p-6">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Reanálise Manual de Homologação (RN-05)</h3>
            <p className="text-xs text-slate-500 mb-4">Inscrição: {selectedInscricao.protocolo}</p>

            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Justificativa Obrigatória (mínimo 20 caracteres):
              </label>
              <textarea
                rows={4}
                value={justificativa}
                onChange={(e) => setJustificativa(e.target.value)}
                placeholder="Informe a motivação para alterar a decisão formal..."
                className="w-full p-2.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setSelectedInscricao(null)}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs text-slate-700 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => handleReanalisar(false)}
                disabled={saving}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-semibold hover:bg-red-700"
              >
                Manter Indeferida
              </button>
              <button
                onClick={() => handleReanalisar(true)}
                disabled={saving}
                className="px-5 py-2 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 flex items-center"
              >
                {saving && <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />}
                Homologar Inscrição
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
