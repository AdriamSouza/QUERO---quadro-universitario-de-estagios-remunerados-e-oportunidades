import React, { useEffect, useState } from 'react';
import { Loader2, Search, UserPlus, Users } from 'lucide-react';
import { createUsuario, fetchUsuarios, updateUsuario, Usuario, UsuarioCreatePayload } from '../api/usuarios';
import { getErrorMessage } from '../api/client';
import { EmptyState, Modal, PageHeader, Spinner, btn, inputClass } from '../components/ui';
import { useToast } from '../components/Toast';
import { useAuth } from '../context/AuthContext';
import { formatDate, PERFIL_LABEL } from '../utils/format';

const VAZIO: UsuarioCreatePayload = { nome: '', email: '', cpf: '', matricula: '', perfil: 'AVALIADOR', senha: '' };

export const UsersPage: React.FC = () => {
  const toast = useToast();
  const { user } = useAuth();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [perfil, setPerfil] = useState('');
  const [busca, setBusca] = useState('');
  const [criando, setCriando] = useState(false);
  const [form, setForm] = useState<UsuarioCreatePayload>(VAZIO);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setUsuarios((await fetchUsuarios({ perfil, busca })).items);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [perfil]);

  const criar = async () => {
    setSaving(true);
    try {
      await createUsuario({ ...form, matricula: form.matricula || undefined });
      toast.success('Usuário cadastrado. Informe a senha inicial ao titular da conta.');
      setCriando(false);
      setForm(VAZIO);
      load();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const alternarAtivo = async (u: Usuario) => {
    if (!window.confirm(`${u.ativo ? 'Desativar' : 'Reativar'} a conta de ${u.nome}?`)) return;
    try {
      const atualizado = await updateUsuario(u.id, { ativo: !u.ativo });
      setUsuarios((prev) => prev.map((x) => (x.id === u.id ? atualizado : x)));
      toast.success(atualizado.ativo ? 'Conta reativada.' : 'Conta desativada.');
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const redefinirSenha = async (u: Usuario) => {
    const nova = window.prompt(`Nova senha para ${u.nome} (mínimo de 8 caracteres):`);
    if (!nova) return;
    try {
      await updateUsuario(u.id, { nova_senha: nova });
      toast.success('Senha redefinida.');
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="Usuários"
        subtitle="Cadastro de avaliadores e gestores, e controle de acesso das contas."
        actions={<button onClick={() => setCriando(true)} className={btn.primary}><UserPlus className="h-4 w-4 mr-1.5" /> Novo usuário</button>}
      />

      <form onSubmit={(e) => { e.preventDefault(); load(); }} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome, e-mail ou matrícula" className={`${inputClass} pl-9`} />
        </div>
        <select value={perfil} onChange={(e) => setPerfil(e.target.value)} className={`${inputClass} sm:w-48`}>
          <option value="">Todos os perfis</option>
          {Object.entries(PERFIL_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <button type="submit" className={btn.secondary}>Buscar</button>
      </form>

      {loading ? (
        <Spinner />
      ) : usuarios.length === 0 ? (
        <EmptyState icon={<Users className="h-12 w-12" />} title="Nenhum usuário encontrado" />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase border-b border-slate-100">
              <tr>
                <th className="py-2.5 px-4">Nome</th>
                <th className="py-2.5 px-4">E-mail</th>
                <th className="py-2.5 px-4">Perfil</th>
                <th className="py-2.5 px-4">Cadastro</th>
                <th className="py-2.5 px-4">Situação</th>
                <th className="py-2.5 px-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {usuarios.map((u) => (
                <tr key={u.id} className={u.ativo ? '' : 'opacity-60'}>
                  <td className="py-2.5 px-4 font-medium text-slate-900">{u.nome}</td>
                  <td className="py-2.5 px-4 text-slate-600">{u.email}</td>
                  <td className="py-2.5 px-4">{PERFIL_LABEL[u.perfil]}</td>
                  <td className="py-2.5 px-4 text-slate-500">{formatDate(u.criado_em)}</td>
                  <td className="py-2.5 px-4">{u.ativo ? <span className="text-emerald-700">Ativa</span> : <span className="text-slate-500">Desativada</span>}</td>
                  <td className="py-2.5 px-4 text-right whitespace-nowrap">
                    <button onClick={() => redefinirSenha(u)} className="text-blue-600 hover:text-blue-800 text-xs font-semibold mr-3">Redefinir senha</button>
                    {u.id !== user?.id && (
                      <button onClick={() => alternarAtivo(u)} className="text-xs font-semibold text-slate-600 hover:text-slate-900">
                        {u.ativo ? 'Desativar' : 'Reativar'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {criando && (
        <Modal
          title="Novo usuário"
          onClose={() => setCriando(false)}
          footer={
            <>
              <button onClick={() => setCriando(false)} className={btn.secondary}>Cancelar</button>
              <button onClick={criar} disabled={saving} className={btn.primary}>{saving && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />} Cadastrar</button>
            </>
          }
        >
          <div className="space-y-3">
            <input placeholder="Nome completo" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} className={inputClass} />
            <input type="email" placeholder="E-mail" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={inputClass} />
            <div className="grid grid-cols-2 gap-3">
              <input placeholder="CPF" value={form.cpf} onChange={(e) => setForm({ ...form, cpf: e.target.value })} className={inputClass} />
              <input placeholder="Matrícula/SIAPE (opcional)" value={form.matricula} onChange={(e) => setForm({ ...form, matricula: e.target.value })} className={inputClass} />
            </div>
            <select value={form.perfil} onChange={(e) => setForm({ ...form, perfil: e.target.value as Usuario['perfil'] })} className={inputClass}>
              <option value="AVALIADOR">Avaliador(a)</option>
              <option value="PRO_REITOR">Pró-Reitoria (gestão)</option>
              <option value="ESTUDANTE">Estudante</option>
            </select>
            <input type="text" placeholder="Senha inicial (mínimo de 8 caracteres)" value={form.senha} onChange={(e) => setForm({ ...form, senha: e.target.value })} className={inputClass} autoComplete="off" />
            <p className="text-xs text-slate-500">Oriente o usuário a alterar a senha no primeiro acesso (menu do usuário › Alterar senha).</p>
          </div>
        </Modal>
      )}
    </div>
  );
};
