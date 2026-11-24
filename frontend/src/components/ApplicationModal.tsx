import React, { useState } from 'react';
import { X, Upload, CheckCircle2, AlertCircle, FileText, Loader2, ShieldCheck, Download } from 'lucide-react';
import { Edital } from '../types/edital';
import { submeterInscricao, downloadComprovante, InscriptionDetail } from '../api/inscricoes';

interface ApplicationModalProps {
  edital: Edital;
  onClose: () => void;
  onSuccess: (protocolo: string) => void;
}

export const ApplicationModal: React.FC<ApplicationModalProps> = ({ edital, onClose, onSuccess }) => {
  const [selectedFiles, setSelectedFiles] = useState<{ [docId: number]: File }>({});
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittedInscricao, setSubmittedInscricao] = useState<InscriptionDetail | null>(null);

  const docs = edital.documentos_exigidos || [];

  const handleFileChange = (docId: number, e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];

    // Validação cliente (RN-04)
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Arquivo inválido: apenas documentos no formato PDF são aceitos.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('Arquivo excede o tamanho máximo permitido de 10 MB.');
      return;
    }

    setSelectedFiles((prev) => ({ ...prev, [docId]: file }));
  };

  const handleSubmit = async () => {
    // Checa se todos os obrigatórios foram preenchidos
    const docsObrigatorios = docs.filter((d) => d.obrigatorio);
    for (const d of docsObrigatorios) {
      if (!selectedFiles[d.id]) {
        setErrorMessage(`Por favor, anexe o documento obrigatório: ${d.nome}`);
        return;
      }
    }

    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await submeterInscricao(edital.id, selectedFiles);
      setSubmittedInscricao(res);
      onSuccess(res.protocolo);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Erro ao submeter inscrição.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-xl max-w-xl w-full border border-slate-200 overflow-hidden my-8">
        {/* Cabeçalho */}
        <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-slate-50">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Inscrição &mdash; {edital.titulo}</h3>
            <p className="text-xs text-slate-500 mt-0.5">QUERO &middot; Envio de Documentos e Validação Automática</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Corpo do Modal */}
        <div className="p-6">
          {submittedInscricao ? (
            /* Tela de Conclusão / Protocolo */
            <div className="text-center py-6">
              <div className={`mx-auto h-14 w-14 rounded-full flex items-center justify-center mb-4 ${
                submittedInscricao.status === 'HOMOLOGADA' ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'
              }`}>
                <CheckCircle2 className="h-8 w-8" />
              </div>

              <h4 className="text-xl font-bold text-slate-900 mb-1">Candidatura Registrada!</h4>
              <p className="text-xs text-slate-500 mb-6">Guarde o seu protocolo para acompanhamento do processo seletivo.</p>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-6 text-left space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Protocolo Único:</span>
                  <span className="font-mono font-bold text-blue-700 text-sm">{submittedInscricao.protocolo}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Situação Formal:</span>
                  <span className={`font-semibold px-2 py-0.5 rounded ${
                    submittedInscricao.status === 'HOMOLOGADA' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                  }`}>
                    {submittedInscricao.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Curso Congelado:</span>
                  <span className="font-medium text-slate-800">{submittedInscricao.curso_congelado}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">CR Congelado:</span>
                  <span className="font-medium text-slate-800">{Number(submittedInscricao.cr_congelado).toFixed(2)}</span>
                </div>
              </div>

              {submittedInscricao.motivos_indeferimento && submittedInscricao.motivos_indeferimento.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3 mb-6 text-left text-xs text-red-700">
                  <p className="font-semibold mb-1">Pendências apontadas na validação automática:</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {submittedInscricao.motivos_indeferimento.map((m, idx) => (
                      <li key={idx}>{m}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={() => downloadComprovante(submittedInscricao.id, submittedInscricao.protocolo)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold flex items-center justify-center hover:bg-blue-700 transition"
                >
                  <Download className="h-4 w-4 mr-1.5" />
                  Baixar Comprovante (PDF)
                </button>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-200 transition"
                >
                  Fechar
                </button>
              </div>
            </div>
          ) : (
            /* Formulário de Upload dos Documentos */
            <div>
              {errorMessage && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                  {errorMessage}
                </div>
              )}

              <p className="text-xs text-slate-600 mb-4">
                Envie os documentos exigidos em formato PDF (máx. 10 MB por arquivo).
                Seus dados acadêmicos (vínculo, curso e CR) serão validados e congelados automaticamente na submissão (RN-02).
              </p>

              <div className="space-y-4 mb-6">
                {docs.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">Nenhum documento cadastrado neste edital.</p>
                ) : (
                  docs.map((doc) => {
                    const file = selectedFiles[doc.id];
                    return (
                      <div key={doc.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-xs font-semibold text-slate-800 flex items-center">
                            <FileText className="h-4 w-4 mr-1.5 text-blue-600" />
                            {doc.nome}
                            {doc.obrigatorio && <span className="text-red-500 ml-1">*</span>}
                          </label>
                          {file && (
                            <span className="text-[11px] text-emerald-600 font-medium flex items-center">
                              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                              Selecionado
                            </span>
                          )}
                        </div>

                        {doc.descricao && (
                          <p className="text-[11px] text-slate-500 mb-2">{doc.descricao}</p>
                        )}

                        <div className="flex items-center gap-2">
                          <input
                            type="file"
                            accept=".pdf,application/pdf"
                            onChange={(e) => handleFileChange(doc.id, e)}
                            className="block w-full text-xs text-slate-500
                              file:mr-2 file:py-1 file:px-2.5
                              file:rounded-md file:border-0
                              file:text-xs file:font-medium
                              file:bg-blue-50 file:text-blue-700
                              hover:file:bg-blue-100"
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 transition"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={loading}
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition flex items-center disabled:opacity-50"
                >
                  {loading && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}
                  Confirmar e Submeter Inscrição
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
