import React, { useState, useEffect } from 'react';
import { Trophy, Award, AlertCircle, FileText, CornerUpRight, Loader2, Sparkles, CheckCircle2 } from 'lucide-react';
import { fetchEditais } from '../api/editais';
import { publishPreliminaryResults, ResultadoPreliminarResponse, ClassificacaoItem } from '../api/avaliacoes';
import { apiClient } from '../api/client';
import { Edital } from '../types/edital';

export const PreliminaryResultsPage: React.FC = () => {
  const [editais, setEditais] = useState<Edital[]>([]);
  const [selectedEditalId, setSelectedEditalId] = useState<number | null>(null);
  const [resultado, setResultado] = useState<ResultadoPreliminarResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    const load = async () => {
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
    load();
  }, []);

  const handlePublishResults = async () => {
    if (!selectedEditalId) return;
    setPublishing(true);
    try {
      const res = await publishPreliminaryResults(selectedEditalId);
      setResultado(res);
      alert('Resultado preliminar calculado e publicado com sucesso! Janela de recursos aberta (AVA-02, RN-10).');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao publicar resultado preliminar.');
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Classificação e Resultado Preliminar</h2>
        <p className="mt-2 text-slate-600 text-sm">
          Cálculo automático de classificação conforme RN-09 (nota decrescente, desempate por CR e protocolo) e distribuição de vagas (RN-12).
        </p>
      </div>

      {/* Barra Superior */}
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
                Edital #{e.id} &mdash; {e.titulo} ({e.status})
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handlePublishResults}
          disabled={publishing || !selectedEditalId}
          className="w-full sm:w-auto px-5 py-2.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition flex items-center justify-center shadow-sm disabled:opacity-50"
        >
          {publishing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
          Calcular e Publicar Resultado Preliminar
        </button>
      </div>

      {/* Resultados */}
      {resultado ? (
        <div className="space-y-6">
          {/* Quadro de Contemplados */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 bg-emerald-50 border-b border-emerald-100 flex items-center justify-between">
              <h3 className="text-sm font-bold text-emerald-900 flex items-center">
                <Trophy className="h-4 w-4 text-emerald-600 mr-2" />
                Quadro I &mdash; Candidatos Contemplados ({resultado.contemplados.length} de {resultado.vagas_totais} vagas)
              </h3>
              <span className="text-xs font-semibold text-emerald-700 bg-white px-2 py-0.5 rounded border border-emerald-200">
                Titulares
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 border-b border-slate-100 uppercase font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Pos.</th>
                    <th className="py-2.5 px-4">Protocolo</th>
                    <th className="py-2.5 px-4">Nome do Candidato</th>
                    <th className="py-2.5 px-4">Curso</th>
                    <th className="py-2.5 px-4">CR</th>
                    <th className="py-2.5 px-4">Nota de Mérito</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {resultado.contemplados.map((item) => (
                    <tr key={item.inscricao_id} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-4 font-bold text-emerald-700">#{item.posicao}</td>
                      <td className="py-2.5 px-4 font-mono font-semibold text-slate-800">{item.protocolo}</td>
                      <td className="py-2.5 px-4 font-medium text-slate-900">{item.nome_estudante}</td>
                      <td className="py-2.5 px-4 text-slate-600">{item.curso}</td>
                      <td className="py-2.5 px-4 text-slate-600">{Number(item.cr).toFixed(2)}</td>
                      <td className="py-2.5 px-4 font-bold text-slate-900">{Number(item.nota_merito).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Quadro de Suplentes */}
          {resultado.suplentes.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-4 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 flex items-center">
                  <Award className="h-4 w-4 text-slate-500 mr-2" />
                  Quadro II &mdash; Banco de Suplentes ({resultado.suplentes.length})
                </h3>
                <span className="text-xs font-semibold text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                  Cadastro Reserva
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 border-b border-slate-100 uppercase font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Pos.</th>
                      <th className="py-2.5 px-4">Protocolo</th>
                      <th className="py-2.5 px-4">Nome do Candidato</th>
                      <th className="py-2.5 px-4">Curso</th>
                      <th className="py-2.5 px-4">CR</th>
                      <th className="py-2.5 px-4">Nota de Mérito</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {resultado.suplentes.map((item) => (
                      <tr key={item.inscricao_id} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-4 font-bold text-slate-600">#{item.posicao}</td>
                        <td className="py-2.5 px-4 font-mono text-slate-700">{item.protocolo}</td>
                        <td className="py-2.5 px-4 font-medium text-slate-900">{item.nome_estudante}</td>
                        <td className="py-2.5 px-4 text-slate-600">{item.curso}</td>
                        <td className="py-2.5 px-4 text-slate-600">{Number(item.cr).toFixed(2)}</td>
                        <td className="py-2.5 px-4 font-bold text-slate-900">{Number(item.nota_merito).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <Award className="h-12 w-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-slate-900">Resultado preliminar ainda não publicado</h3>
          <p className="text-sm text-slate-500 mt-1">
            Selecione o edital e clique em &quot;Calcular e Publicar Resultado Preliminar&quot; para consolidar as avaliações da banca.
          </p>
        </div>
      )}
    </div>
  );
};
