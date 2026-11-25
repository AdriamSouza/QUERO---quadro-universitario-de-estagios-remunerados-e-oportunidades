import React, { useEffect, useState } from 'react';
import { AuthProvider, useAuth, UserRole } from './context/AuthContext';
import { ToastProvider, useToast } from './components/Toast';
import { Navbar } from './components/Navbar';
import { CreateEditalModal } from './components/CreateEditalModal';
import { Spinner } from './components/ui';
import { CatalogPage } from './pages/CatalogPage';
import { EditalDetailPage } from './pages/EditalDetailPage';
import { MyApplicationsPage } from './pages/MyApplicationsPage';
import { DocumentReviewPage } from './pages/DocumentReviewPage';
import { EvaluationQueuePage } from './pages/EvaluationQueuePage';
import { PreliminaryResultsPage } from './pages/PreliminaryResultsPage';
import { ExecutiveApprovalPage } from './pages/ExecutiveApprovalPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { UsersPage } from './pages/UsersPage';
import { LoginPage } from './pages/LoginPage';

export type Page =
  | 'catalog' | 'detail' | 'login' | 'my-applications' | 'review' | 'evaluation'
  | 'results' | 'approval' | 'audit' | 'users';

/** Perfis exigidos por página. Páginas ausentes são públicas. */
const PAGE_ROLES: Partial<Record<Page, UserRole[]>> = {
  'my-applications': ['ESTUDANTE'],
  review: ['PRO_REITOR'],
  evaluation: ['AVALIADOR', 'PRO_REITOR'],
  approval: ['PRO_REITOR'],
  audit: ['PRO_REITOR'],
  users: ['PRO_REITOR'],
};

export const MainLayout: React.FC = () => {
  const { user, role, loading, sessionExpired } = useAuth();
  const toast = useToast();
  const [currentPage, setCurrentPage] = useState<Page>('catalog');
  const [pendingPage, setPendingPage] = useState<Page | null>(null);
  const [selectedEditalId, setSelectedEditalId] = useState<number | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (sessionExpired) {
      toast.info('Sua sessão expirou. Entre novamente para continuar.');
      setCurrentPage('login');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionExpired]);

  const navigate = (page: Page) => {
    const required = PAGE_ROLES[page];
    if (required && !user) {
      setPendingPage(page);
      setCurrentPage('login');
    } else {
      setCurrentPage(page);
    }
    window.scrollTo({ top: 0 });
  };

  const handleSelectEdital = (id: number) => {
    setSelectedEditalId(id);
    setCurrentPage('detail');
    window.scrollTo({ top: 0 });
  };

  const required = PAGE_ROLES[currentPage];
  const forbidden = !!(required && user && role && !required.includes(role));
  const needsLogin = !!(required && !user);

  const renderPage = () => {
    if (loading) return <Spinner label="Carregando..." />;
    if (needsLogin || currentPage === 'login') {
      return (
        <LoginPage
          onLoginSuccess={() => {
            const target = pendingPage;
            setPendingPage(null);
            setCurrentPage(target || 'catalog');
          }}
        />
      );
    }
    if (forbidden) {
      return (
        <div className="max-w-xl mx-auto py-20 text-center px-4">
          <h2 className="text-xl font-bold text-slate-900">Acesso restrito</h2>
          <p className="text-sm text-slate-600 mt-2">Seu perfil não tem acesso a esta área.</p>
          <button onClick={() => navigate('catalog')} className="mt-6 text-blue-600 font-semibold text-sm">Voltar para os editais</button>
        </div>
      );
    }
    switch (currentPage) {
      case 'detail':
        return selectedEditalId ? (
          <EditalDetailPage editalId={selectedEditalId} onBack={() => navigate('catalog')} onNavigate={navigate} />
        ) : null;
      case 'my-applications':
        return <MyApplicationsPage onSelectEdital={handleSelectEdital} />;
      case 'review':
        return <DocumentReviewPage />;
      case 'evaluation':
        return <EvaluationQueuePage />;
      case 'results':
        return <PreliminaryResultsPage />;
      case 'approval':
        return <ExecutiveApprovalPage />;
      case 'audit':
        return <AuditLogsPage />;
      case 'users':
        return <UsersPage />;
      default:
        return (
          <CatalogPage
            key={refreshKey}
            onSelectEdital={handleSelectEdital}
            onOpenCreateEdital={() => setIsCreateModalOpen(true)}
          />
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        onNavigate={(p) => navigate(p as Page)}
        currentPage={currentPage}
        onOpenCreateEdital={() => setIsCreateModalOpen(true)}
      />

      <main className="flex-1">{renderPage()}</main>

      <CreateEditalModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={(id) => {
          setRefreshKey((prev) => prev + 1);
          handleSelectEdital(id);
        }}
      />

      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <p className="font-semibold text-slate-700">QUERO — Quadro Universitário de Estágios Remunerados e Oportunidades</p>
        <p className="mt-1">Seleção de estágios, monitorias e bolsas acadêmicas · Pró-Reitoria de Graduação</p>
      </footer>
    </div>
  );
};

export const App: React.FC = () => (
  <ToastProvider>
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  </ToastProvider>
);

export default App;
