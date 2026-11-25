import React, { useEffect, useState } from 'react';
import { ClipboardCheck, Download, FileText, Loader2 } from 'lucide-react';
import { fetchEditais } from '../api/editais';
import { downloadArquivo, downloadComprovante, fetchEditalApplications, InscriptionDetail, reanalisarInscricao } from '../api/inscricoes';
import { getErrorMessage } from '../api/client';
import { Edital } from '../types/edital';
import { EditalSelect, EmptyState, InscricaoStatusBadge, Modal, PageHeader, Spinner, btn, inputClass } from '../components/ui';
import { useToast } from '../components/Toast';
import { formatDateTime, formatNumber, INSCRICAO_STATUS_LABEL } from '../utils/format';

export const DocumentReviewPage: React.FC = () => {
  const toast = useToast();
  const [editais, setEditais] = useState<Edital[]>([]);
  const [editalId, setEditalId] = useState<number | null>(null);
  const [filtro, setFiltro] = useState('');
  const [inscricoes, setInscricoes] = useState<InscriptionDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [selecionada, setSelecionada] = useState<InscriptionDetail | null>(null);
  const [justificativa, setJustificativa] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchEditais()
      .then((res) => {
        const lista = res.items.filter((e) => e.status !== 'RASCUNHO');
        setEditais(lista);
        if (lista.length) setEditalId(lista[0].id);
      })
      .catch((err) => toast.error(getErrorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = async () => {
    if (!editalId) return;
    setLoading(true);
    try {
      setInscricoes(await fetchEditalApplications(editalId, filtro || undefined));
    } catch (err) {
      toast.error(getErrorMessage(err));
      setInscricoes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editalId, filtro]);

  const edital = editais.find((e) => e.id === editalId);
  const analiseAberta = edital ? ['ABERTO', 'INSCRICOES_ENCERRADAS'].includes(edital.status) : false;

  const decidir = async (deferido: boolean) => {
    if (!selecionada) return;
    if (justificativa.trim().length < 20) return toast.error('A justificativa deve ter pelo menos 20 caracteres.');
    setSaving(true);
    try {
      await reanalisarInscricao(selecionada.id, deferido, justificativa.trim());
      toast.success(deferido ? 'Inscrição homologada.' : 'Inscrição indeferida.');
      setSelecionada(null);
      setJustificativa('');
      load();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const pendentes = inscricoes.filter((i) => i.status === 'PENDENTE_VALIDACAO_VINCULO').length;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="Inscrições"
        subtitle="Confira a documentação dos candidatos e homologue ou indefira inscrições até o início da avaliação de mérito."
      />

      <EditalSelect
        editais={editais}
        value={editalId}
        onChange={setEditalId}
        right={
          <div className="flex items-end gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Situação</label>
              <select value={filtro} onChange={(e) => setFiltro(e.target.value)} className="py-2 px-3 border border-slate-300 rounded-lg text-sm bg-white">
                <option value="">Todas</option>
                {Object.entries(INSCRICAO_STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <p className="text-xs text-slate-500 pb-2">{inscricoes.length} inscrição(ões){pendentes ? ` · ${pendentes} aguardando análise` : ''}</p>
          </div>
        }
      />

      {loading ? (
        <Spinner label="Carregando inscrições..." />
      ) : inscricoes.length === 0 ? (
        <EmptyState icon={<ClipboardCheck className="h-12 w-12" />} title="Nenhuma inscrição encontrada" description="Não há inscrições com os filtros selecionados." />
      ) : (
        <div className="space-y-3">
          {inscricoes.map((insc) => {
            const ativos = insc.arquivos.filter((a) => a.ativo);
            const podeAnalisar = analiseAberta && ['PENDENTE_VALIDACAO_VINCULO', 'INDEFERIDA'].includes(insc.status);
            return (
              <div key={insc.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">{insc.protocolo}</span>
                      <InscricaoStatusBadge status={insc.status} />
                    </div>
                    <h3 className="text-base font-bold text-slate-900">{insc.nome_estudante}</h3>
                    <p className="text-xs text-slate-500">
                      {insc.email_estudante} · Matrícula {insc.matricula_estudante || '-'} · {insc.curso_congelado} · CR {formatNumber(insc.cr_congelado)}
                      {insc.vinculo_ativo_congelado === null || insc.vinculo_ativo_congelado === undefined ? ' (declarado)' : ''}
                    </p>
                    <p className="text-xs text-slate-400">Inscrição em {formatDateTime(insc.data_submissao_original)}</p>
                    {insc.motivos_indeferimento && insc.motivos_indeferimento.length > 0 && (
                      <ul className="text-xs text-red-700 list-disc list-inside">
                        {insc.motivos_indeferimento.map((m) => <li key={m}>{m}</li>)}
                      </ul>
                    )}
                    <div className="flex flex-wrap gap-2 pt-1">
                      {ativos.map((a) => (
                        <button
                          key={a.id}
                          onClick={() => downloadArquivo(a).catch((err) => toast.error(getErrorMessage(err)))}
                          className="inline-flex items-center text-xs px-2.5 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700"
                        >
                          <FileText className="h-3.5 w-3.5 mr-1" /> {a.nome_original}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => downloadComprovante(insc.id, insc.protocolo).catch((err) => toast.error(getErrorMessage(err)))} className={btn.secondary}>
                      <Download className="h-4 w-4 mr-1.5" /> Comprovante
                    </button>
                    {podeAnalisar && (
                      <button onClick={() => setSelecionada(insc)} className={btn.primary}>Analisar</button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selecionada && (
        <Modal
          title="Análise da inscrição"
          subtitle={`${selecionada.nome_estudante} · ${selecionada.protocolo}`}
          onClose={() => setSelecionada(null)}
          footer={
            <>
              <button onClick={() => setSelecionada(null)} className={btn.secondary}>Cancelar</button>
              <button onClick={() => decidir(false)} disabled={saving} className={btn.danger}>Indeferir</button>
              <button onClick={() => decidir(true)} disabled={saving} className={btn.success}>
                {saving && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />} Homologar
              </button>
            </>
          }
        >
          <p className="text-sm text-slate-600 mb-3">
            Confira se o histórico comprova o vínculo ativo, o curso e o CR informados pelo candidato.
          </p>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Justificativa (mínimo de 20 caracteres)</label>
          <textarea rows={4} value={justificativa} onChange={(e) => setJustificativa(e.target.value)} className={inputClass} />
        </Modal>
      )}
    </div>
  );
};
