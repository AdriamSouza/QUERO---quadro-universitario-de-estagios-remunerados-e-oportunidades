import React, { useState, useEffect } from 'react';
import { ShieldCheck, Eye, RefreshCw } from 'lucide-react';
import { fetchAuditLogs, AuditLog } from '../api/homologacao';
import { getErrorMessage } from '../api/client';
import { Modal, btn } from '../components/ui';
import { useToast } from '../components/Toast';

export const AuditLogsPage: React.FC = () => {
  const toast = useToast();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [entidade, setEntidade] = useState('');
  const [selectedPayload, setSelectedPayload] = useState<{ antes: unknown; depois: unknown } | null>(null);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const res = await fetchAuditLogs(entidade || undefined);
      setLogs(res.items);
      setTotal(res.total);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Não foi possível carregar os registros de auditoria.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entidade]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Auditoria</h2>
          <p className="mt-1 text-slate-600 text-sm">
            Registro permanente das operações realizadas no sistema: quem fez, o quê, quando e de onde.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={entidade}
            onChange={(e) => setEntidade(e.target.value)}
            className="py-2 px-3 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-blue-500 text-slate-800"
          >
            <option value="">Todas as entidades</option>
            <option value="editais">Editais</option>
            <option value="inscricoes">Inscrições</option>
            <option value="avaliacoes">Avaliações</option>
            <option value="recursos">Recursos</option>
            <option value="usuarios">Usuários</option>
          </select>

          <button
            onClick={loadLogs}
            className="p-2 border border-slate-300 hover:bg-slate-100 rounded-lg text-slate-600 transition"
            title="Atualizar"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center text-xs">
          <span className="font-semibold text-slate-700">Eventos registrados</span>
          <span className="text-slate-500">Total: <strong>{total}</strong></span>
        </div>

        {loading ? (
          <div className="text-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-3 text-slate-500 text-xs">Carregando registros...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-16">
            <ShieldCheck className="h-10 w-10 text-slate-400 mx-auto mb-2" />
            <p className="text-sm text-slate-500">Nenhum evento registrado com os filtros aplicados.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-100 uppercase font-semibold">
                <tr>
                  <th className="py-2.5 px-4">Data/Hora</th>
                  <th className="py-2.5 px-4">Usuário</th>
                  <th className="py-2.5 px-4">Ação</th>
                  <th className="py-2.5 px-4">Registro</th>
                  <th className="py-2.5 px-4">IP</th>
                  <th className="py-2.5 px-4 text-right">Dados</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-4 font-mono text-slate-500">
                      {new Date(log.criado_em).toLocaleString('pt-BR')}
                    </td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">
                      {log.usuario_id ? `Usuário #${log.usuario_id}` : 'Sistema (automático)'}
                    </td>
                    <td className="py-2.5 px-4">
                      <span className="bg-blue-50 text-blue-700 font-bold px-2 py-0.5 rounded text-[11px] border border-blue-100">
                        {log.acao.replace(/_/g, ' ').toLowerCase()}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-slate-700">
                      {log.entidade} (ID #{log.entidade_id})
                    </td>
                    <td className="py-2.5 px-4 font-mono text-slate-500">
                      {log.ip_origem || '-'}
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      {(log.dados_antes || log.dados_depois) && (
                        <button
                          onClick={() => setSelectedPayload({ antes: log.dados_antes, depois: log.dados_depois })}
                          className="text-blue-600 hover:text-blue-800 font-medium inline-flex items-center text-xs"
                        >
                          <Eye className="h-3.5 w-3.5 mr-1" />
                          Detalhes
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Visualização de Payload / Diff */}
      {selectedPayload && (
        <Modal
          title="Detalhes do evento"
          size="lg"
          onClose={() => setSelectedPayload(null)}
          footer={<button onClick={() => setSelectedPayload(null)} className={btn.secondary}>Fechar</button>}
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="font-sans font-bold text-slate-700 block mb-1">Antes:</span>
              <pre className="text-[11px] whitespace-pre-wrap text-slate-600 max-h-60 overflow-y-auto">
                {selectedPayload.antes ? JSON.stringify(selectedPayload.antes, null, 2) : '—'}
              </pre>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="font-sans font-bold text-slate-700 block mb-1">Depois:</span>
              <pre className="text-[11px] whitespace-pre-wrap text-slate-600 max-h-60 overflow-y-auto">
                {selectedPayload.depois ? JSON.stringify(selectedPayload.depois, null, 2) : '—'}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
