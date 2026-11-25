import React, { useEffect, useState } from 'react';
import { CheckCircle2, FileText, Gavel, Loader2, Sparkles, Star } from 'lucide-react';
import { fetchEditais } from '../api/editais';
import {
  AvaliacaoInputPayload, fetchAppeals, fetchEvaluationQueue, judgeAppeal, publishPreliminaryResults, Recurso, submitEvaluation,
} from '../api/avaliacoes';
import { downloadArquivo, InscriptionDetail } from '../api/inscricoes';
import { getErrorMessage } from '../api/client';
import { Edital } from '../types/edital';
import { EditalSelect, EmptyState, Modal, PageHeader, Spinner, btn, inputClass } from '../components/ui';
import { useToast } from '../components/Toast';
import { useAuth } from '../context/AuthContext';
import { formatDateTime, formatNumber } from '../utils/format';

const AVALIACAO_LABEL: Record<string, { label: string; style: string }> = {
  RASCUNHO: { label: 'Rascunho', style: 'bg-slate-100 text-slate-600' },
  CONFIRMADA: { label: 'Avaliada', style: 'bg-emerald-50 text-emerald-700' },
  RETIFICADA: { label: 'Retificada', style: 'bg-indigo-50 text-indigo-700' },
};

const FASES = ['ABERTO', 'INSCRICOES_ENCERRADAS', 'EM_AVALIACAO', 'EM_RECURSO', 'EM_HOMOLOGACAO_FINAL'];
const FASES_AVALIACAO = ['INSCRICOES_ENCERRADAS', 'EM_AVALIACAO'];

const avisoFase = (edital: Edital | null, aba: 'fila' | 'recursos'): { tom: 'info' | 'ok'; texto: string } | null => {
  if (!edital) return null;
  if (aba === 'recursos') {
    if (edital.status === 'EM_RECURSO' || edital.status === 'EM_HOMOLOGACAO_FINAL') {
      return { tom: 'ok', texto: 'Fase recursal: julgue os recursos pendentes. O recurso deve ser julgado por membro diferente do autor da avaliação original, quando a comissão tiver dois ou mais membros.' };
    }
    return { tom: 'info', texto: 'Os recursos só podem ser interpostos após a publicação do resultado preliminar.' };
  }
  switch (edital.status) {
    case 'ABERTO':
      return {
        tom: 'info',
        texto: `As inscrições estão abertas até ${formatDateTime(edital.data_fim_inscricao)}. A avaliação é liberada após o encerramento das inscrições (a Pró-Reitoria pode encerrá-las antes do prazo). Somente candidaturas homologadas pela Pró-Reitoria aparecem nesta fila.`,
      };
    case 'INSCRICOES_ENCERRADAS':
    case 'EM_AVALIACAO':
      return { tom: 'ok', texto: 'Avaliação liberada: avalie todas as candidaturas e, ao final, publique o resultado preliminar.' };
    case 'EM_RECURSO':
      return { tom: 'info', texto: 'O resultado preliminar já foi publicado. Acompanhe e julgue os recursos na aba "Recursos".' };
    case 'EM_HOMOLOGACAO_FINAL':
      return { tom: 'info', texto: 'Avaliação concluída. O edital aguarda a homologação final pela Pró-Reitoria.' };
    default:
      return null;
  }
};

export const EvaluationQueuePage: React.FC = () => {
  const toast = useToast();
  const { user, role } = useAuth();
  const [editais, setEditais] = useState<Edital[]>([]);
  const [editalId, setEditalId] = useState<number | null>(null);
  const [aba, setAba] = useState<'fila' | 'recursos'>('fila');
  const [fila, setFila] = useState<InscriptionDetail[]>([]);
  const [recursos, setRecursos] = useState<Recurso[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const [avaliando, setAvaliando] = useState<InscriptionDetail | null>(null);
  const [form, setForm] = useState({ declaracao: false, nota: '', parecer: 'DEFERIDO' as 'DEFERIDO' | 'INDEFERIDO', justificativa: '', retificacao: '' });
  const [salvando, setSalvando] = useState(false);
  const [publicando, setPublicando] = useState(false);

  const [julgando, setJulgando] = useState<Recurso | null>(null);
  const [julg, setJulg] = useState({ decisao: 'INDEFERIDO' as 'DEFERIDO' | 'INDEFERIDO', justificativa: '', novaNota: '' });

  useEffect(() => {
    fetchEditais()
      .then((res) => {
        const lista = res.items.filter(
          (e) => FASES.includes(e.status) && (role === 'PRO_REITOR' || (e.comissao || []).some((m) => m.avaliador_id === user?.id))
        );
        setEditais(lista);
        if (lista.length) setEditalId(lista[0].id);
      })
      .catch((err) => toast.error(getErrorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const edital = editais.find((e) => e.id === editalId) || null;

  const load = async () => {
    if (!editalId) return;
    setLoading(true);
    setErro(null);
    try {
      if (aba === 'fila') setFila(await fetchEvaluationQueue(editalId));
      else setRecursos(await fetchAppeals(editalId));
    } catch (err) {
      setErro(getErrorMessage(err));
      setFila([]);
      setRecursos([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editalId, aba]);

  const abrirAvaliacao = (insc: InscriptionDetail) => {
    const av = insc.avaliacao_resumo;
    setAvaliando(insc);
    setForm({
      declaracao: false,
      nota: av?.nota_merito !== null && av?.nota_merito !== undefined ? String(av.nota_merito) : '',
      parecer: (av?.parecer as 'DEFERIDO' | 'INDEFERIDO') || 'DEFERIDO',
      justificativa: '',
      retificacao: '',
    });
  };

  const salvarAvaliacao = async (confirmar: boolean) => {
    if (!avaliando) return;
    const nota = Number(form.nota.replace(',', '.'));
    if (!form.declaracao) return toast.error('Confirme a declaração de ausência de impedimento.');
    if (form.nota === '' || Number.isNaN(nota) || nota < 0 || nota > 10) return toast.error('Informe uma nota entre 0 e 10.');
    if (form.parecer === 'INDEFERIDO' && form.justificativa.trim().length < 15) return toast.error('Justifique o parecer desfavorável (mínimo de 15 caracteres).');
    const jaConfirmada = avaliando.avaliacao_resumo && avaliando.avaliacao_resumo.status !== 'RASCUNHO';
    if (jaConfirmada && form.retificacao.trim().length < 15) return toast.error('Informe a justificativa da retificação (mínimo de 15 caracteres).');

    const payload: AvaliacaoInputPayload = {
      declaracao_sem_impedimento: true,
      nota_merito: nota,
      parecer: form.parecer,
      justificativa: form.parecer === 'INDEFERIDO' ? form.justificativa.trim() : undefined,
      confirmar,
      justificativa_retificacao: jaConfirmada ? form.retificacao.trim() : undefined,
    };
    setSalvando(true);
    try {
      await submitEvaluation(avaliando.id, payload);
      toast.success(confirmar ? 'Avaliação registrada.' : 'Rascunho salvo.');
      setAvaliando(null);
      load();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSalvando(false);
    }
  };

  const publicar = async () => {
    if (!editalId) return;
    if (!window.confirm('Publicar o resultado preliminar? Os candidatos serão notificados e o prazo de recursos será aberto.')) return;
    setPublicando(true);
    try {
      await publishPreliminaryResults(editalId);
      toast.success('Resultado preliminar publicado.');
      setEditais((prev) => prev.map((e) => (e.id === editalId ? { ...e, status: 'EM_RECURSO' } : e)));
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setPublicando(false);
    }
  };

  const salvarJulgamento = async () => {
    if (!julgando) return;
    if (julg.justificativa.trim().length < 20) return toast.error('A justificativa deve ter pelo menos 20 caracteres.');
    let novaNota: number | undefined;
    if (julg.decisao === 'DEFERIDO' && julg.novaNota !== '') {
      novaNota = Number(julg.novaNota.replace(',', '.'));
      if (Number.isNaN(novaNota) || novaNota < 0 || novaNota > 10) return toast.error('A nova nota deve estar entre 0 e 10.');
    }
    setSalvando(true);
    try {
      await judgeAppeal(julgando.id, julg.decisao, julg.justificativa.trim(), novaNota);
      toast.success('Recurso julgado.');
      setJulgando(null);
      load();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSalvando(false);
    }
  };

  const avaliadas = fila.filter((i) => i.avaliacao_resumo && i.avaliacao_resumo.status !== 'RASCUNHO').length;
  const podePublicar = edital?.status === 'EM_AVALIACAO' && fila.length > 0 && avaliadas === fila.length;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader title="Avaliação" subtitle="Avalie as candidaturas homologadas e julgue os recursos dos editais em que você integra a comissão." />

      <EditalSelect
        editais={editais}
        value={editalId}
        onChange={setEditalId}
        right={
          aba === 'fila' && fila.length > 0 ? (
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">{avaliadas} de {fila.length} avaliada(s)</span>
              {edital?.status === 'EM_AVALIACAO' && (
                <button onClick={publicar} disabled={!podePublicar || publicando} className={btn.primary} title={podePublicar ? '' : 'Todas as candidaturas precisam estar avaliadas'}>
                  {publicando ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Sparkles className="h-4 w-4 mr-1.5" />} Publicar resultado preliminar
                </button>
              )}
            </div>
          ) : undefined
        }
      />

      <div className="flex gap-2 mb-4">
        {(['fila', 'recursos'] as const).map((a) => (
          <button
            key={a}
            onClick={() => setAba(a)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${aba === a ? 'bg-slate-900 text-white' : 'bg-white border border-slate-200 text-slate-700'}`}
          >
            {a === 'fila' ? 'Candidaturas' : 'Recursos'}
          </button>
        ))}
      </div>

      {(() => {
        const aviso = avisoFase(edital, aba);
        return aviso ? (
          <div className={`mb-4 rounded-xl border p-4 text-sm ${aviso.tom === 'ok' ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-blue-50 border-blue-200 text-blue-900'}`}>
            {aviso.texto}
          </div>
        ) : null;
      })()}

      {editais.length === 0 ? (
        <EmptyState icon={<Star className="h-12 w-12" />} title="Nenhum edital para avaliar" description="Você será notificado(a) quando for designado(a) para uma comissão avaliadora." />
      ) : loading ? (
        <Spinner label="Carregando..." />
      ) : erro ? (
        <EmptyState icon={<Star className="h-12 w-12" />} title="Não foi possível carregar" description={erro} />
      ) : aba === 'fila' ? (
        fila.length === 0 ? (
          <EmptyState icon={<CheckCircle2 className="h-12 w-12" />} title="Nenhuma candidatura na fila" description="As candidaturas aparecem aqui depois de conferidas e homologadas pela Pró-Reitoria (página Inscrições)." />
        ) : (
          <div className="space-y-3">
            {fila.map((insc) => {
              const av = insc.avaliacao_resumo;
              const badge = av ? AVALIACAO_LABEL[av.status] : { label: 'Pendente', style: 'bg-amber-50 text-amber-700' };
              return (
                <div key={insc.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">{insc.protocolo}</span>
                      <span className={`text-xs px-2 py-0.5 rounded font-semibold ${badge.style}`}>{badge.label}</span>
                      {av?.nota_merito !== undefined && av?.nota_merito !== null && <span className="text-xs text-slate-600">Nota {formatNumber(av.nota_merito)}</span>}
                    </div>
                    <h3 className="text-base font-bold text-slate-900">{insc.nome_estudante}</h3>
                    <p className="text-xs text-slate-500">{insc.curso_congelado} · CR {formatNumber(insc.cr_congelado)}</p>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {insc.arquivos.filter((a) => a.ativo).map((a) => (
                        <button key={a.id} onClick={() => downloadArquivo(a).catch((err) => toast.error(getErrorMessage(err)))} className="inline-flex items-center text-xs px-2.5 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700">
                          <FileText className="h-3.5 w-3.5 mr-1" /> {a.nome_original}
                        </button>
                      ))}
                    </div>
                  </div>
                  {(() => {
                    const liberado = FASES_AVALIACAO.includes(edital?.status || '');
                    const motivo = edital?.status === 'ABERTO'
                      ? 'Disponível após o encerramento das inscrições'
                      : 'Fase de avaliação encerrada';
                    return (
                      <div className="flex flex-col items-start md:items-end gap-1">
                        <button onClick={() => abrirAvaliacao(insc)} disabled={!liberado} title={liberado ? '' : motivo} className={btn.primary}>
                          <Star className="h-4 w-4 mr-1.5" /> {av && av.status !== 'RASCUNHO' ? 'Retificar avaliação' : 'Avaliar'}
                        </button>
                        {!liberado && <span className="text-[11px] text-slate-500">{motivo}</span>}
                      </div>
                    );
                  })()}
                </div>
              );
            })}
          </div>
        )
      ) : recursos.length === 0 ? (
        <EmptyState icon={<Gavel className="h-12 w-12" />} title="Nenhum recurso interposto" />
      ) : (
        <div className="space-y-3">
          {recursos.map((r) => {
            const autor = r.avaliador_original_id === user?.id;
            const pendente = r.status === 'ABERTO' || r.status === 'EM_ANALISE';
            return (
              <div key={r.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">{r.protocolo}</span>
                      <span className={`text-xs px-2 py-0.5 rounded font-semibold ${pendente ? 'bg-orange-50 text-orange-700' : r.status === 'DEFERIDO' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                        {pendente ? 'Aguardando julgamento' : r.status === 'DEFERIDO' ? 'Deferido' : 'Indeferido'}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-slate-900">{r.nome_estudante}</h3>
                    <p className="text-xs text-slate-500">Interposto em {formatDateTime(r.criado_em)} · Nota original {formatNumber(r.nota_original)}</p>
                    <p className="text-sm text-slate-700 whitespace-pre-line bg-slate-50 border border-slate-100 rounded-lg p-3 mt-2">{r.texto}</p>
                    {r.justificativa_decisao && <p className="text-xs text-slate-600 mt-2"><strong>Decisão:</strong> {r.justificativa_decisao}</p>}
                  </div>
                  {pendente && (
                    <button
                      onClick={() => { setJulgando(r); setJulg({ decisao: 'INDEFERIDO', justificativa: '', novaNota: '' }); }}
                      disabled={autor}
                      title={autor ? 'O recurso deve ser julgado por outro membro da comissão.' : ''}
                      className={btn.primary}
                    >
                      <Gavel className="h-4 w-4 mr-1.5" /> Julgar
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {avaliando && (
        <Modal
          title="Avaliação de mérito"
          subtitle={`${avaliando.nome_estudante} · ${avaliando.curso_congelado} · CR ${formatNumber(avaliando.cr_congelado)}`}
          onClose={() => setAvaliando(null)}
          footer={
            <>
              <button onClick={() => setAvaliando(null)} className={btn.secondary}>Cancelar</button>
              {(!avaliando.avaliacao_resumo || avaliando.avaliacao_resumo.status === 'RASCUNHO') && (
                <button onClick={() => salvarAvaliacao(false)} disabled={salvando} className={btn.secondary}>Salvar rascunho</button>
              )}
              <button onClick={() => salvarAvaliacao(true)} disabled={salvando} className={btn.primary}>
                {salvando && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />} Confirmar avaliação
              </button>
            </>
          }
        >
          <label className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg mb-4 cursor-pointer">
            <input type="checkbox" checked={form.declaracao} onChange={(e) => setForm({ ...form, declaracao: e.target.checked })} className="mt-0.5 h-4 w-4" />
            <span className="text-xs text-amber-900">
              Declaro não possuir impedimento ou suspeição em relação a este candidato (parentesco, orientação direta ou conflito de interesses).
            </span>
          </label>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Nota (0 a 10)</label>
              <input inputMode="decimal" value={form.nota} onChange={(e) => setForm({ ...form, nota: e.target.value })} className={inputClass} />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Parecer</label>
              <select value={form.parecer} onChange={(e) => setForm({ ...form, parecer: e.target.value as 'DEFERIDO' | 'INDEFERIDO' })} className={inputClass}>
                <option value="DEFERIDO">Favorável</option>
                <option value="INDEFERIDO">Desfavorável</option>
              </select>
            </div>
          </div>
          {form.parecer === 'INDEFERIDO' && (
            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-700 mb-1">Justificativa do parecer desfavorável</label>
              <textarea rows={3} value={form.justificativa} onChange={(e) => setForm({ ...form, justificativa: e.target.value })} className={inputClass} />
            </div>
          )}
          {avaliando.avaliacao_resumo && avaliando.avaliacao_resumo.status !== 'RASCUNHO' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Justificativa da retificação</label>
              <textarea rows={2} value={form.retificacao} onChange={(e) => setForm({ ...form, retificacao: e.target.value })} className={inputClass} />
            </div>
          )}
        </Modal>
      )}

      {julgando && (
        <Modal
          title="Julgamento de recurso"
          subtitle={`${julgando.nome_estudante} · ${julgando.protocolo}`}
          onClose={() => setJulgando(null)}
          footer={
            <>
              <button onClick={() => setJulgando(null)} className={btn.secondary}>Cancelar</button>
              <button onClick={salvarJulgamento} disabled={salvando} className={btn.primary}>
                {salvando && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />} Registrar decisão
              </button>
            </>
          }
        >
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Decisão</label>
              <select value={julg.decisao} onChange={(e) => setJulg({ ...julg, decisao: e.target.value as 'DEFERIDO' | 'INDEFERIDO' })} className={inputClass}>
                <option value="INDEFERIDO">Indeferir</option>
                <option value="DEFERIDO">Deferir</option>
              </select>
            </div>
            {julg.decisao === 'DEFERIDO' && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Nova nota (opcional)</label>
                <input inputMode="decimal" value={julg.novaNota} onChange={(e) => setJulg({ ...julg, novaNota: e.target.value })} className={inputClass} />
              </div>
            )}
          </div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Fundamentação (mínimo de 20 caracteres)</label>
          <textarea rows={4} value={julg.justificativa} onChange={(e) => setJulg({ ...julg, justificativa: e.target.value })} className={inputClass} />
        </Modal>
      )}
    </div>
  );
};
