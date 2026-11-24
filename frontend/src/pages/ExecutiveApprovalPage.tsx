import React, { useState, useEffect } from 'react';
import { FileCheck2, Download, Table, CheckCircle2, AlertTriangle, ShieldAlert, Loader2, Undo2 } from 'lucide-react';
import { fetchEditais } from '../api/editais';
import { executeFinalHomologation, returnForAdjustments, AtaHomologacaoResponse } from '../api/homologacao';
import { apiClient } from '../api/client';
import { Edital } from '../types/edital';

export const ExecutiveApprovalPage: React.FC = () => {
  const [editais, setEditais] = useState<Edital[]>([]);
  const [selectedEdital, setSelectedEdital] = useState<Edital | null>(null);
  const [loading, setLoading] = useState(false);
  const [despacho, setDespacho] = useState('Homologo o resultado final do processo seletivo em estrita observância às disposições do edital.');
  const [homologating, setHomologating] = useState(false);
  const [homologatedInfo, setHomologatedInfo] = useState<AtaHomologacaoResponse | null>(null);

  // Devolver para ajustes
  const [showDevolverModal, setShowDevolverModal] = useState(false);
  const [justificativaAjuste, setJustificativaAjuste] = useState('');
  const [devolvendo, setDevolvendo] = useState(false);

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

  const handleHomologate = async () => {
    if (!selectedEdital) return;
    const confirm = window.confirm(
      'ATENÇÃO: A homologação do resultado final é um ato formal IRREVOGÁVEL (RN-13). As notas e a classificação serão congeladas definitivamente no sistema. Deseja prosseguir?'
    );
    if (!confirm) return;

    setHomologating(true);
    try {
      const res = await executeFinalHomologation(selectedEdital.id, despacho);
      setHomologatedInfo(res);
      alert('Edital homologado com sucesso! Ata oficial e listas finais em PDF/CSV geradas.');
      setSelectedEdital({ ...selectedEdital, status: 'ENCERRADO' });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao homologar edital.');
    } finally {
      setHomologating(false);
    }
  };

  const handleDevolverAjustes = async () => {
    if (!selectedEdital) return;
    if (justificativaAjuste.trim().length < 15) {
      alert('A justificativa de devolução para ajustes deve conter pelo menos 15 caracteres (HOM-01).');
      return;
    }

    setDevolvendo(true);
    try {
      await returnForAdjustments(selectedEdital.id, justificativaAjuste);
      alert('Processo devolvido para a comissão examinadora com sucesso (status: EM_AVALIACAO).');
      setShowDevolverModal(false);
      setJustificativaAjuste('');
      setSelectedEdital({ ...selectedEdital, status: 'EM_AVALIACAO' });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao devolver para ajustes.');
    } finally {
      setDevolvendo(false);
    }
  };

  const downloadAtaPdf = () => {
    if (!selectedEdital) return;
    window.open(`${apiClient.defaults.baseURL}/editais/${selectedEdital.id}/ata-pdf`, '_blank');
  };

  const downloadFolhaCsv = () => {
    if (!selectedEdital) return;
    window.open(`${apiClient.defaults.baseURL}/editais/${selectedEdital.id}/folha-csv`, '_blank');
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Homologação Final (Pró-Reitoria)</h2>
        <p className="mt-2 text-slate-600 text-sm">
          Ato administrativo formal e imutável que encerra o processo seletivo e oficializa os candidatos contemplados (HOM-01, HOM-02, RN-13).
        </p>
      </div>

      {/* Seletor de Edital */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="w-full sm:w-auto">
          <label className="block text-xs font-semibold text-slate-500 mb-1">Selecionar Edital:</label>
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
          Status Atual: <strong className="text-slate-900">{selectedEdital?.status}</strong>
        </div>
      </div>

      {/* Painel de Decisão do Pró-Reitor */}
      {selectedEdital && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
          <h3 className="text-base font-bold text-slate-900 mb-3 flex items-center">
            <FileCheck2 className="h-5 w-5 text-blue-600 mr-2" />
            Despacho e Validação de Encerramento (HOM-01)
          </h3>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Texto do Despacho Administrativo da Ata:
            </label>
            <textarea
              rows={3}
              value={despacho}
              onChange={(e) => setDespacho(e.target.value)}
              className="w-full p-2.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100">
            <div className="flex gap-2">
              <button
                onClick={downloadAtaPdf}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 transition flex items-center"
              >
                <Download className="h-4 w-4 mr-1.5 text-slate-500" />
                Baixar Ata Oficial (PDF)
              </button>
              <button
                onClick={downloadFolhaCsv}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 transition flex items-center"
              >
                <Table className="h-4 w-4 mr-1.5 text-slate-500" />
                Exportar Folha (CSV)
              </button>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setShowDevolverModal(true)}
                className="px-4 py-2 border border-amber-200 bg-amber-50 rounded-lg text-xs font-semibold text-amber-800 hover:bg-amber-100 transition flex items-center"
              >
                <Undo2 className="h-4 w-4 mr-1.5 text-amber-600" />
                Devolver para Ajustes
              </button>

              <button
                onClick={handleHomologate}
                disabled={homologating || selectedEdital.status === 'ENCERRADO'}
                className="px-5 py-2 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 transition flex items-center shadow-sm disabled:opacity-50"
              >
                {homologating && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}
                <CheckCircle2 className="h-4 w-4 mr-1.5" />
                Homologar Resultado Final
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Devolver para Ajustes */}
      {showDevolverModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full border border-slate-200 p-6">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Devolver para Ajustes (HOM-01)</h3>
            <p className="text-xs text-slate-500 mb-4">
              Informe a motivação formal para reabertura de avaliação de mérito pela banca.
            </p>

            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Justificativa Obrigatória (mínimo 15 caracteres):
              </label>
              <textarea
                rows={4}
                value={justificativaAjuste}
                onChange={(e) => setJustificativaAjuste(e.target.value)}
                placeholder="Identificada inconformidade procedimental..."
                className="w-full p-2.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDevolverModal(false)}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs text-slate-700 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleDevolverAjustes}
                disabled={devolvendo}
                className="px-5 py-2 bg-amber-600 text-white rounded-lg text-xs font-semibold hover:bg-amber-700 flex items-center disabled:opacity-50"
              >
                {devolvendo && <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />}
                Confirmar Devolução
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
