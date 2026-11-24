import React, { useState, useEffect } from 'react';
import { Search, Calendar, Users, DollarSign, Award, ArrowRight, Briefcase, Plus, AlertCircle, RefreshCw } from 'lucide-react';
import { Edital } from '../types/edital';
import { fetchEditais } from '../api/editais';
import { useAuth } from '../context/AuthContext';

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

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEditais({
        categoria: categoria || undefined,
        busca: searchTerm || undefined,
      });
      setEditais(data.items || []);
    } catch (err: any) {
      console.error('Falha ao carregar editais:', err);
      setError(
        err?.response?.data?.detail || 
        err?.message || 
        'Não foi possível conectar ao servidor para carregar os editais.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [categoria]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header com chamada */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Oportunidades Universitárias</h2>
          <p className="mt-1 text-sm text-slate-600">
            QUERO — Quadro Universitário de Estágios Remunerados e Oportunidades: vagas de estágio, monitoria e bolsas acadêmicas.
          </p>
        </div>

        {role === 'PRO_REITOR' && onOpenCreateEdital && (
          <button
            onClick={onOpenCreateEdital}
            className="self-start md:self-auto flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-sm transition"
          >
            <Plus className="h-4 w-4" />
            <span>Novo Edital de Seleção</span>
          </button>
        )}
      </div>

      {/* Alerta de Erro com Retry */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-xl mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center space-x-2.5">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
            <div>
              <p className="font-semibold text-xs">Erro na comunicação com a API:</p>
              <p className="text-xs text-red-700 mt-0.5">{error}</p>
            </div>
          </div>
          <button
            onClick={loadData}
            className="self-start sm:self-auto flex items-center space-x-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Tentar Novamente</span>
          </button>
        </div>
      )}

      {/* Barra de Filtros */}
      <form onSubmit={handleSearchSubmit} className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 mb-8 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="relative md:col-span-2">
          <Search className="absolute left-3 top-2.5 h-5 w-5 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por título ou descrição..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <select
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
            className="w-full py-2 px-3 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-700"
          >
            <option value="">Todas as Categorias</option>
            <option value="ESTAGIO">Estágio Remunerado</option>
            <option value="MONITORIA">Monitoria Acadêmica</option>
            <option value="BOLSA">Bolsa Acadêmica / Pesquisa</option>
          </select>
        </div>

        <div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg text-sm hover:bg-blue-700 transition shadow-sm"
          >
            Filtrar Oportunidades
          </button>
        </div>
      </form>

      {/* Grid de Cards */}
      {loading ? (
        <div className="text-center py-20 bg-white rounded-xl border border-slate-200">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-500 text-xs font-medium">Carregando oportunidades abertas...</p>
        </div>
      ) : editais.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200 p-8">
          <Briefcase className="h-12 w-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-900">Nenhum edital encontrado</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            {searchTerm || categoria 
              ? 'Nenhum resultado corresponde aos filtros aplicados. Tente ajustar os termos de pesquisa.'
              : 'Não há editais abertos no momento. Novos editais publicados pela Pró-Reitoria aparecerão aqui automaticamente.'}
          </p>
          {role === 'PRO_REITOR' && onOpenCreateEdital && (
            <button
              onClick={onOpenCreateEdital}
              className="mt-4 inline-flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-xs font-semibold transition"
            >
              <Plus className="h-4 w-4" />
              <span>Publicar Primeiro Edital</span>
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {editais.map((edital) => (
            <div
              key={edital.id}
              className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition flex flex-col justify-between"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-3">
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-100">
                    {edital.categoria} • {edital.modalidade}
                  </span>
                  <span className={`text-[11px] px-2 py-0.5 rounded-full font-bold ${
                    edital.status === 'ABERTO' 
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                      : 'bg-slate-100 text-slate-600'
                  }`}>
                    {edital.status}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900 mb-2 line-clamp-2 leading-snug">
                  {edital.titulo}
                </h3>
                <p className="text-slate-600 text-xs mb-4 line-clamp-3 leading-relaxed">
                  {edital.descricao}
                </p>

                <div className="space-y-2 border-t border-slate-100 pt-3 text-xs text-slate-500">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center text-slate-500">
                      <DollarSign className="h-4 w-4 mr-1 text-slate-400" />
                      Remuneração
                    </span>
                    <span className="font-bold text-slate-800">
                      R$ {Number(edital.valor_bolsa).toFixed(2)}/mês
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center text-slate-500">
                      <Users className="h-4 w-4 mr-1 text-slate-400" />
                      Vagas
                    </span>
                    <span className="font-medium text-slate-700">
                      {edital.vagas} vaga(s) &middot; {edital.carga_horaria_semanal}h/sem
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center text-slate-500">
                      <Award className="h-4 w-4 mr-1 text-slate-400" />
                      CR Mínimo
                    </span>
                    <span className="font-medium text-slate-700">
                      &ge; {Number(edital.cr_minimo).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-slate-500">
                  Inscrições até {new Date(edital.data_fim_inscricao).toLocaleDateString('pt-BR')}
                </span>
                <button
                  onClick={() => onSelectEdital(edital.id)}
                  className="flex items-center text-xs font-bold text-blue-600 hover:text-blue-800 transition"
                >
                  Ver Edital
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
