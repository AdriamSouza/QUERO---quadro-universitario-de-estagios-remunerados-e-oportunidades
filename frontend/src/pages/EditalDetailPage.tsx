import React, { useEffect, useState } from 'react';
import {
  ArrowLeft, Award, Ban, Calendar, CheckCircle2, Clock, Download, FileText, LogIn, Send, Settings, Trash2,
  UserPlus, Users, Wallet,
} from 'lucide-react';
import { Edital } from '../types/edital';
import {
  assignCommittee, cancelEdital, closeRegistrations, fetchEditalById, publishEdital, removeCommitteeMember,
} from '../api/editais';
import { fetchMyApplications, InscriptionDetail } from '../api/inscricoes';
import { downloadAtaPdf } from '../api/homologacao';
import { fetchUsuarios, Usuario } from '../api/usuarios';
import { getErrorMessage } from '../api/client';
import { ApplicationModal } from '../components/ApplicationModal';
import { EditalStatusBadge, Modal, Spinner, btn, inputClass } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import { CATEGORIA_LABEL, formatDateTime, formatMoney, formatNumber, INSCRICAO_STATUS_LABEL } from '../utils/format';

interface EditalDetailPageProps {
  editalId: number;
  onBack: () => void;
  onNavigate: (page: 'login' | 'my-applications' | 'results') => void;
}

const FASES_RESULTADO = ['EM_RECURSO', 'EM_HOMOLOGACAO_FINAL', 'ENCERRADO'];

const ManagementPanel: React.FC<{ edital: Edital; onChange: (e: Edital) => void }> = ({ edital, onChange }) => {
  const toast = useToast();
  const [avaliadores, setAvaliadores] = useState<Usuario[]>([]);
  const [novoAvaliador, setNovoAvaliador] = useState<number | ''>('');
  const [busy, setBusy] = useState(false);
  const [showCancel, setShowCancel] = useState(false);
  const [justificativa, setJustificativa] = useState('');

  useEffect(() => {
    fetchUsuarios({ perfil: 'AVALIADOR' }).then((r) => setAvaliadores(r.items.filter((u) => u.ativo))).catch(() => undefined);
  }, []);

  const run = async (fn: () => Promise<Edital>, msg: string) => {
    setBusy(true);
    try {
      onChange(await fn());
      toast.success(msg);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const atualizarComissao = async (fn: () => Promise<unknown>, msg: string) => {
    setBusy(true);
    try {
      await fn();
      onChange(await fetchEditalById(edital.id));
      toast.success(msg);
      setNovoAvaliador('');
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const finalizado = ['ENCERRADO', 'CANCELADO'].includes(edital.status);
  const comissaoEditavel = ['RASCUNHO', 'ABERTO', 'INSCRICOES_ENCERRADAS'].includes(edital.status);
  const membros = edital.comissao || [];
  const disponiveis = avaliadores.filter((a) => !membros.some((m) => m.avaliador_id === a.id));

  return (
    <section className="bg-white rounded-xl border border-emerald-200 p-6 shadow-sm mb-6">
      <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center">
        <Settings className="h-5 w-5 text-emerald-600 mr-2" /> Gestão do edital
      </h3>

      <div className="flex flex-wrap gap-2 mb-6">
        {edital.status === 'RASCUNHO' && (
          <button disabled={busy} onClick={() => run(() => publishEdital(edital.id), 'Edital publicado.')} className={btn.success}>
            Publicar edital
          </button>
        )}
        {edital.status === 'ABERTO' && (
          <button
            disabled={busy}
            onClick={() => window.confirm('Encerrar as inscrições agora? Novas inscrições e retificações serão bloqueadas.') && run(() => closeRegistrations(edital.id), 'Inscrições encerradas.')}
            className={btn.secondary}
          >
            Encerrar inscrições
          </button>
        )}
        {!finalizado && (
          <button disabled={busy} onClick={() => setShowCancel(true)} className="inline-flex items-center px-4 py-2 border border-red-200 text-red-700 rounded-lg text-sm font-medium hover:bg-red-50">
            <Ban className="h-4 w-4 mr-1.5" /> Cancelar edital
          </button>
        )}
      </div>

      <h4 className="text-sm font-semibold text-slate-800 mb-2 flex items-center"><Users className="h-4 w-4 mr-1.5" /> Comissão avaliadora</h4>
      {membros.length === 0 ? (
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3 mb-3">
          Nenhum avaliador designado. A comissão precisa ser definida antes da avaliação.
        </p>
      ) : (
        <ul className="divide-y divide-slate-100 border border-slate-200 rounded-lg mb-3">
          {membros.map((m) => (
            <li key={m.avaliador_id} className="flex items-center justify-between px-3 py-2 text-sm">
              <span>
                <span className="font-medium text-slate-800">{m.avaliador_nome || `Usuário #${m.avaliador_id}`}</span>
                {m.avaliador_email && <span className="text-slate-500 ml-2 text-xs">{m.avaliador_email}</span>}
              </span>
              {comissaoEditavel && (
                <button
                  disabled={busy}
                  onClick={() => atualizarComissao(() => removeCommitteeMember(edital.id, m.avaliador_id), 'Avaliador removido.')}
                  className="text-red-600 hover:text-red-800 p-1"
                  aria-label="Remover"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {!finalizado && (
        <div className="flex flex-col sm:flex-row gap-2">
          <select value={novoAvaliador} onChange={(e) => setNovoAvaliador(e.target.value ? Number(e.target.value) : '')} className={`${inputClass} sm:max-w-sm`}>
            <option value="">{disponiveis.length ? 'Selecione um avaliador' : 'Nenhum avaliador disponível'}</option>
            {disponiveis.map((a) => (
              <option key={a.id} value={a.id}>{a.nome} ({a.email})</option>
            ))}
          </select>
          <button
            disabled={busy || !novoAvaliador}
            onClick={() => atualizarComissao(() => assignCommittee(edital.id, [Number(novoAvaliador)]), 'Avaliador designado.')}
            className={btn.primary}
          >
            <UserPlus className="h-4 w-4 mr-1.5" /> Designar
          </button>
        </div>
      )}

      {showCancel && (
        <Modal
          title="Cancelar edital"
          subtitle="Os inscritos serão notificados. Esta ação não pode ser desfeita."
          onClose={() => setShowCancel(false)}
          footer={
            <>
              <button onClick={() => setShowCancel(false)} className={btn.secondary}>Voltar</button>
              <button
                disabled={busy || justificativa.trim().length < 10}
                onClick={async () => {
                  await run(() => cancelEdital(edital.id, justificativa.trim()), 'Edital cancelado.');
                  setShowCancel(false);
                }}
                className={btn.danger}
              >
                Confirmar cancelamento
              </button>
            </>
          }
        >
          <label className="block text-xs font-semibold text-slate-700 mb-1">Justificativa</label>
          <textarea rows={4} value={justificativa} onChange={(e) => setJustificativa(e.target.value)} className={inputClass} />
        </Modal>
      )}
    </section>
  );
};

export const EditalDetailPage: React.FC<EditalDetailPageProps> = ({ editalId, onBack, onNavigate }) => {
  const { user, role } = useAuth();
  const toast = useToast();
  const [edital, setEdital] = useState<Edital | null>(null);
  const [loading, setLoading] = useState(true);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [minhaInscricao, setMinhaInscricao] = useState<InscriptionDetail | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchEditalById(editalId)
      .then(setEdital)
      .catch(() => setEdital(null))
      .finally(() => setLoading(false));
  }, [editalId]);

  useEffect(() => {
    if (role !== 'ESTUDANTE') return;
    fetchMyApplications()
      .then((list) => setMinhaInscricao(list.find((i) => i.edital_id === editalId) || null))
      .catch(() => undefined);
  }, [role, editalId]);

  if (loading) return <Spinner label="Carregando edital..." />;

  if (!edital) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <p className="text-slate-700">Edital não encontrado.</p>
        <button onClick={onBack} className="mt-4 text-blue-600 font-semibold text-sm">Voltar aos editais</button>
      </div>
    );
  }

  const agora = new Date();
  const inscricoesAbertas =
    edital.status === 'ABERTO' && agora >= new Date(edital.data_inicio_inscricao) && agora <= new Date(edital.data_fim_inscricao);

  const renderCta = () => {
    if (minhaInscricao) {
      return (
        <button onClick={() => onNavigate('my-applications')} className={btn.secondary}>
          Você já está inscrito(a) · {INSCRICAO_STATUS_LABEL[minhaInscricao.status]} — ver inscrição
        </button>
      );
    }
    if (!inscricoesAbertas) return null;
    if (!user) {
      return (
        <button onClick={() => onNavigate('login')} className={btn.primary}>
          <LogIn className="h-4 w-4 mr-2" /> Entre para se inscrever
        </button>
      );
    }
    if (role === 'ESTUDANTE') {
      return (
        <button onClick={() => setShowApplyModal(true)} className={btn.primary}>
          <Send className="h-4 w-4 mr-2" /> Inscrever-se
        </button>
      );
    }
    return null;
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <button onClick={onBack} className="flex items-center text-sm font-medium text-slate-600 hover:text-slate-900 mb-6">
        <ArrowLeft className="h-4 w-4 mr-1.5" /> Voltar aos editais
      </button>

      <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm mb-6">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-100">
              {CATEGORIA_LABEL[edital.categoria] || edital.categoria} · {edital.modalidade}
            </span>
            <EditalStatusBadge status={edital.status} />
          </div>
          <span className="text-sm font-mono text-slate-500">Edital nº {edital.id}</span>
        </div>

        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight mb-4">{edital.titulo}</h1>
        <p className="text-slate-700 text-sm leading-relaxed mb-8 whitespace-pre-line">{edital.descricao}</p>

        {edital.status === 'CANCELADO' && edital.justificativa_cancelamento && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
            <strong>Edital cancelado.</strong> {edital.justificativa_cancelamento}
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
          {[
            { icon: <Wallet className="h-3.5 w-3.5 mr-1" />, label: 'Bolsa mensal', value: formatMoney(edital.valor_bolsa) },
            { icon: <Users className="h-3.5 w-3.5 mr-1" />, label: 'Vagas', value: String(edital.vagas) },
            { icon: <Clock className="h-3.5 w-3.5 mr-1" />, label: 'Carga horária', value: `${edital.carga_horaria_semanal}h/semana` },
            { icon: <Award className="h-3.5 w-3.5 mr-1" />, label: 'CR mínimo', value: formatNumber(edital.cr_minimo) },
          ].map((item) => (
            <div key={item.label}>
              <span className="text-xs text-slate-500 flex items-center">{item.icon}{item.label}</span>
              <p className="text-base font-bold text-slate-900 mt-0.5">{item.value}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-t border-slate-100 pt-6">
          <div className="text-sm">
            {inscricoesAbertas ? (
              <span className="text-emerald-700 font-medium flex items-center">
                <CheckCircle2 className="h-4 w-4 mr-1" /> Inscrições abertas até {formatDateTime(edital.data_fim_inscricao)}
              </span>
            ) : (
              <span className="text-slate-600">Inscrições de {formatDateTime(edital.data_inicio_inscricao)} a {formatDateTime(edital.data_fim_inscricao)}</span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {FASES_RESULTADO.includes(edital.status) && (
              <button onClick={() => onNavigate('results')} className={btn.secondary}>Ver classificação</button>
            )}
            {edital.status === 'ENCERRADO' && (
              <button
                onClick={() => downloadAtaPdf(edital.id).catch((err) => toast.error(getErrorMessage(err)))}
                className={btn.secondary}
              >
                <Download className="h-4 w-4 mr-1.5" /> Ata de homologação
              </button>
            )}
            {renderCta()}
          </div>
        </div>
      </div>

      {role === 'PRO_REITOR' && <ManagementPanel edital={edital} onChange={setEdital} />}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 mr-2" /> Cursos elegíveis
          </h3>
          <ul className="divide-y divide-slate-100 text-sm">
            {(edital.cursos || []).map((c) => (
              <li key={c.codigo_curso} className="py-2.5 flex items-center justify-between">
                <span className="text-slate-800 font-medium">{c.nome_curso}</span>
                <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{c.codigo_curso}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center">
            <Calendar className="h-5 w-5 text-blue-600 mr-2" /> Cronograma
          </h3>
          <dl className="space-y-3 text-sm">
            {[
              ['Inscrições', `${formatDateTime(edital.data_inicio_inscricao)} a ${formatDateTime(edital.data_fim_inscricao)}`],
              ['Início da avaliação', formatDateTime(edital.data_inicio_avaliacao)],
              ['Resultado preliminar', formatDateTime(edital.data_resultado_preliminar)],
              ['Prazo para recursos', `${edital.prazo_recurso_horas} horas após o resultado preliminar`],
              ['Resultado final', formatDateTime(edital.data_homologacao_final)],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4 pb-2 border-b border-slate-100 last:border-0">
                <dt className="text-slate-600">{label}</dt>
                <dd className="font-medium text-slate-900 text-right">{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>

      <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center">
          <FileText className="h-5 w-5 text-blue-600 mr-2" /> Documentos exigidos (PDF, até 10 MB cada)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {(edital.documentos_exigidos || []).map((doc) => (
            <div key={doc.id} className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-slate-900 text-sm">{doc.nome}</span>
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${doc.obrigatorio ? 'bg-red-50 text-red-700 border-red-200' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                  {doc.obrigatorio ? 'Obrigatório' : 'Opcional'}
                </span>
              </div>
              {doc.descricao && <p className="text-xs text-slate-600 mt-1">{doc.descricao}</p>}
            </div>
          ))}
        </div>
      </section>

      {showApplyModal && (
        <ApplicationModal
          edital={edital}
          onClose={() => setShowApplyModal(false)}
          onSuccess={(insc) => setMinhaInscricao(insc)}
        />
      )}
    </div>
  );
};
