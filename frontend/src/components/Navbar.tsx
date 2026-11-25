import React, { useEffect, useRef, useState } from 'react';
import { Bell, ChevronDown, GraduationCap, KeyRound, LogIn, LogOut, PlusCircle } from 'lucide-react';
import { useAuth, UserRole } from '../context/AuthContext';
import { useToast } from './Toast';
import { Modal, btn, inputClass } from './ui';
import { changePassword, fetchNotificacoes, markAllNotificationsRead, Notificacao } from '../api/usuarios';
import { getErrorMessage } from '../api/client';
import { formatDateTime, PERFIL_LABEL } from '../utils/format';

interface NavbarProps {
  onNavigate: (page: string) => void;
  currentPage: string;
  onOpenCreateEdital?: () => void;
}

const NAV_ITEMS: { page: string; label: string; roles?: UserRole[] }[] = [
  { page: 'catalog', label: 'Editais' },
  { page: 'my-applications', label: 'Minhas inscrições', roles: ['ESTUDANTE'] },
  { page: 'review', label: 'Inscrições', roles: ['PRO_REITOR'] },
  { page: 'evaluation', label: 'Avaliação', roles: ['AVALIADOR', 'PRO_REITOR'] },
  { page: 'results', label: 'Resultados' },
  { page: 'approval', label: 'Homologação', roles: ['PRO_REITOR'] },
  { page: 'users', label: 'Usuários', roles: ['PRO_REITOR'] },
  { page: 'audit', label: 'Auditoria', roles: ['PRO_REITOR'] },
];

const useClickOutside = (ref: React.RefObject<HTMLElement>, onOutside: () => void) => {
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onOutside();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [ref, onOutside]);
};

const NotificationBell: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notificacao[]>([]);
  const [naoLidas, setNaoLidas] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false));

  const load = () =>
    fetchNotificacoes()
      .then((res) => {
        setItems(res.items);
        setNaoLidas(res.nao_lidas);
      })
      .catch(() => undefined);

  useEffect(() => {
    load();
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, []);

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && naoLidas > 0) {
      await markAllNotificationsRead().catch(() => undefined);
      setNaoLidas(0);
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button onClick={toggle} className="relative p-2 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white" aria-label="Notificações">
        <Bell className="h-5 w-5" />
        {naoLidas > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full h-4 min-w-[1rem] px-1 flex items-center justify-center">
            {naoLidas > 9 ? '9+' : naoLidas}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-white text-slate-900 rounded-xl shadow-2xl border border-slate-200 z-50">
          <div className="px-4 py-3 border-b border-slate-100 text-sm font-semibold">Notificações</div>
          {items.length === 0 ? (
            <p className="px-4 py-6 text-sm text-slate-500 text-center">Nenhuma notificação.</p>
          ) : (
            items.map((n) => (
              <div key={n.id} className={`px-4 py-3 border-b border-slate-50 text-sm ${n.lida ? '' : 'bg-blue-50/50'}`}>
                <p className="font-semibold text-slate-800">{n.titulo}</p>
                <p className="text-slate-600 text-xs mt-0.5">{n.mensagem}</p>
                <p className="text-[11px] text-slate-400 mt-1">{formatDateTime(n.criado_em)}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

const ChangePasswordModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const toast = useToast();
  const [atual, setAtual] = useState('');
  const [nova, setNova] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (nova.length < 8) return toast.error('A nova senha deve ter pelo menos 8 caracteres.');
    if (nova !== confirmacao) return toast.error('A confirmação não corresponde à nova senha.');
    setSaving(true);
    try {
      await changePassword(atual, nova);
      toast.success('Senha alterada com sucesso.');
      onClose();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Alterar senha"
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className={btn.secondary}>Cancelar</button>
          <button onClick={submit} disabled={saving} className={btn.primary}>Salvar</button>
        </>
      }
    >
      <div className="space-y-3">
        <input type="password" placeholder="Senha atual" value={atual} onChange={(e) => setAtual(e.target.value)} className={inputClass} autoComplete="current-password" />
        <input type="password" placeholder="Nova senha (mínimo 8 caracteres)" value={nova} onChange={(e) => setNova(e.target.value)} className={inputClass} autoComplete="new-password" />
        <input type="password" placeholder="Confirme a nova senha" value={confirmacao} onChange={(e) => setConfirmacao(e.target.value)} className={inputClass} autoComplete="new-password" />
      </div>
    </Modal>
  );
};

export const Navbar: React.FC<NavbarProps> = ({ onNavigate, currentPage, onOpenCreateEdital }) => {
  const { user, role, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  useClickOutside(menuRef, () => setMenuOpen(false));

  const items = NAV_ITEMS.filter((item) => !item.roles || (role && item.roles.includes(role)));

  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <button className="flex items-center space-x-3 text-left" onClick={() => onNavigate('catalog')}>
          <div className="bg-blue-600 p-2 rounded-xl shadow-sm">
            <GraduationCap className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight leading-tight">QUERO</h1>
            <p className="text-[11px] text-slate-400 hidden sm:block">Estágios, monitorias e bolsas</p>
          </div>
        </button>

        <nav className="hidden lg:flex items-center gap-1">
          {items.map((item) => (
            <button
              key={item.page}
              onClick={() => onNavigate(item.page)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                currentPage === item.page ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {role === 'PRO_REITOR' && onOpenCreateEdital && (
            <button
              onClick={onOpenCreateEdital}
              className="hidden sm:flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-sm font-semibold transition"
            >
              <PlusCircle className="h-4 w-4" />
              <span>Novo edital</span>
            </button>
          )}

          {!user ? (
            <button
              onClick={() => onNavigate('login')}
              className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-3.5 py-1.5 rounded-lg text-sm font-semibold transition"
            >
              <LogIn className="h-4 w-4" />
              <span>Entrar</span>
            </button>
          ) : (
            <>
              <NotificationBell />
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setMenuOpen(!menuOpen)}
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 rounded-lg text-sm transition"
                >
                  <span className="h-6 w-6 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold">
                    {user.nome.charAt(0).toUpperCase()}
                  </span>
                  <div className="text-left hidden md:block">
                    <p className="font-semibold text-slate-100 leading-tight text-xs">{user.nome}</p>
                    <p className="text-[10px] text-slate-400 leading-none">{role ? PERFIL_LABEL[role] : ''}</p>
                  </div>
                  <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                </button>
                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-64 bg-white text-slate-900 rounded-xl shadow-2xl border border-slate-200 py-2 z-50">
                    <div className="px-4 py-2 border-b border-slate-100">
                      <p className="text-sm font-semibold">{user.nome}</p>
                      <p className="text-xs text-slate-500 truncate">{user.email}</p>
                    </div>
                    <button
                      onClick={() => { setMenuOpen(false); setShowPassword(true); }}
                      className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 flex items-center gap-2"
                    >
                      <KeyRound className="h-4 w-4 text-slate-500" /> Alterar senha
                    </button>
                    <button
                      onClick={() => { setMenuOpen(false); logout(); onNavigate('catalog'); }}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                    >
                      <LogOut className="h-4 w-4" /> Sair
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Navegação em telas menores */}
      <nav className="lg:hidden flex gap-1 overflow-x-auto px-4 pb-2 -mt-1">
        {items.map((item) => (
          <button
            key={item.page}
            onClick={() => onNavigate(item.page)}
            className={`whitespace-nowrap px-3 py-1 rounded-lg text-xs font-medium ${
              currentPage === item.page ? 'bg-slate-800 text-white' : 'text-slate-300'
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {showPassword && <ChangePasswordModal onClose={() => setShowPassword(false)} />}
    </header>
  );
};
