import React, { useEffect, useState } from 'react';
import { Award, Download, Trophy } from 'lucide-react';
import { fetchEditais } from '../api/editais';
import { ClassificacaoItem, fetchResults, ResultadoPreliminarResponse } from '../api/avaliacoes';
import { downloadAtaPdf } from '../api/homologacao';
import { getErrorMessage } from '../api/client';
import { Edital } from '../types/edital';
import { EditalSelect, EmptyState, PageHeader, Spinner, btn } from '../components/ui';
import { useToast } from '../components/Toast';
import { formatDateTime, formatNumber } from '../utils/format';

const FASES_RESULTADO = ['EM_RECURSO', 'EM_HOMOLOGACAO_FINAL', 'ENCERRADO'];

const Tabela: React.FC<{ titulo: string; icon: React.ReactNode; itens: ClassificacaoItem[]; destaque?: boolean; mostrarMatricula: boolean }> = ({
  titulo, icon, itens, destaque, mostrarMatricula,
}) => (
  <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
    <div className={`p-4 border-b flex items-center ${destaque ? 'bg-emerald-50 border-emerald-100' : 'bg-slate-50 border-slate-100'}`}>
      {icon}
      <h3 className={`text-sm font-bold ${destaque ? 'text-emerald-900' : 'text-slate-800'}`}>{titulo}</h3>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-slate-600 border-b border-slate-100 text-xs uppercase">
          <tr>
            <th className="py-2.5 px-4">Posição</th>
            <th className="py-2.5 px-4">Protocolo</th>
            <th className="py-2.5 px-4">Candidato(a)</th>
            {mostrarMatricula && <th className="py-2.5 px-4">Matrícula</th>}
            <th className="py-2.5 px-4">Curso</th>
            <th className="py-2.5 px-4">CR</th>
            <th className="py-2.5 px-4">Nota</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {itens.map((item) => (
            <tr key={item.inscricao_id}>
              <td className={`py-2.5 px-4 font-bold ${destaque ? 'text-emerald-700' : 'text-slate-600'}`}>{item.posicao || '-'}º</td>
              <td className="py-2.5 px-4 font-mono text-xs text-slate-700">{item.protocolo}</td>
              <td className="py-2.5 px-4 font-medium text-slate-900">{item.nome_estudante}</td>
              {mostrarMatricula && <td className="py-2.5 px-4 text-slate-600">{item.matricula || '-'}</td>}
              <td className="py-2.5 px-4 text-slate-600">{item.curso}</td>
              <td className="py-2.5 px-4 text-slate-600">{formatNumber(item.cr)}</td>
              <td className="py-2.5 px-4 font-bold text-slate-900">{formatNumber(item.nota_merito)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

export const PreliminaryResultsPage: React.FC = () => {
  const toast = useToast();
  const [editais, setEditais] = useState<Edital[]>([]);
  const [editalId, setEditalId] = useState<number | null>(null);
  const [resultado, setResultado] = useState<ResultadoPreliminarResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchEditais()
      .then((res) => {
        const lista = res.items.filter((e) => FASES_RESULTADO.includes(e.status));
        setEditais(lista);
        if (lista.length) setEditalId(lista[0].id);
      })
      .catch((err) => toast.error(getErrorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!editalId) return;
    setLoading(true);
    fetchResults(editalId)
      .then(setResultado)
      .catch((err) => {
        setResultado(null);
        toast.error(getErrorMessage(err));
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editalId]);

  const final = resultado?.status_edital === 'ENCERRADO';
  const mostrarMatricula = !!resultado?.contemplados.some((i) => i.matricula);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="Resultados"
        subtitle="Classificação por nota de mérito. Em caso de empate, aplicam-se os critérios de desempate definidos no edital."
      />

      {editais.length === 0 ? (
        <EmptyState icon={<Award className="h-12 w-12" />} title="Nenhum resultado publicado" description="Os resultados aparecem aqui após a publicação pela comissão avaliadora." />
      ) : (
        <>
          <EditalSelect
            editais={editais}
            value={editalId}
            onChange={setEditalId}
            right={
              final ? (
                <button onClick={() => editalId && downloadAtaPdf(editalId).catch((err) => toast.error(getErrorMessage(err)))} className={btn.secondary}>
                  <Download className="h-4 w-4 mr-1.5" /> Ata de homologação
                </button>
              ) : undefined
            }
          />

          {loading ? (
            <Spinner label="Carregando resultado..." />
          ) : resultado ? (
            <div className="space-y-6">
              <div className={`rounded-xl border p-4 text-sm ${final ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-amber-50 border-amber-200 text-amber-900'}`}>
                {final ? (
                  <strong>Resultado final homologado.</strong>
                ) : (
                  <>
                    <strong>Resultado preliminar</strong>, publicado em {formatDateTime(resultado.publicado_em)}.
                    {resultado.prazo_recurso_ate && <> Recursos até {formatDateTime(resultado.prazo_recurso_ate)}.</>}
                    {' '}A classificação pode mudar após o julgamento dos recursos.
                  </>
                )}
                <span className="block text-xs mt-1 opacity-80">
                  {resultado.total_homologadas} candidato(s) avaliado(s) · {resultado.vagas_totais} vaga(s)
                </span>
              </div>

              <Tabela
                titulo={`Contemplados (${resultado.contemplados.length})`}
                icon={<Trophy className="h-4 w-4 text-emerald-600 mr-2" />}
                itens={resultado.contemplados}
                destaque
                mostrarMatricula={mostrarMatricula}
              />
              {resultado.suplentes.length > 0 && (
                <Tabela
                  titulo={`Cadastro de reserva (${resultado.suplentes.length})`}
                  icon={<Award className="h-4 w-4 text-slate-500 mr-2" />}
                  itens={resultado.suplentes}
                  mostrarMatricula={mostrarMatricula}
                />
              )}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
};
