import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, Download, FileText, Loader2 } from 'lucide-react';
import { Edital } from '../types/edital';
import { downloadComprovante, InscriptionDetail, submeterInscricao } from '../api/inscricoes';
import { getErrorMessage } from '../api/client';
import { Modal, btn, inputClass, InscricaoStatusBadge } from './ui';
import { useToast } from './Toast';
import { formatNumber } from '../utils/format';

interface ApplicationModalProps {
  edital: Edital;
  onClose: () => void;
  onSuccess: (inscricao: InscriptionDetail) => void;
}

const MAX_BYTES = 10 * 1024 * 1024;

export const ApplicationModal: React.FC<ApplicationModalProps> = ({ edital, onClose, onSuccess }) => {
  const toast = useToast();
  const cursos = edital.cursos || [];
  const docs = edital.documentos_exigidos || [];
  const [selectedFiles, setSelectedFiles] = useState<{ [docId: number]: File }>({});
  const [cursoCodigo, setCursoCodigo] = useState(cursos.length === 1 ? cursos[0].codigo_curso : '');
  const [cr, setCr] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<InscriptionDetail | null>(null);

  const handleFileChange = (docId: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Envie apenas arquivos em PDF.');
      e.target.value = '';
      return;
    }
    if (file.size > MAX_BYTES) {
      toast.error('O arquivo excede o limite de 10 MB.');
      e.target.value = '';
      return;
    }
    setSelectedFiles((prev) => ({ ...prev, [docId]: file }));
  };

  const handleSubmit = async () => {
    const faltando = docs.filter((d) => d.obrigatorio && !selectedFiles[d.id]);
    if (faltando.length) return setErrorMessage(`Anexe o documento obrigatório: ${faltando[0].nome}.`);
    if (!cursoCodigo) return setErrorMessage('Selecione o seu curso.');
    const crNum = Number(cr.replace(',', '.'));
    if (!cr || Number.isNaN(crNum) || crNum < 0 || crNum > 10) return setErrorMessage('Informe seu CR (coeficiente de rendimento) entre 0 e 10.');

    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await submeterInscricao(edital.id, selectedFiles, { curso_codigo: cursoCodigo, cr_declarado: String(crNum) });
      setSubmitted(res);
      onSuccess(res);
    } catch (err) {
      setErrorMessage(getErrorMessage(err, 'Não foi possível enviar a inscrição.'));
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <Modal title="Inscrição registrada" subtitle={edital.titulo} onClose={onClose}
        footer={
          <>
            <button onClick={() => downloadComprovante(submitted.id, submitted.protocolo).catch((err) => toast.error(getErrorMessage(err)))} className={btn.primary}>
              <Download className="h-4 w-4 mr-1.5" /> Baixar comprovante
            </button>
            <button onClick={onClose} className={btn.secondary}>Fechar</button>
          </>
        }
      >
        <div className="text-center mb-5">
          <div className="mx-auto h-14 w-14 rounded-full flex items-center justify-center mb-3 bg-emerald-100 text-emerald-600">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <p className="text-sm text-slate-600">Guarde o número de protocolo para acompanhar o processo seletivo.</p>
        </div>
        <dl className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2 text-sm">
          <div className="flex justify-between"><dt className="text-slate-500">Protocolo</dt><dd className="font-mono font-bold text-blue-700">{submitted.protocolo}</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">Situação</dt><dd><InscricaoStatusBadge status={submitted.status} /></dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">Curso</dt><dd className="text-slate-800">{submitted.curso_congelado}</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">CR</dt><dd className="text-slate-800">{formatNumber(submitted.cr_congelado)}</dd></div>
        </dl>
        {submitted.status === 'PENDENTE_VALIDACAO_VINCULO' && (
          <p className="mt-4 text-xs text-slate-600 bg-amber-50 border border-amber-200 rounded-lg p-3">
            Sua inscrição será conferida pela Pró-Reitoria com base nos documentos enviados. Você será notificado(a) do resultado da análise.
          </p>
        )}
        {submitted.motivos_indeferimento && submitted.motivos_indeferimento.length > 0 && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
            <p className="font-semibold mb-1">Pendências identificadas:</p>
            <ul className="list-disc list-inside space-y-0.5">
              {submitted.motivos_indeferimento.map((m) => <li key={m}>{m}</li>)}
            </ul>
            <p className="mt-2 text-xs">Enquanto as inscrições estiverem abertas, você pode substituir documentos em "Minhas inscrições".</p>
          </div>
        )}
      </Modal>
    );
  }

  return (
    <Modal
      title="Inscrição"
      subtitle={edital.titulo}
      onClose={onClose}
      size="lg"
      footer={
        <>
          <button onClick={onClose} className={btn.secondary}>Cancelar</button>
          <button onClick={handleSubmit} disabled={loading} className={btn.primary}>
            {loading && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />} Enviar inscrição
          </button>
        </>
      }
    >
      {errorMessage && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center">
          <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" /> {errorMessage}
        </div>
      )}

      <h4 className="text-sm font-semibold text-slate-800 mb-2">Dados acadêmicos</h4>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-2">
        <div className="sm:col-span-2">
          <label className="block text-xs text-slate-600 mb-1">Curso</label>
          <select value={cursoCodigo} onChange={(e) => setCursoCodigo(e.target.value)} className={inputClass}>
            <option value="">Selecione</option>
            {cursos.map((c) => <option key={c.codigo_curso} value={c.codigo_curso}>{c.nome_curso}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">CR acumulado</label>
          <input inputMode="decimal" placeholder="Ex.: 8,25" value={cr} onChange={(e) => setCr(e.target.value)} className={inputClass} />
        </div>
      </div>
      <p className="text-xs text-slate-500 mb-5">
        As informações serão conferidas com o histórico escolar enviado. Declarações inconsistentes levam ao indeferimento.
      </p>

      <h4 className="text-sm font-semibold text-slate-800 mb-2">Documentos (PDF, até 10 MB)</h4>
      <div className="space-y-3">
        {docs.map((doc) => (
          <div key={doc.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-sm font-medium text-slate-800 flex items-center">
                <FileText className="h-4 w-4 mr-1.5 text-blue-600" />
                {doc.nome}
                {doc.obrigatorio ? <span className="text-red-500 ml-1">*</span> : <span className="text-slate-400 ml-1 text-xs">(opcional)</span>}
              </label>
              {selectedFiles[doc.id] && (
                <span className="text-xs text-emerald-600 font-medium flex items-center"><CheckCircle2 className="h-3.5 w-3.5 mr-1" />Anexado</span>
              )}
            </div>
            {doc.descricao && <p className="text-xs text-slate-500 mb-2">{doc.descricao}</p>}
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => handleFileChange(doc.id, e)}
              className="block w-full text-xs text-slate-500 file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border-0 file:text-xs file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>
        ))}
      </div>
    </Modal>
  );
};
