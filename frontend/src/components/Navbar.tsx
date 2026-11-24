import React from 'react';
import { GraduationCap, BookOpen, User, LogIn, FileText, CheckSquare } from 'lucide-react';

interface NavbarProps {
  onNavigate: (page: string, editalId?: number) => void;
  currentPage: string;
}

export const Navbar: React.FC<NavbarProps> = ({ onNavigate, currentPage }) => {
  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div 
          className="flex items-center space-x-3 cursor-pointer"
          onClick={() => onNavigate('catalog')}
        >
          <div className="bg-blue-600 p-2 rounded-lg">
            <GraduationCap className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">QUERO</h1>
            <p className="text-xs text-slate-400">Quadro Universitário de Estágios Remunerados e Oportunidades</p>
          </div>
        </div>

        <nav className="flex items-center space-x-2 sm:space-x-4">
          <button
            onClick={() => onNavigate('catalog')}
            className={`px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition ${
              currentPage === 'catalog' 
                ? 'bg-slate-800 text-blue-400' 
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            Vitrine
          </button>

          <button
            onClick={() => onNavigate('my-applications')}
            className={`px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition ${
              currentPage === 'my-applications' 
                ? 'bg-slate-800 text-blue-400' 
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            Minhas Inscrições
          </button>

          <button
            onClick={() => onNavigate('evaluation')}
            className={`px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition ${
              currentPage === 'evaluation' 
                ? 'bg-slate-800 text-blue-400' 
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            Avaliação
          </button>

          <button
            onClick={() => onNavigate('results')}
            className={`px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition ${
              currentPage === 'results' 
                ? 'bg-slate-800 text-blue-400' 
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            Classificação
          </button>

          <button
            onClick={() => onNavigate('approval')}
            className={`px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition ${
              currentPage === 'approval' 
                ? 'bg-slate-800 text-blue-400' 
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            Homologação
          </button>

          <button
            onClick={() => onNavigate('audit')}
            className={`px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition ${
              currentPage === 'audit' 
                ? 'bg-slate-800 text-blue-400' 
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            Auditoria
          </button>
        </nav>
      </div>
    </header>
  );
};
