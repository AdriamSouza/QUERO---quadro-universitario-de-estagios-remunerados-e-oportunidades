import React, { useEffect, useState } from 'react';
import { CheckCircle2, Download, FileCheck2, Loader2, Table, Undo2 } from 'lucide-react';
import { fetchEditais } from '../api/editais';
import { downloadAtaPdf, downloadFolhaCsv, executeFinalHomologation, returnForAdjustments } from '../api/homologacao';
import { getErrorMessage } from '../api/client';
import { Edital } from '../types/edital';
import { EditalSelect, EditalStatusBadge, EmptyState, Modal, PageHeader, btn, inputClass } from '../components/ui';
import { useToast } from '../components/Toast';
import { formatDateTime } from '../utils/format';

const FASES = ['EM_RECURSO', 'EM_HOMOLOGACAO_FINAL', 'ENCERRADO'];

export const ExecutiveApprovalPage: React.FC = () => {
  const toast = useToast();
  const [editais, setEditais] = useState<Edital[]>([]);
  const [editalId, setEditalId] = useState<number | null>(null);
  const [despacho, setDespacho] = useState('Homologo o resultado final do processo seletivo, nos termos do edital.');
  const [busy, setBusy] = useState(false);
  const [showDevolver, setShowDevolver] = useState(false);
  const [justificativa, setJustificativa] = useState('');

  useEffect(() => {
    fetchEditais()
      .then((res) => {
        const lista = res.items.filter((e) => FASES.includes(e.status));
        setEditais(lista);
        const prioritario = lista.find((e) => e.status === 'EM_HOMOLOGACAO_FINAL') || lista[0];
        if (prioritario) setEditalId(prioritario.id);
      })
      .catch((err) => toast.error(getErrorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const edital = editais.find((e) => e.id === editalId) || null;
  const atualizarStatus = (status: string) => setEditais((prev) => prev.map((e) => (e.id === editalId ? { ...e, status } : e)));

  const homologar = async () => {
    if (!edital) return;
    if (!window.confirm('A homologação é definitiva: a classificação será oficializada e o edital encerrado. Deseja continuar?')) return;
    setBusy(true);
    try {
      await executeFinalHomologation(edital.id, despacho.trim());
      atualizarStatus('ENCERRADO');
      toast.success('Resultado homologado. A ata e a lista final foram geradas.');
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const devolver = async () => {
    if (!edital) return;
    if (justificativa.trim().length < 15) return toast.error('A justificativa deve ter pelo menos 15 caracteres.');
    setBusy(true);
    try {
      await returnForAdjustments(edital.id, justificativa.trim());
      atualizarStatus('EM_AVALIACAO');
      toast.success('Processo devolvido à comissão avaliadora.');
      setShowDevolver(false);
      setJustificativa('');
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const baixar = (fn: (id: number) => Promise<void>) => edital && fn(edital.id).catch((err) => toast.error(getErrorMessage(err)));

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader title="Homologação" subtitle="Homologação do resultado final, emissão da ata e exportação da lista de contemplados." />

      {editais.length === 0 ? (
        <EmptyState icon={<FileCheck2 className="h-12 w-12" />} title="Nenhum edital em fase de homologação" description="Editais aparecem aqui após a publicação do resultado preliminar." />
      ) : (
        <>
          <EditalSelect editais={editais} value={editalId} onChange={setEditalId} right={edital ? <EditalStatusBadge status={edital.status} /> : undefined} />

          {edital && (
            <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              {edital.status === 'EM_RECURSO' && (
                <p className="mb-4 text-sm bg-amber-50 border border-amber-200 text-amber-900 rounded-lg p-3">
                  Prazo de recursos em andamento
                  {edital.data_publicacao_preliminar
                    ? ` (encerra em ${formatDateTime(new Date(new Date(edital.data_publicacao_preliminar).getTime() + edital.prazo_recurso_horas * 3600000).toISOString())})`
                    : ''}
                  . A homologação fica disponível após o prazo e o julgamento de todos os recursos.
                </p>
              )}

              {edital.status !== 'ENCERRADO' ? (
                <>
                  <label className="block text-sm font-semibold text-slate-800 mb-1">Despacho da ata</label>
                  <textarea rows={3} value={despacho} onChange={(e) => setDespacho(e.target.value)} className={`${inputClass} mb-4`} />
                  <div className="flex flex-wrap justify-end gap-2">
                    {edital.status === 'EM_HOMOLOGACAO_FINAL' && (
                      <button onClick={() => setShowDevolver(true)} disabled={busy} className="inline-flex items-center px-4 py-2 border border-amber-200 bg-amber-50 rounded-lg text-sm font-semibold text-amber-800 hover:bg-amber-100">
                        <Undo2 className="h-4 w-4 mr-1.5" /> Devolver à comissão
                      </button>
                    )}
                    <button onClick={homologar} disabled={busy || edital.status !== 'EM_HOMOLOGACAO_FINAL'} className={btn.success}>
                      {busy ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <CheckCircle2 className="h-4 w-4 mr-1.5" />} Homologar resultado final
                    </button>
                  </div>
                </>
              ) : (
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <p className="text-sm text-emerald-800 flex items-center"><CheckCircle2 className="h-5 w-5 mr-2 text-emerald-600" /> Resultado final homologado.</p>
                  <div className="flex gap-2">
                    <button onClick={() => baixar(downloadAtaPdf)} className={btn.secondary}><Download className="h-4 w-4 mr-1.5" /> Ata (PDF)</button>
                    <button onClick={() => baixar(downloadFolhaCsv)} className={btn.secondary}><Table className="h-4 w-4 mr-1.5" /> Lista final (CSV)</button>
                  </div>
                </div>
              )}
            </section>
          )}
        </>
      )}

      {showDevolver && (
        <Modal
          title="Devolver à comissão avaliadora"
          subtitle="O edital volta para a fase de avaliação para correções."
          onClose={() => setShowDevolver(false)}
          footer={
            <>
              <button onClick={() => setShowDevolver(false)} className={btn.secondary}>Cancelar</button>
              <button onClick={devolver} disabled={busy} className="inline-flex items-center px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-semibold hover:bg-amber-700">Confirmar devolução</button>
            </>
          }
        >
          <label className="block text-xs font-semibold text-slate-700 mb-1">Justificativa</label>
          <textarea rows={4} value={justificativa} onChange={(e) => setJustificativa(e.target.value)} className={inputClass} />
        </Modal>
      )}
    </div>
  );
};
