import React, { useState } from 'react';
import { X, Plus, Trash2, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { createEdital, publishEdital } from '../api/editais';

interface CreateEditalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateEditalModal: React.FC<CreateEditalModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Campos principais
  const [titulo, setTitulo] = useState('');
  const [descricao, setDescricao] = useState('');
  const [categoria, setCategoria] = useState<'ESTAGIO' | 'MONITORIA' | 'BOLSA'>('MONITORIA');
  const [modalidade, setModalidade] = useState('Presencial');
  const [valorBolsa, setValorBolsa] = useState(700);
  const [cargaHoraria, setCargaHoraria] = useState(20);
  const [vagas, setVagas] = useState(3);
  const [crMinimo, setCrMinimo] = useState(6.0);
  const [publicarDireto, setPublicarDireto] = useState(true);

  // Datas
  const now = new Date();
  const formatIsoDate = (d: Date) => d.toISOString().slice(0, 16);
  
  const dInicioInsc = new Date(now.getTime() - 1000 * 60 * 60); // 1h atrás
  const dFimInsc = new Date(now.getTime() + 1000 * 60 * 60 * 24 * 14); // 14 dias
  const dInicioAv = new Date(dFimInsc.getTime() + 1000 * 60 * 60 * 24); // 15 dias
  const dResPrelim = new Date(dInicioAv.getTime() + 1000 * 60 * 60 * 24 * 5); // 20 dias
  const dHomolog = new Date(dResPrelim.getTime() + 1000 * 60 * 60 * 24 * 5); // 25 dias

  const [dataInicioInsc, setDataInicioInsc] = useState(formatIsoDate(dInicioInsc));
  const [dataFimInsc, setDataFimInsc] = useState(formatIsoDate(dFimInsc));
  const [dataInicioAv, setDataInicioAv] = useState(formatIsoDate(dInicioAv));
  const [dataResPrelim, setDataResPrelim] = useState(formatIsoDate(dResPrelim));
  const [dataHomolog, setDataHomolog] = useState(formatIsoDate(dHomolog));

  // Cursos
  const [codigoCurso, setCodigoCurso] = useState('SI');
  const [nomeCurso, setNomeCurso] = useState('Sistemas de Informação');

  // Documentos
  const [docNome, setDocNome] = useState('Histórico Escolar Atualizado');
  const [docDescricao, setDocDescricao] = useState('Histórico oficial emitido pelo SIGA');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!titulo.trim() || !descricao.trim()) {
      setError('Preencha o título e a descrição do edital.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        titulo,
        descricao,
        categoria,
        modalidade,
        valor_bolsa: Number(valorBolsa),
        carga_horaria_semanal: Number(cargaHoraria),
        vagas: Number(vagas),
        cr_minimo: Number(crMinimo),
        prazo_recurso_horas: 48,
        data_inicio_inscricao: new Date(dataInicioInsc).toISOString(),
        data_fim_inscricao: new Date(dataFimInsc).toISOString(),
        data_inicio_avaliacao: new Date(dataInicioAv).toISOString(),
        data_resultado_preliminar: new Date(dataResPrelim).toISOString(),
        data_homologacao_final: new Date(dataHomolog).toISOString(),
        cursos: [
          { codigo_curso: codigoCurso || 'SI', nome_curso: nomeCurso || 'Sistemas de Informação' }
        ],
        documentos_exigidos: [
          { nome: docNome || 'Histórico Escolar Atualizado', descricao: docDescricao || 'Histórico emitido pelo SIGA', obrigatorio: true }
        ],
        criterios_pontuacao: { "CR": 0.6, "Entrevista": 0.4 },
        criterios_desempate: ["CR_DESC", "SUBMISSAO_ASC"]
      };

      const editalCriado = await createEdital(payload);

      if (publicarDireto && editalCriado.id) {
        await publishEdital(editalCriado.id);
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      console.error('Erro ao cadastrar edital:', err);
      setError(err?.response?.data?.detail || err?.message || 'Falha ao cadastrar edital.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-2xl w-full my-8 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold">Novo Edital de Oportunidades</h3>
            <p className="text-xs text-slate-400">Cadastre e publique editais de estágio, monitoria ou bolsa acadêmica (v5.0 EDT-01)</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Título do Edital *</label>
            <input
              type="text"
              required
              placeholder="Ex: Edital 03/2026 - Seleção de Bolsistas de Monitoria em Algoritmos"
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Descrição e Objeto *</label>
            <textarea
              required
              rows={3}
              placeholder="Descreva as atividades, pré-requisitos gerais e objetivos da oportunidade..."
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Categoria *</label>
              <select
                value={categoria}
                onChange={(e) => setCategoria(e.target.value as any)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <option value="MONITORIA">Monitoria Acadêmica</option>
                <option value="ESTAGIO">Estágio Remunerado</option>
                <option value="BOLSA">Bolsa Acadêmica / Pesquisa</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Modalidade *</label>
              <select
                value={modalidade}
                onChange={(e) => setModalidade(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <option value="Presencial">Presencial</option>
                <option value="Híbrido">Híbrido</option>
                <option value="Remoto">Remoto</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Remuneração (R$) *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={valorBolsa}
                onChange={(e) => setValorBolsa(Number(e.target.value))}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Carga Horária (h/sem) *</label>
              <input
                type="number"
                min="1"
                max="40"
                value={cargaHoraria}
                onChange={(e) => setCargaHoraria(Number(e.target.value))}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Vagas Oferecidas *</label>
              <input
                type="number"
                min="1"
                value={vagas}
                onChange={(e) => setVagas(Number(e.target.value))}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">CR Mínimo (0 a 10) *</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="10"
                value={crMinimo}
                onChange={(e) => setCrMinimo(Number(e.target.value))}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Cronograma */}
          <div className="border-t border-slate-200 pt-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase mb-2">Cronograma do Processo Seletivo (v5.0 EDT-02)</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-slate-600 mb-0.5">Início das Inscrições</label>
                <input
                  type="datetime-local"
                  value={dataInicioInsc}
                  onChange={(e) => setDataInicioInsc(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-0.5">Fim das Inscrições</label>
                <input
                  type="datetime-local"
                  value={dataFimInsc}
                  onChange={(e) => setDataFimInsc(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-0.5">Resultado Preliminar</label>
                <input
                  type="datetime-local"
                  value={dataResPrelim}
                  onChange={(e) => setDataResPrelim(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-0.5">Homologação Final</label>
                <input
                  type="datetime-local"
                  value={dataHomolog}
                  onChange={(e) => setDataHomolog(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
            </div>
          </div>

          {/* Cursos e Documentos */}
          <div className="border-t border-slate-200 pt-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <h4 className="text-xs font-bold text-slate-900 uppercase mb-1">Curso Elegível</h4>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Código (Ex: SI)"
                  value={codigoCurso}
                  onChange={(e) => setCodigoCurso(e.target.value)}
                  className="w-1/3 text-xs p-2 border border-slate-300 rounded-lg"
                />
                <input
                  type="text"
                  placeholder="Nome do Curso"
                  value={nomeCurso}
                  onChange={(e) => setNomeCurso(e.target.value)}
                  className="w-2/3 text-xs p-2 border border-slate-300 rounded-lg"
                />
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-900 uppercase mb-1">Documento Exigido (PDF)</h4>
              <input
                type="text"
                placeholder="Nome do Documento Obrigatório"
                value={docNome}
                onChange={(e) => setDocNome(e.target.value)}
                className="w-full text-xs p-2 border border-slate-300 rounded-lg"
              />
            </div>
          </div>

          {/* Publicação Direta Checkbox */}
          <div className="border-t border-slate-200 pt-3 flex items-center space-x-2">
            <input
              type="checkbox"
              id="chkPublicar"
              checked={publicarDireto}
              onChange={(e) => setPublicarDireto(e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
            />
            <label htmlFor="chkPublicar" className="text-xs text-slate-700 font-medium cursor-pointer">
              Publicar imediatamente após cadastrar (muda status para <strong>ABERTO</strong> na vitrine)
            </label>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-slate-200 flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-2 transition shadow-sm"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Cadastrando...</span>
                </>
              ) : (
                <span>{publicarDireto ? 'Cadastrar e Publicar' : 'Salvar como Rascunho'}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
