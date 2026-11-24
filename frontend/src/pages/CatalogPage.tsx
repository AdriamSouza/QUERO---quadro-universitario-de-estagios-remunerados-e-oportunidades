import React, { useState, useEffect } from 'react';
import { Search, Calendar, Users, DollarSign, Award, ArrowRight, Briefcase } from 'lucide-react';
import { Edital } from '../types/edital';
import { fetchEditais } from '../api/editais';

interface CatalogPageProps {
  onSelectEdital: (id: number) => void;
}

export const CatalogPage: React.FC<CatalogPageProps> = ({ onSelectEdital }) => {
  const [editais, setEditais] = useState<Edital[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoria, setCategoria] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchEditais({
        categoria: categoria || undefined,
        busca: searchTerm || undefined,
      });
      setEditais(data.items);
    } catch (err) {
      console.error('Falha ao carregar editais', err);
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
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Oportunidades Universitárias</h2>
        <p className="mt-2 text-slate-600">
          QUERO — Quadro Universitário de Estágios Remunerados e Oportunidades: vagas de estágio, monitoria e bolsas acadêmicas.
        </p>
      </div>

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
            className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg text-sm hover:bg-blue-700 transition"
          >
            Filtrar Oportunidades
          </button>
        </div>
      </form>

      {/* Grid de Cards */}
      {loading ? (
        <div className="text-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-500 text-sm">Carregando oportunidades abertas...</p>
        </div>
      ) : editais.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <Briefcase className="h-12 w-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-slate-900">Nenhum edital encontrado</h3>
          <p className="text-sm text-slate-500 mt-1">Ajuste os filtros de pesquisa para visualizar outras chamadas.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {editais.map((edital) => (
            <div
              key={edital.id}
              className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition flex flex-col justify-between"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-3">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-100">
                    {edital.categoria} • {edital.modalidade}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    edital.status === 'ABERTO' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {edital.status}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-slate-900 mb-2 line-clamp-2">
                  {edital.titulo}
                </h3>
                <p className="text-slate-600 text-xs mb-4 line-clamp-3 leading-relaxed">
                  {edital.descricao}
                </p>

                <div className="space-y-2 border-t border-slate-100 pt-3 text-xs text-slate-500">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center">
                      <DollarSign className="h-4 w-4 mr-1 text-slate-400" />
                      Remuneração / Bolsa
                    </span>
                    <span className="font-semibold text-slate-800">
                      R$ {Number(edital.valor_bolsa).toFixed(2)}/mês
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center">
                      <Users className="h-4 w-4 mr-1 text-slate-400" />
                      Vagas disponíveis
                    </span>
                    <span className="font-medium text-slate-700">
                      {edital.vagas} vaga(s) ({edital.carga_horaria_semanal}h/sem)
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center">
                      <Award className="h-4 w-4 mr-1 text-slate-400" />
                      CR Mínimo
                    </span>
                    <span className="font-medium text-slate-700">
                      &ge; {Number(edital.cr_minimo).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-slate-500">
                  Inscrições até {new Date(edital.data_fim_inscricao).toLocaleDateString('pt-BR')}
                </span>
                <button
                  onClick={() => onSelectEdital(edital.id)}
                  className="flex items-center text-xs font-semibold text-blue-600 hover:text-blue-800 transition"
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
