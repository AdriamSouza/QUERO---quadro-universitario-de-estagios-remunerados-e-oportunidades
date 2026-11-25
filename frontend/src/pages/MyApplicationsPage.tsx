import React, { useEffect, useState } from 'react';
import { Ban, CornerUpRight, Download, ExternalLink, FileText, Loader2, Upload } from 'lucide-react';
import {
  desistirInscricao, downloadComprovante, fetchMyApplications, InscriptionDetail, interporRecurso, retificarInscricao,
} from '../api/inscricoes';
import { fetchEditalById } from '../api/editais';
import { getErrorMessage } from '../api/client';
import { Edital } from '../types/edital';
import { EditalStatusBadge, EmptyState, InscricaoStatusBadge, Modal, PageHeader, Spinner, btn, inputClass } from '../components/ui';
import { useToast } from '../components/Toast';
import { formatDate, formatNumber } from '../utils/format';

const RECURSO_LABEL: Record<string, string> = {
  ABERTO: 'Recurso em análise',
  EM_ANALISE: 'Recurso em análise',
  DEFERIDO: 'Recurso deferido',
  INDEFERIDO: 'Recurso indeferido',
};

const RetificarModal: React.FC<{ inscricao: InscriptionDetail; onClose: () => void; onDone: () => void }> = ({ inscricao, onClose, onDone }) => {
  const toast = useToast();
  const [edital, setEdital] = useState<Edital | null>(null);
  const [files, setFiles] = useState<{ [docId: number]: File }>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchEditalById(inscricao.edital_id).then(setEdital).catch((err) => toast.error(getErrorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inscricao.edital_id]);

  const submit = async () => {
    if (Object.keys(files).length === 0) return toast.error('Selecione ao menos um arquivo.');
    setSaving(true);
    try {
      await retificarInscricao(inscricao.id, files);
      toast.success('Documentos substituídos com sucesso.');
      onDone();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Substituir documentos"
      subtitle={`Inscrição ${inscricao.protocolo} — o protocolo e a data original da inscrição são mantidos.`}
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className={btn.secondary}>Cancelar</button>
          <button onClick={submit} disabled={saving} className={btn.primary}>
            {saving && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />} Enviar
          </button>
        </>
      }
    >
      {!edital ? <Spinner /> : (
        <div className="space-y-3">
          {(edital.documentos_exigidos || []).map((doc) => {
            const atual = inscricao.arquivos.find((a) => a.documento_exigido_id === doc.id && a.ativo);
            return (
              <div key={doc.id} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <p className="text-sm font-medium text-slate-800">{doc.nome}</p>
                <p className="text-xs text-slate-500 mb-2">{atual ? `Atual: ${atual.nome_original} (versão ${atual.versao})` : 'Nenhum arquivo enviado'}</p>
                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) setFiles((prev) => ({ ...prev, [doc.id]: f }));
                  }}
                  className="block w-full text-xs text-slate-500 file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border-0 file:bg-blue-50 file:text-blue-700"
                />
              </div>
            );
          })}
        </div>
      )}
    </Modal>
  );
};

export const MyApplicationsPage: React.FC<{ onSelectEdital: (id: number) => void }> = ({ onSelectEdital }) => {
  const toast = useToast();
  const [inscricoes, setInscricoes] = useState<InscriptionDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [recursoPara, setRecursoPara] = useState<InscriptionDetail | null>(null);
  const [recursoTexto, setRecursoTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [retificar, setRetificar] = useState<InscriptionDetail | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      setInscricoes(await fetchMyApplications());
    } catch (err) {
      toast.error(getErrorMessage(err, 'Não foi possível carregar suas inscrições.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const enviarRecurso = async () => {
    if (!recursoPara) return;
    if (recursoTexto.trim().length < 20) return toast.error('Descreva o recurso com pelo menos 20 caracteres.');
    setEnviando(true);
    try {
      await interporRecurso(recursoPara.id, recursoTexto.trim());
      toast.success('Recurso enviado. Você será notificado(a) do julgamento.');
      setRecursoPara(null);
      setRecursoTexto('');
      loadData();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setEnviando(false);
    }
  };

  const desistir = async (insc: InscriptionDetail) => {
    if (!window.confirm(`Confirmar a desistência da inscrição ${insc.protocolo}? Esta ação não pode ser desfeita.`)) return;
    try {
      await desistirInscricao(insc.id, 'Desistência solicitada pelo estudante.');
      toast.success('Desistência registrada.');
      loadData();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader title="Minhas inscrições" subtitle="Acompanhe a situação das suas candidaturas, baixe comprovantes e interponha recursos." />

      {loading ? (
        <Spinner label="Carregando suas inscrições..." />
      ) : inscricoes.length === 0 ? (
        <EmptyState icon={<FileText className="h-12 w-12" />} title="Você ainda não possui inscrições" description="Consulte os editais abertos para se candidatar." />
      ) : (
        <div className="space-y-4">
          {inscricoes.map((insc) => {
            const statusEdital = insc.status_edital || '';
            const podeRetificar = statusEdital === 'ABERTO' && insc.status !== 'DESISTENTE';
            const podeRecorrer = statusEdital === 'EM_RECURSO' && insc.status === 'HOMOLOGADA' && !insc.recurso_status;
            const podeDesistir = ['ABERTO', 'INSCRICOES_ENCERRADAS', 'EM_AVALIACAO'].includes(statusEdital) && insc.status !== 'DESISTENTE';
            const av = insc.avaliacao_resumo;
            return (
              <div key={insc.id} className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">{insc.protocolo}</span>
                      <InscricaoStatusBadge status={insc.status} />
                      {statusEdital && <EditalStatusBadge status={statusEdital} />}
                    </div>
                    <button onClick={() => onSelectEdital(insc.edital_id)} className="text-base font-bold text-slate-900 hover:text-blue-700 flex items-center text-left">
                      {insc.titulo_edital || `Edital nº ${insc.edital_id}`} <ExternalLink className="h-3.5 w-3.5 ml-1.5 text-slate-400" />
                    </button>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span>Curso: <strong className="text-slate-700">{insc.curso_congelado || '-'}</strong></span>
                      <span>CR: <strong className="text-slate-700">{formatNumber(insc.cr_congelado)}</strong></span>
                      <span>Inscrição em {formatDate(insc.data_submissao_original)}</span>
                      {insc.data_ultima_retificacao && <span>Última substituição em {formatDate(insc.data_ultima_retificacao)}</span>}
                    </div>
                    {av && av.nota_merito !== null && av.nota_merito !== undefined && (
                      <p className="text-sm text-slate-700">
                        Nota de mérito: <strong>{formatNumber(av.nota_merito)}</strong>
                        {av.parecer === 'INDEFERIDO' && <span className="text-red-600 ml-2">(parecer desfavorável)</span>}
                      </p>
                    )}
                    {insc.recurso_status && <p className="text-xs font-medium text-orange-700">{RECURSO_LABEL[insc.recurso_status] || insc.recurso_status}</p>}
                    {insc.status === 'PENDENTE_VALIDACAO_VINCULO' && (
                      <p className="text-xs text-amber-700">Aguardando conferência dos documentos pela Pró-Reitoria.</p>
                    )}
                    {insc.motivos_indeferimento && insc.motivos_indeferimento.length > 0 && (
                      <div className="text-xs text-red-700 bg-red-50 p-2.5 rounded-lg border border-red-100">
                        <p className="font-semibold">Motivo(s):</p>
                        <ul className="list-disc list-inside mt-0.5">
                          {insc.motivos_indeferimento.map((m) => <li key={m}>{m}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-2 md:justify-end md:max-w-xs">
                    <button onClick={() => downloadComprovante(insc.id, insc.protocolo).catch((err) => toast.error(getErrorMessage(err)))} className={btn.secondary}>
                      <Download className="h-4 w-4 mr-1.5" /> Comprovante
                    </button>
                    {podeRetificar && (
                      <button onClick={() => setRetificar(insc)} className={btn.secondary}>
                        <Upload className="h-4 w-4 mr-1.5" /> Substituir documentos
                      </button>
                    )}
                    {podeRecorrer && (
                      <button onClick={() => setRecursoPara(insc)} className={btn.primary}>
                        <CornerUpRight className="h-4 w-4 mr-1.5" /> Interpor recurso
                      </button>
                    )}
                    {podeDesistir && (
                      <button onClick={() => desistir(insc)} className="inline-flex items-center px-4 py-2 border border-red-200 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50">
                        <Ban className="h-4 w-4 mr-1.5" /> Desistir
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {recursoPara && (
        <Modal
          title="Interpor recurso"
          subtitle={`Inscrição ${recursoPara.protocolo}. É permitido um recurso por candidatura.`}
          onClose={() => setRecursoPara(null)}
          footer={
            <>
              <button onClick={() => setRecursoPara(null)} className={btn.secondary}>Cancelar</button>
              <button onClick={enviarRecurso} disabled={enviando} className={btn.primary}>
                {enviando && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />} Enviar recurso
              </button>
            </>
          }
        >
          <label className="block text-xs font-semibold text-slate-700 mb-1">Fundamentação (até 5.000 caracteres)</label>
          <textarea
            rows={6}
            maxLength={5000}
            value={recursoTexto}
            onChange={(e) => setRecursoTexto(e.target.value)}
            placeholder="Explique de forma objetiva os motivos do pedido de revisão."
            className={inputClass}
          />
          <p className="text-xs text-slate-400 text-right mt-1">{recursoTexto.length}/5000</p>
        </Modal>
      )}

      {retificar && (
        <RetificarModal inscricao={retificar} onClose={() => setRetificar(null)} onDone={() => { setRetificar(null); loadData(); }} />
      )}
    </div>
  );
};
