import React, { useState } from 'react';
import { GraduationCap, Users, Shield, PlusCircle, Check, ChevronDown, UserCircle } from 'lucide-react';
import { useAuth, UserRole } from '../context/AuthContext';

interface NavbarProps {
  onNavigate: (page: string, editalId?: number) => void;
  currentPage: string;
  onOpenCreateEdital?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onNavigate, currentPage, onOpenCreateEdital }) => {
  const { user, role, switchProfile, loading } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const roleColors: Record<UserRole, { bg: string; text: string; label: string; icon: string }> = {
    ESTUDANTE: { bg: 'bg-blue-600', text: 'text-blue-100', label: 'Estudante', icon: '🎓' },
    AVALIADOR: { bg: 'bg-purple-600', text: 'text-purple-100', label: 'Avaliador', icon: '⚖️' },
    PRO_REITOR: { bg: 'bg-emerald-600', text: 'text-emerald-100', label: 'Pró-Reitora', icon: '🏛️' },
  };

  const currentBadge = roleColors[role] || roleColors.ESTUDANTE;

  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div 
          className="flex items-center space-x-3 cursor-pointer"
          onClick={() => onNavigate('catalog')}
        >
          <div className="bg-blue-600 p-2 rounded-xl shadow-sm">
            <GraduationCap className="h-6 w-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-tight">QUERO</h1>
              <span className="text-[10px] uppercase font-bold bg-blue-900/60 text-blue-400 px-1.5 py-0.5 rounded border border-blue-700/50">v5.0</span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">Quadro Universitário de Estágios Remunerados e Oportunidades</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center space-x-1 lg:space-x-2">
          <button
            onClick={() => onNavigate('catalog')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              currentPage === 'catalog' 
                ? 'bg-slate-800 text-blue-400 border border-slate-700' 
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            Vitrine
          </button>

          {role === 'ESTUDANTE' && (
            <button
              onClick={() => onNavigate('my-applications')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                currentPage === 'my-applications' 
                  ? 'bg-slate-800 text-blue-400 border border-slate-700' 
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              Minhas Inscrições
            </button>
          )}

          {(role === 'AVALIADOR' || role === 'PRO_REITOR') && (
            <button
              onClick={() => onNavigate('evaluation')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                currentPage === 'evaluation' 
                  ? 'bg-slate-800 text-blue-400 border border-slate-700' 
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              Banca Avaliadora
            </button>
          )}

          <button
            onClick={() => onNavigate('results')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              currentPage === 'results' 
                ? 'bg-slate-800 text-blue-400 border border-slate-700' 
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            Classificação
          </button>

          {role === 'PRO_REITOR' && (
            <>
              <button
                onClick={() => onNavigate('approval')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  currentPage === 'approval' 
                    ? 'bg-slate-800 text-blue-400 border border-slate-700' 
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                Homologação
              </button>

              <button
                onClick={() => onNavigate('audit')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  currentPage === 'audit' 
                    ? 'bg-slate-800 text-blue-400 border border-slate-700' 
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                Auditoria
              </button>
            </>
          )}
        </nav>

        {/* Right Actions: Novo Edital + Profile Switcher */}
        <div className="flex items-center space-x-3">
          {role === 'PRO_REITOR' && onOpenCreateEdital && (
            <button
              onClick={onOpenCreateEdital}
              className="hidden sm:flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition shadow-sm"
            >
              <PlusCircle className="h-4 w-4" />
              <span>Novo Edital</span>
            </button>
          )}

          {/* User Profile Switcher */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700/80 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-medium transition"
            >
              <span className="text-sm">{currentBadge.icon}</span>
              <div className="text-left hidden lg:block">
                <p className="font-semibold text-slate-200 leading-tight">{user?.nome || 'Usuário'}</p>
                <p className="text-[10px] text-slate-400 leading-none">{currentBadge.label}</p>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400 ml-1" />
            </button>

            {dropdownOpen && (
              <div 
                className="absolute right-0 mt-2 w-64 bg-white text-slate-900 rounded-xl shadow-xl border border-slate-200 py-2 z-50 animate-in fade-in slide-in-from-top-1"
                onClick={() => setDropdownOpen(false)}
              >
                <div className="px-4 py-2 border-b border-slate-100">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Simulador de Perfis (RBAC v5.0)</p>
                  <p className="text-xs text-slate-600 mt-0.5">Alterne entre papéis para testar os fluxos regulamentares:</p>
                </div>

                <div className="py-1">
                  <button
                    onClick={() => switchProfile('ESTUDANTE')}
                    className="w-full text-left px-4 py-2.5 text-xs hover:bg-slate-50 flex items-center justify-between transition"
                  >
                    <div className="flex items-center space-x-2.5">
                      <span className="text-base">🎓</span>
                      <div>
                        <p className="font-bold text-slate-800">João Silva</p>
                        <p className="text-[11px] text-slate-500">Estudante (Inscrição & Recurso)</p>
                      </div>
                    </div>
                    {role === 'ESTUDANTE' && <Check className="h-4 w-4 text-blue-600" />}
                  </button>

                  <button
                    onClick={() => switchProfile('AVALIADOR')}
                    className="w-full text-left px-4 py-2.5 text-xs hover:bg-slate-50 flex items-center justify-between transition"
                  >
                    <div className="flex items-center space-x-2.5">
                      <span className="text-base">⚖️</span>
                      <div>
                        <p className="font-bold text-slate-800">Prof. Carlos</p>
                        <p className="text-[11px] text-slate-500">Avaliador (Banca & Pareceres)</p>
                      </div>
                    </div>
                    {role === 'AVALIADOR' && <Check className="h-4 w-4 text-purple-600" />}
                  </button>

                  <button
                    onClick={() => switchProfile('PRO_REITOR')}
                    className="w-full text-left px-4 py-2.5 text-xs hover:bg-slate-50 flex items-center justify-between transition"
                  >
                    <div className="flex items-center space-x-2.5">
                      <span className="text-base">🏛️</span>
                      <div>
                        <p className="font-bold text-slate-800">Dra. Maria</p>
                        <p className="text-[11px] text-slate-500">Pró-Reitora (Gestão & Homologação)</p>
                      </div>
                    </div>
                    {role === 'PRO_REITOR' && <Check className="h-4 w-4 text-emerald-600" />}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
