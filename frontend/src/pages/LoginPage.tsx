import React, { useState } from 'react';
import { 
  GraduationCap, 
  ShieldCheck, 
  UserCheck, 
  ArrowRight, 
  CheckCircle2, 
  LogIn, 
  AlertCircle, 
  Loader2, 
  LogOut, 
  Building2, 
  BookOpen, 
  Scale, 
  KeyRound 
} from 'lucide-react';
import { useAuth, UserRole } from '../context/AuthContext';

interface LoginPageProps {
  onLoginSuccess: () => void;
  onNavigate: (page: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess, onNavigate }) => {
  const { user, role, switchProfile, loginWithCustomEmail, logout, loading } = useAuth();
  
  const [customEmail, setCustomEmail] = useState('');
  const [customPassword, setCustomPassword] = useState('');
  const [customRole, setCustomRole] = useState<UserRole>('ESTUDANTE');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleQuickLogin = async (targetRole: UserRole) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await switchProfile(targetRole);
      onLoginSuccess();
    } catch (err: any) {
      setErrorMessage(err?.message || 'Falha ao autenticar.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCustomLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customEmail.trim()) {
      setErrorMessage('Informe o e-mail institucional.');
      return;
    }
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      if (loginWithCustomEmail) {
        await loginWithCustomEmail(customEmail.trim(), customRole);
      } else {
        await switchProfile(customRole);
      }
      onLoginSuccess();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Credenciais inválidas.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Top Banner / Heading */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center justify-center p-3 bg-blue-600 text-white rounded-2xl shadow-md mb-4">
          <GraduationCap className="h-8 w-8" />
        </div>
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Portal de Acesso & Identidade</h2>
        <p className="mt-2 text-sm text-slate-600">
          Autenticação institucional do <strong>QUERO</strong>. Selecione um perfil demonstrativo ou insira suas credenciais institucionais (v5.0 RNF-06 / TRV-02).
        </p>
      </div>

      {/* Alerta de Erro se houver */}
      {errorMessage && (
        <div className="max-w-2xl mx-auto mb-8 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs flex items-center space-x-3">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Se já estiver conectado, exibe o cartão da sessão ativa */}
      {user && (
        <div className="max-w-2xl mx-auto bg-white rounded-2xl border border-slate-200 p-6 shadow-sm mb-10">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center space-x-3">
              <div className="h-12 w-12 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-lg">
                {user.nome.charAt(0)}
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-base font-bold text-slate-900">{user.nome}</h3>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    Sessão Ativa
                  </span>
                </div>
                <p className="text-xs text-slate-500">{user.email}</p>
              </div>
            </div>

            <button
              onClick={logout}
              className="flex items-center space-x-1.5 text-xs text-red-600 hover:text-red-700 font-semibold px-3 py-1.5 rounded-lg hover:bg-red-50 transition"
            >
              <LogOut className="h-4 w-4" />
              <span>Sair da Conta</span>
            </button>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 text-xs">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="text-slate-400 block font-medium">Perfil Atual:</span>
              <span className="text-slate-800 font-bold mt-0.5 block">{role}</span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="text-slate-400 block font-medium">Permissões Habilitadas:</span>
              <span className="text-slate-800 font-semibold mt-0.5 block">{user.perfis?.join(', ') || role}</span>
            </div>
          </div>

          <div className="mt-5 flex gap-3">
            <button
              onClick={() => onNavigate('catalog')}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-xl text-xs flex items-center justify-center space-x-2 transition shadow-sm"
            >
              <span>Ir para a Vitrine de Editais</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Seleção Rápida por Papéis Institucionais (3 Cartões Demonstrativos) */}
      <div className="mb-12">
        <div className="flex items-center space-x-2 mb-4 justify-center">
          <KeyRound className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">Acesso Rápido por Perfil Regulamentar</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Estudante */}
          <div className={`bg-white rounded-2xl border p-6 flex flex-col justify-between shadow-sm transition hover:shadow-md ${
            role === 'ESTUDANTE' && user ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-slate-200'
          }`}>
            <div>
              <div className="h-12 w-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4 text-2xl">
                🎓
              </div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100">
                  ESTUDANTE
                </span>
                {role === 'ESTUDANTE' && user && (
                  <span className="text-[10px] text-emerald-600 font-bold flex items-center">
                    <CheckCircle2 className="h-3.5 w-3.5 mr-0.5" /> Ativo
                  </span>
                )}
              </div>
              <h4 className="text-base font-bold text-slate-900 mt-2">João Silva</h4>
              <p className="text-xs text-slate-500 mb-3">estudante@faculdade.edu.br</p>
              
              <ul className="text-xs text-slate-600 space-y-1.5 border-t border-slate-100 pt-3 mb-6">
                <li className="flex items-start">
                  <span className="text-blue-500 mr-1.5 font-bold">•</span>
                  <span>Consultar vitrine de estágios e monitorias</span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-500 mr-1.5 font-bold">•</span>
                  <span>Submeter candidatura com envio de PDF</span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-500 mr-1.5 font-bold">•</span>
                  <span>Acompanhar protocolo e interpor recursos</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleQuickLogin('ESTUDANTE')}
              disabled={isSubmitting}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-4 rounded-xl text-xs transition shadow-sm flex items-center justify-center space-x-2"
            >
              {isSubmitting && role === 'ESTUDANTE' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Conectar como Estudante</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </div>

          {/* Card 2: Avaliador */}
          <div className={`bg-white rounded-2xl border p-6 flex flex-col justify-between shadow-sm transition hover:shadow-md ${
            role === 'AVALIADOR' && user ? 'border-purple-500 ring-2 ring-purple-500/20' : 'border-slate-200'
          }`}>
            <div>
              <div className="h-12 w-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-4 text-2xl">
                ⚖️
              </div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-bold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-100">
                  AVALIADOR / DOCENTE
                </span>
                {role === 'AVALIADOR' && user && (
                  <span className="text-[10px] text-emerald-600 font-bold flex items-center">
                    <CheckCircle2 className="h-3.5 w-3.5 mr-0.5" /> Ativo
                  </span>
                )}
              </div>
              <h4 className="text-base font-bold text-slate-900 mt-2">Prof. Carlos Avaliador</h4>
              <p className="text-xs text-slate-500 mb-3">avaliador@faculdade.edu.br</p>
              
              <ul className="text-xs text-slate-600 space-y-1.5 border-t border-slate-100 pt-3 mb-6">
                <li className="flex items-start">
                  <span className="text-purple-500 mr-1.5 font-bold">•</span>
                  <span>Fila de avaliação dos editais designados</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-500 mr-1.5 font-bold">•</span>
                  <span>Lançamento de notas ponderadas (CR/Prova)</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-500 mr-1.5 font-bold">•</span>
                  <span>Julgamento de recursos com emissão de parecer</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleQuickLogin('AVALIADOR')}
              disabled={isSubmitting}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2.5 px-4 rounded-xl text-xs transition shadow-sm flex items-center justify-center space-x-2"
            >
              {isSubmitting && role === 'AVALIADOR' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Conectar como Avaliador</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </div>

          {/* Card 3: Pró-Reitora */}
          <div className={`bg-white rounded-2xl border p-6 flex flex-col justify-between shadow-sm transition hover:shadow-md ${
            role === 'PRO_REITOR' && user ? 'border-emerald-500 ring-2 ring-emerald-500/20' : 'border-slate-200'
          }`}>
            <div>
              <div className="h-12 w-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4 text-2xl">
                🏛️
              </div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
                  PRÓ-REITORIA / GESTÃO
                </span>
                {role === 'PRO_REITOR' && user && (
                  <span className="text-[10px] text-emerald-600 font-bold flex items-center">
                    <CheckCircle2 className="h-3.5 w-3.5 mr-0.5" /> Ativo
                  </span>
                )}
              </div>
              <h4 className="text-base font-bold text-slate-900 mt-2">Dra. Maria Pró-Reitora</h4>
              <p className="text-xs text-slate-500 mb-3">proreitor@faculdade.edu.br</p>
              
              <ul className="text-xs text-slate-600 space-y-1.5 border-t border-slate-100 pt-3 mb-6">
                <li className="flex items-start">
                  <span className="text-emerald-500 mr-1.5 font-bold">•</span>
                  <span>Cadastrar e publicar editais na vitrine</span>
                </li>
                <li className="flex items-start">
                  <span className="text-emerald-500 mr-1.5 font-bold">•</span>
                  <span>Designar bancas e homologar resultados</span>
                </li>
                <li className="flex items-start">
                  <span className="text-emerald-500 mr-1.5 font-bold">•</span>
                  <span>Auditoria imutável e geração de atas oficiais</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleQuickLogin('PRO_REITOR')}
              disabled={isSubmitting}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 px-4 rounded-xl text-xs transition shadow-sm flex items-center justify-center space-x-2"
            >
              {isSubmitting && role === 'PRO_REITOR' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Conectar como Pró-Reitora</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Formulário de Login com Credenciais Institucionais */}
      <div className="max-w-xl mx-auto bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
        <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-slate-100">
          <div className="p-2 bg-slate-100 rounded-lg text-slate-700">
            <LogIn className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Entrar com Outro E-mail / Matrícula</h3>
            <p className="text-xs text-slate-500">Informe suas credenciais ou selecione seu papel correspondente</p>
          </div>
        </div>

        <form onSubmit={handleCustomLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">E-mail Institucional *</label>
            <input
              type="email"
              required
              placeholder="seu.nome@faculdade.edu.br"
              value={customEmail}
              onChange={(e) => setCustomEmail(e.target.value)}
              className="w-full text-sm px-3.5 py-2.5 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Senha de Acesso</label>
            <input
              type="password"
              placeholder="••••••••"
              value={customPassword}
              onChange={(e) => setCustomPassword(e.target.value)}
              className="w-full text-sm px-3.5 py-2.5 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <p className="text-[11px] text-slate-400 mt-1">Em ambiente de testes/contingência, a senha é simulada.</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Perfil Solicitado</label>
            <select
              value={customRole}
              onChange={(e) => setCustomRole(e.target.value as UserRole)}
              className="w-full text-sm px-3.5 py-2.5 border border-slate-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none text-slate-700"
            >
              <option value="ESTUDANTE">Estudante (Inscrições e Recursos)</option>
              <option value="AVALIADOR">Avaliador (Banca Examinadora)</option>
              <option value="PRO_REITOR">Pró-Reitoria (Gestão Global)</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-xl text-xs transition shadow-sm flex items-center justify-center space-x-2 mt-6"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Autenticando...</span>
              </>
            ) : (
              <>
                <span>Entrar no Sistema QUERO</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>

        {/* Separador SSO */}
        <div className="relative my-6 text-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200"></div>
          </div>
          <span className="relative bg-white px-3 text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
            Ou autentique via
          </span>
        </div>

        <button
          onClick={() => handleQuickLogin('ESTUDANTE')}
          className="w-full bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-300 font-semibold py-2.5 px-4 rounded-xl text-xs transition flex items-center justify-center space-x-2"
        >
          <Building2 className="h-4 w-4 text-blue-600" />
          <span>SSO Institucional (OIDC / SAML 2.0 / Gov.br)</span>
        </button>
      </div>
    </div>
  );
};
