import React, { useState } from 'react';
import { AlertCircle, Loader2, Plus, Trash2, X } from 'lucide-react';
import { createEdital, publishEdital } from '../api/editais';
import { getErrorMessage } from '../api/client';
import { useToast } from './Toast';
import { inputClass } from './ui';

interface CreateEditalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (editalId: number) => void;
}

interface CursoForm { codigo_curso: string; nome_curso: string }
interface DocForm { nome: string; descricao: string; obrigatorio: boolean }

const toLocalInput = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
const daysFromNow = (days: number, hour = 23, minute = 59) => {
  const d = new Date();
  d.setDate(d.getDate() + days);
  d.setHours(hour, minute, 0, 0);
  return toLocalInput(d);
};

const initialState = () => ({
  titulo: '',
  descricao: '',
  categoria: 'MONITORIA' as 'ESTAGIO' | 'MONITORIA' | 'BOLSA',
  modalidade: 'Presencial',
  valorBolsa: '',
  cargaHoraria: '',
  vagas: '',
  crMinimo: '',
  prazoRecurso: '48',
  dataInicioInsc: toLocalInput(new Date()),
  dataFimInsc: daysFromNow(14),
  dataInicioAv: daysFromNow(15, 8, 0),
  dataResPrelim: daysFromNow(20, 18, 0),
  dataHomolog: daysFromNow(25, 18, 0),
  cursos: [{ codigo_curso: '', nome_curso: '' }] as CursoForm[],
  docs: [{ nome: 'Histórico escolar atualizado', descricao: 'Histórico oficial emitido pela secretaria acadêmica, com CR.', obrigatorio: true }] as DocForm[],
  publicar: true,
});

const Label: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <label className="block text-xs font-semibold text-slate-700 mb-1">{children}</label>
);

export const CreateEditalModal: React.FC<CreateEditalModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const toast = useToast();
  const [f, setF] = useState(initialState);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const set = <K extends keyof ReturnType<typeof initialState>>(key: K, value: ReturnType<typeof initialState>[K]) =>
    setF((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const cursos = f.cursos.filter((c) => c.codigo_curso.trim() && c.nome_curso.trim());
    const docs = f.docs.filter((d) => d.nome.trim());
    if (!cursos.length) return setError('Informe ao menos um curso elegível (código e nome).');
    if (!docs.length) return setError('Informe ao menos um documento exigido.');

    setLoading(true);
    try {
      const edital = await createEdital({
        titulo: f.titulo.trim(),
        descricao: f.descricao.trim(),
        categoria: f.categoria,
        modalidade: f.modalidade,
        valor_bolsa: Number(f.valorBolsa.replace(',', '.')),
        carga_horaria_semanal: Number(f.cargaHoraria),
        vagas: Number(f.vagas),
        cr_minimo: Number(f.crMinimo.replace(',', '.')),
        prazo_recurso_horas: Number(f.prazoRecurso),
        data_inicio_inscricao: new Date(f.dataInicioInsc).toISOString(),
        data_fim_inscricao: new Date(f.dataFimInsc).toISOString(),
        data_inicio_avaliacao: new Date(f.dataInicioAv).toISOString(),
        data_resultado_preliminar: new Date(f.dataResPrelim).toISOString(),
        data_homologacao_final: new Date(f.dataHomolog).toISOString(),
        cursos: cursos.map((c) => ({ codigo_curso: c.codigo_curso.trim().toUpperCase(), nome_curso: c.nome_curso.trim() })),
        documentos_exigidos: docs.map((d) => ({ nome: d.nome.trim(), descricao: d.descricao.trim() || null, obrigatorio: d.obrigatorio })),
        criterios_desempate: ['CR_DESC', 'SUBMISSAO_ASC'],
      });
      if (f.publicar) {
        try {
          await publishEdital(edital.id);
        } catch (err) {
          toast.error(`Edital salvo como rascunho, mas não foi publicado: ${getErrorMessage(err)}`);
        }
      }
      toast.success(f.publicar ? 'Edital cadastrado.' : 'Rascunho salvo.');
      setF(initialState());
      onSuccess(edital.id);
      onClose();
    } catch (err) {
      setError(getErrorMessage(err, 'Não foi possível cadastrar o edital.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full overflow-hidden flex flex-col max-h-[92vh]">
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold">Novo edital</h3>
            <p className="text-xs text-slate-400">Estágio, monitoria ou bolsa acadêmica</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded-lg" aria-label="Fechar"><X className="h-5 w-5" /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto flex-1">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0" /> {error}
            </div>
          )}

          <div>
            <Label>Título *</Label>
            <input required minLength={5} placeholder="Ex.: Edital 03/2026 — Monitoria de Algoritmos" value={f.titulo} onChange={(e) => set('titulo', e.target.value)} className={inputClass} />
          </div>
          <div>
            <Label>Descrição *</Label>
            <textarea required minLength={10} rows={4} placeholder="Objeto, atividades, requisitos e informações gerais." value={f.descricao} onChange={(e) => set('descricao', e.target.value)} className={inputClass} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <Label>Categoria *</Label>
              <select value={f.categoria} onChange={(e) => set('categoria', e.target.value as 'ESTAGIO' | 'MONITORIA' | 'BOLSA')} className={inputClass}>
                <option value="MONITORIA">Monitoria</option>
                <option value="ESTAGIO">Estágio</option>
                <option value="BOLSA">Bolsa</option>
              </select>
            </div>
            <div>
              <Label>Modalidade *</Label>
              <select value={f.modalidade} onChange={(e) => set('modalidade', e.target.value)} className={inputClass}>
                <option>Presencial</option>
                <option>Híbrido</option>
                <option>Remoto</option>
              </select>
            </div>
            <div>
              <Label>Bolsa mensal (R$) *</Label>
              <input required inputMode="decimal" value={f.valorBolsa} onChange={(e) => set('valorBolsa', e.target.value)} className={inputClass} />
            </div>
            <div>
              <Label>Carga horária (h/sem) *</Label>
              <input required type="number" min={1} max={44} value={f.cargaHoraria} onChange={(e) => set('cargaHoraria', e.target.value)} className={inputClass} />
            </div>
            <div>
              <Label>Vagas *</Label>
              <input required type="number" min={1} value={f.vagas} onChange={(e) => set('vagas', e.target.value)} className={inputClass} />
            </div>
            <div>
              <Label>CR mínimo *</Label>
              <input required inputMode="decimal" placeholder="0 a 10" value={f.crMinimo} onChange={(e) => set('crMinimo', e.target.value)} className={inputClass} />
            </div>
            <div>
              <Label>Prazo de recurso (h) *</Label>
              <input required type="number" min={1} value={f.prazoRecurso} onChange={(e) => set('prazoRecurso', e.target.value)} className={inputClass} />
            </div>
          </div>

          <fieldset className="border-t border-slate-200 pt-4">
            <legend className="text-sm font-bold text-slate-900 mb-2">Cronograma</legend>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {([
                ['dataInicioInsc', 'Início das inscrições'],
                ['dataFimInsc', 'Fim das inscrições'],
                ['dataInicioAv', 'Início da avaliação'],
                ['dataResPrelim', 'Resultado preliminar'],
                ['dataHomolog', 'Resultado final'],
              ] as const).map(([key, label]) => (
                <div key={key}>
                  <Label>{label}</Label>
                  <input type="datetime-local" required value={f[key]} onChange={(e) => set(key, e.target.value)} className={inputClass} />
                </div>
              ))}
            </div>
          </fieldset>

          <fieldset className="border-t border-slate-200 pt-4">
            <legend className="text-sm font-bold text-slate-900 mb-2">Cursos elegíveis</legend>
            <div className="space-y-2">
              {f.cursos.map((c, i) => (
                <div key={i} className="flex gap-2">
                  <input placeholder="Código (ex.: SI)" value={c.codigo_curso} onChange={(e) => set('cursos', f.cursos.map((x, j) => (j === i ? { ...x, codigo_curso: e.target.value } : x)))} className={`${inputClass} w-32`} />
                  <input placeholder="Nome do curso" value={c.nome_curso} onChange={(e) => set('cursos', f.cursos.map((x, j) => (j === i ? { ...x, nome_curso: e.target.value } : x)))} className={inputClass} />
                  {f.cursos.length > 1 && (
                    <button type="button" onClick={() => set('cursos', f.cursos.filter((_, j) => j !== i))} className="text-slate-400 hover:text-red-600 px-2" aria-label="Remover curso"><Trash2 className="h-4 w-4" /></button>
                  )}
                </div>
              ))}
              <button type="button" onClick={() => set('cursos', [...f.cursos, { codigo_curso: '', nome_curso: '' }])} className="text-sm text-blue-600 font-medium flex items-center"><Plus className="h-4 w-4 mr-1" /> Adicionar curso</button>
            </div>
          </fieldset>

          <fieldset className="border-t border-slate-200 pt-4">
            <legend className="text-sm font-bold text-slate-900 mb-2">Documentos exigidos (PDF)</legend>
            <div className="space-y-2">
              {f.docs.map((d, i) => (
                <div key={i} className="flex flex-col sm:flex-row gap-2 sm:items-center">
                  <input placeholder="Nome do documento" value={d.nome} onChange={(e) => set('docs', f.docs.map((x, j) => (j === i ? { ...x, nome: e.target.value } : x)))} className={`${inputClass} sm:w-64`} />
                  <input placeholder="Orientação (opcional)" value={d.descricao} onChange={(e) => set('docs', f.docs.map((x, j) => (j === i ? { ...x, descricao: e.target.value } : x)))} className={inputClass} />
                  <label className="flex items-center gap-1.5 text-xs text-slate-700 whitespace-nowrap">
                    <input type="checkbox" checked={d.obrigatorio} onChange={(e) => set('docs', f.docs.map((x, j) => (j === i ? { ...x, obrigatorio: e.target.checked } : x)))} /> Obrigatório
                  </label>
                  {f.docs.length > 1 && (
                    <button type="button" onClick={() => set('docs', f.docs.filter((_, j) => j !== i))} className="text-slate-400 hover:text-red-600 px-2" aria-label="Remover documento"><Trash2 className="h-4 w-4" /></button>
                  )}
                </div>
              ))}
              <button type="button" onClick={() => set('docs', [...f.docs, { nome: '', descricao: '', obrigatorio: true }])} className="text-sm text-blue-600 font-medium flex items-center"><Plus className="h-4 w-4 mr-1" /> Adicionar documento</button>
            </div>
          </fieldset>

          <label className="border-t border-slate-200 pt-4 flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
            <input type="checkbox" checked={f.publicar} onChange={(e) => set('publicar', e.target.checked)} className="h-4 w-4" />
            Publicar imediatamente (caso contrário, fica salvo como rascunho, visível apenas para a Pró-Reitoria)
          </label>

          <div className="pt-4 border-t border-slate-200 flex justify-end gap-3">
            <button type="button" onClick={onClose} disabled={loading} className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={loading} className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold flex items-center gap-2 disabled:opacity-60">
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {f.publicar ? 'Cadastrar e publicar' : 'Salvar rascunho'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
