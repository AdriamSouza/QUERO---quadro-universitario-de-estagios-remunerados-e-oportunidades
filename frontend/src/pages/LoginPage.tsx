import React, { useState } from 'react';
import { AlertCircle, ArrowRight, GraduationCap, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getErrorMessage } from '../api/client';
import { inputClass } from '../components/ui';

interface LoginPageProps {
  onLoginSuccess: () => void;
}

const formatCpf = (value: string) => {
  const d = value.replace(/\D/g, '').slice(0, 11);
  return d
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1-$2');
};

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const { login, cadastrar } = useAuth();
  const [mode, setMode] = useState<'login' | 'cadastro'>('login');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [matricula, setMatricula] = useState('');
  const [confirmacao, setConfirmacao] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (mode === 'cadastro') {
      if (senha.length < 8) return setError('A senha deve ter pelo menos 8 caracteres.');
      if (senha !== confirmacao) return setError('As senhas não conferem.');
    }
    setSubmitting(true);
    try {
      if (mode === 'login') {
        await login(email.trim(), senha);
      } else {
        await cadastrar({ nome: nome.trim(), email: email.trim(), cpf, matricula: matricula.trim(), senha });
      }
      onLoginSuccess();
    } catch (err) {
      setError(getErrorMessage(err, mode === 'login' ? 'Não foi possível entrar.' : 'Não foi possível concluir o cadastro.'));
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = (m: 'login' | 'cadastro') => {
    setMode(m);
    setError(null);
  };

  return (
    <div className="max-w-md mx-auto px-4 py-12">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center p-3 bg-blue-600 text-white rounded-2xl shadow-md mb-4">
          <GraduationCap className="h-8 w-8" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900">{mode === 'login' ? 'Acesse sua conta' : 'Crie sua conta de estudante'}</h2>
        <p className="mt-2 text-sm text-slate-600">
          {mode === 'login'
            ? 'Entre com seu e-mail institucional e senha.'
            : 'Cadastre-se para se inscrever em editais de estágio, monitoria e bolsas.'}
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm">
        <div className="grid grid-cols-2 border-b border-slate-200 text-sm font-semibold">
          {(['login', 'cadastro'] as const).map((m) => (
            <button
              key={m}
              onClick={() => switchMode(m)}
              className={`py-3 rounded-t-2xl transition ${mode === m ? 'text-blue-700 border-b-2 border-blue-600' : 'text-slate-500 hover:text-slate-800'}`}
            >
              {m === 'login' ? 'Entrar' : 'Cadastrar'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {mode === 'cadastro' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Nome completo</label>
                <input required minLength={3} value={nome} onChange={(e) => setNome(e.target.value)} className={inputClass} autoComplete="name" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">CPF</label>
                  <input required inputMode="numeric" placeholder="000.000.000-00" value={cpf} onChange={(e) => setCpf(formatCpf(e.target.value))} className={inputClass} />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Matrícula</label>
                  <input required value={matricula} onChange={(e) => setMatricula(e.target.value)} className={inputClass} />
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">E-mail</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} autoComplete="email" />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Senha</label>
            <input
              type="password"
              required
              minLength={mode === 'cadastro' ? 8 : 1}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              className={inputClass}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </div>

          {mode === 'cadastro' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Confirme a senha</label>
              <input type="password" required value={confirmacao} onChange={(e) => setConfirmacao(e.target.value)} className={inputClass} autoComplete="new-password" />
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg text-sm flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
            {mode === 'login' ? 'Entrar' : 'Criar conta'}
          </button>

          {mode === 'login' && (
            <p className="text-xs text-slate-500 text-center">
              Esqueceu a senha ou é avaliador sem acesso? Procure a Pró-Reitoria de Graduação.
            </p>
          )}
          {mode === 'cadastro' && (
            <p className="text-xs text-slate-500 text-center">
              Seus dados são usados exclusivamente nos processos seletivos, conforme a LGPD.
            </p>
          )}
        </form>
      </div>
    </div>
  );
};
