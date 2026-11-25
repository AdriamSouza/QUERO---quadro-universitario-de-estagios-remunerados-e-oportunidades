import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('Erro inesperado na interface:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 shadow-sm p-6 text-center">
            <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto mb-3" />
            <h1 className="text-lg font-bold text-slate-900">Algo deu errado</h1>
            <p className="text-sm text-slate-600 mt-1">
              Ocorreu um erro inesperado ao exibir esta tela. Recarregue a página para continuar.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-5 inline-flex items-center px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition"
            >
              <RotateCcw className="h-4 w-4 mr-1.5" />
              Recarregar página
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
