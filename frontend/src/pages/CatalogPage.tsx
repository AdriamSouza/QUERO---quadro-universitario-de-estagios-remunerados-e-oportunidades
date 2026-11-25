import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowRight, Award, Briefcase, Clock, Plus, RefreshCw, Search, Users, Wallet } from 'lucide-react';
import { Edital } from '../types/edital';
import { fetchEditais } from '../api/editais';
import { getErrorMessage } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { EditalStatusBadge, PageHeader, Spinner } from '../components/ui';
import { CATEGORIA_LABEL, formatDate, formatMoney, formatNumber } from '../utils/format';

interface CatalogPageProps {
  onSelectEdital: (id: number) => void;
  onOpenCreateEdital?: () => void;
}

export const CatalogPage: React.FC<CatalogPageProps> = ({ onSelectEdital, onOpenCreateEdital }) => {
  const { role } = useAuth();
  const [editais, setEditais] = useState<Edital[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoria, setCategoria] = useState('');
  const [somenteAbertos, setSomenteAbertos] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEditais({
        categoria: categoria || undefined,
        busca: searchTerm || undefined,
        somente_abertos: somenteAbertos || undefined,
      });
      setEditais(data.items || []);
    } catch (err) {
      setError(getErrorMessage(err, 'Não foi possível carregar os editais.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoria, somenteAbertos]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="Oportunidades acadêmicas"
        subtitle="Editais de estágio remunerado, monitoria e bolsas acadêmicas da universidade."
        actions={
          role === 'PRO_REITOR' && onOpenCreateEdital ? (
            <button
              onClick={onOpenCreateEdital}
              className="self-start md:self-auto flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm px-4 py-2.5 rounded-lg shadow-sm"
            >
              <Plus className="h-4 w-4" /> Novo edital
            </button>
          ) : undefined
        }
      />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-xl mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 text-sm">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={loadData} className="self-start flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold">
            <RefreshCw className="h-3.5 w-3.5" /> Tentar novamente
          </button>
        </div>
      )}

      <form
        onSubmit={(e) => { e.preventDefault(); loadData(); }}
        className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 mb-8 grid grid-cols-1 md:grid-cols-5 gap-3 items-center"
      >
        <div className="relative md:col-span-2">
          <Search className="absolute left-3 top-2.5 h-5 w-5 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por título ou descrição"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={categoria}
          onChange={(e) => setCategoria(e.target.value)}
          className="w-full py-2 px-3 border border-slate-300 rounded-lg text-sm bg-white text-slate-700"
        >
          <option value="">Todas as categorias</option>
          <option value="ESTAGIO">Estágio remunerado</option>
          <option value="MONITORIA">Monitoria</option>
          <option value="BOLSA">Bolsa acadêmica / pesquisa</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
          <input type="checkbox" checked={somenteAbertos} onChange={(e) => setSomenteAbertos(e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
          Somente inscrições abertas
        </label>
        <button type="submit" className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg text-sm hover:bg-blue-700">
          Buscar
        </button>
      </form>

      {loading ? (
        <Spinner label="Carregando editais..." />
      ) : editais.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200 p-8">
          <Briefcase className="h-12 w-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-900">Nenhum edital encontrado</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
            {searchTerm || categoria || somenteAbertos
              ? 'Nenhum edital corresponde aos filtros selecionados.'
              : 'Não há editais publicados no momento. Novas oportunidades serão divulgadas aqui.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {editais.map((edital) => (
            <article key={edital.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition flex flex-col justify-between">
              <div className="p-6">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-100">
                    {CATEGORIA_LABEL[edital.categoria] || edital.categoria} · {edital.modalidade}
                  </span>
                  <EditalStatusBadge status={edital.status} />
                </div>
                <h3 className="text-base font-bold text-slate-900 mb-2 line-clamp-2 leading-snug">{edital.titulo}</h3>
                <p className="text-slate-600 text-sm mb-4 line-clamp-3 leading-relaxed">{edital.descricao}</p>
                <dl className="space-y-2 border-t border-slate-100 pt-3 text-sm">
                  <div className="flex items-center justify-between">
                    <dt className="flex items-center text-slate-500"><Wallet className="h-4 w-4 mr-1.5 text-slate-400" />Bolsa mensal</dt>
                    <dd className="font-semibold text-slate-800">{formatMoney(edital.valor_bolsa)}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="flex items-center text-slate-500"><Users className="h-4 w-4 mr-1.5 text-slate-400" />Vagas</dt>
                    <dd className="text-slate-700">{edital.vagas} · {edital.carga_horaria_semanal}h/semana</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="flex items-center text-slate-500"><Award className="h-4 w-4 mr-1.5 text-slate-400" />CR mínimo</dt>
                    <dd className="text-slate-700">{formatNumber(edital.cr_minimo)}</dd>
                  </div>
                </dl>
              </div>
              <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-100 rounded-b-2xl flex items-center justify-between">
                <span className="text-xs text-slate-500 flex items-center">
                  <Clock className="h-3.5 w-3.5 mr-1" />
                  {edital.status === 'ABERTO'
                    ? `Inscrições até ${formatDate(edital.data_fim_inscricao)}`
                    : edital.status === 'RASCUNHO'
                      ? `Inscrições a partir de ${formatDate(edital.data_inicio_inscricao)}`
                      : `Inscrições encerradas em ${formatDate(edital.data_fim_inscricao)}`}
                </span>
                <button onClick={() => onSelectEdital(edital.id)} className="flex items-center text-sm font-semibold text-blue-600 hover:text-blue-800">
                  Ver edital <ArrowRight className="h-4 w-4 ml-1" />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};
