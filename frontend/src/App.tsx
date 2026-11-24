import React, { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { CatalogPage } from './pages/CatalogPage';
import { EditalDetailPage } from './pages/EditalDetailPage';
import { MyApplicationsPage } from './pages/MyApplicationsPage';
import { DocumentReviewPage } from './pages/DocumentReviewPage';
import { EvaluationQueuePage } from './pages/EvaluationQueuePage';
import { PreliminaryResultsPage } from './pages/PreliminaryResultsPage';
import { ExecutiveApprovalPage } from './pages/ExecutiveApprovalPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { LoginPage } from './pages/LoginPage';
import { CreateEditalModal } from './components/CreateEditalModal';

export const MainLayout: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<'catalog' | 'detail' | 'my-applications' | 'review' | 'evaluation' | 'results' | 'approval' | 'audit' | 'login'>('catalog');
  const [selectedEditalId, setSelectedEditalId] = useState<number | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSelectEdital = (id: number) => {
    setSelectedEditalId(id);
    setCurrentPage('detail');
  };

  const handleNavigate = (page: string) => {
    setSelectedEditalId(null);
    setCurrentPage(page as any);
  };

  const handleCreateSuccess = () => {
    setRefreshKey((prev) => prev + 1);
    setCurrentPage('catalog');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar 
        onNavigate={handleNavigate} 
        currentPage={currentPage}
        onOpenCreateEdital={() => setIsCreateModalOpen(true)}
      />

      <main className="flex-1">
        {currentPage === 'catalog' && (
          <CatalogPage 
            key={refreshKey}
            onSelectEdital={handleSelectEdital} 
            onOpenCreateEdital={() => setIsCreateModalOpen(true)}
          />
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
        {currentPage === 'login' && (
          <LoginPage 
            onLoginSuccess={() => setCurrentPage('catalog')} 
            onNavigate={handleNavigate} 
          />
        )}
      </main>

      <CreateEditalModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleCreateSuccess}
      />

      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <p className="font-semibold text-slate-700">QUERO &mdash; Quadro Universitário de Estágios Remunerados e Oportunidades</p>
        <p className="mt-1">Sistema Unificado de Seleção e Gestão de Estágios, Monitorias e Bolsas Acadêmicas &middot; v5.0</p>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  );
};

export default App;
