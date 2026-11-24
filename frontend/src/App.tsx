import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { CatalogPage } from './pages/CatalogPage';
import { EditalDetailPage } from './pages/EditalDetailPage';
import { MyApplicationsPage } from './pages/MyApplicationsPage';
import { DocumentReviewPage } from './pages/DocumentReviewPage';
import { EvaluationQueuePage } from './pages/EvaluationQueuePage';
import { PreliminaryResultsPage } from './pages/PreliminaryResultsPage';
import { ExecutiveApprovalPage } from './pages/ExecutiveApprovalPage';
import { AuditLogsPage } from './pages/AuditLogsPage';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<'catalog' | 'detail' | 'my-applications' | 'review' | 'evaluation' | 'results' | 'approval' | 'audit'>('catalog');
  const [selectedEditalId, setSelectedEditalId] = useState<number | null>(null);

  const handleSelectEdital = (id: number) => {
    setSelectedEditalId(id);
    setCurrentPage('detail');
  };

  const handleNavigate = (page: string) => {
    setSelectedEditalId(null);
    setCurrentPage(page as any);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar onNavigate={handleNavigate} currentPage={currentPage} />

      <main className="flex-1">
        {currentPage === 'catalog' && (
          <CatalogPage onSelectEdital={handleSelectEdital} />
        )}
        {currentPage === 'detail' && selectedEditalId && (
          <EditalDetailPage 
            editalId={selectedEditalId} 
            onBack={() => setCurrentPage('catalog')} 
          />
        )}
        {currentPage === 'my-applications' && (
          <MyApplicationsPage />
        )}
        {currentPage === 'review' && (
          <DocumentReviewPage />
        )}
        {currentPage === 'evaluation' && (
          <EvaluationQueuePage />
        )}
        {currentPage === 'results' && (
          <PreliminaryResultsPage />
        )}
        {currentPage === 'approval' && (
          <ExecutiveApprovalPage />
        )}
        {currentPage === 'audit' && (
          <AuditLogsPage />
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <p className="font-semibold text-slate-700">QUERO &mdash; Quadro Universitário de Estágios Remunerados e Oportunidades</p>
        <p className="mt-1">Sistema Unificado de Seleção e Gestão de Estágios, Monitorias e Bolsas Acadêmicas &middot; v5.0</p>
      </footer>
    </div>
  );
};

export default App;
