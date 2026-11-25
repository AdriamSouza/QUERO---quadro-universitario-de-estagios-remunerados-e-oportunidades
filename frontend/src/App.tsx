import React, { useEffect, useState } from 'react';
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router-dom';
import { AuthProvider, useAuth, UserRole } from './context/AuthContext';
import { ToastProvider, useToast } from './components/Toast';
import { Navbar } from './components/Navbar';
import { CreateEditalModal } from './components/CreateEditalModal';
import { ErrorBoundary } from './components/ErrorBoundary';
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

const PAGE_PATHS: Record<Exclude<Page, 'detail'>, string> = {
  catalog: '/',
  login: '/entrar',
  'my-applications': '/minhas-inscricoes',
  review: '/analise-documental',
  evaluation: '/avaliacoes',
  results: '/resultados',
  approval: '/homologacao',
  audit: '/auditoria',
  users: '/usuarios',
};

function getPageFromPathname(pathname: string): Page {
  if (pathname.startsWith('/editais/')) return 'detail';
  const entry = Object.entries(PAGE_PATHS).find(([, path]) => path === pathname);
  return (entry?.[0] as Page) || 'catalog';
}

const ProtectedRoute: React.FC<{
  roles?: UserRole[];
  children: React.ReactElement;
}> = ({ roles, children }) => {
  const { user, role, loading } = useAuth();
  const location = useLocation();
  const routerNavigate = useNavigate();

  if (loading) return <Spinner label="Carregando..." />;
  if (roles && !user) {
    return <Navigate to={PAGE_PATHS.login} state={{ from: location.pathname }} replace />;
  }
  if (roles && user && role && !roles.includes(role)) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center px-4">
        <h2 className="text-xl font-bold text-slate-900">Acesso restrito</h2>
        <p className="text-sm text-slate-600 mt-2">Seu perfil não tem acesso a esta área.</p>
        <button onClick={() => routerNavigate(PAGE_PATHS.catalog)} className="mt-6 text-blue-600 font-semibold text-sm">
          Voltar para os editais
        </button>
      </div>
    );
  }
  return children;
};

const EditalDetailRoute: React.FC<{ onNavigate: (page: Page) => void }> = ({ onNavigate }) => {
  const { id } = useParams<{ id: string }>();
  const editalId = Number(id);
  if (!id || !Number.isInteger(editalId) || editalId <= 0) {
    return <Navigate to={PAGE_PATHS.catalog} replace />;
  }
  return <EditalDetailPage editalId={editalId} onBack={() => onNavigate('catalog')} onNavigate={onNavigate} />;
};

const LoginRoute: React.FC = () => {
  const { loading } = useAuth();
  const location = useLocation();
  const routerNavigate = useNavigate();

  if (loading) return <Spinner label="Carregando..." />;
  const from = (location.state as { from?: string } | null)?.from || PAGE_PATHS.catalog;

  return (
    <LoginPage
      onLoginSuccess={() => {
        routerNavigate(from, { replace: true });
      }}
    />
  );
};

export const MainLayout: React.FC = () => {
  const { sessionExpired } = useAuth();
  const toast = useToast();
  const location = useLocation();
  const routerNavigate = useNavigate();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const currentPage = getPageFromPathname(location.pathname);

  useEffect(() => {
    if (sessionExpired) {
      toast.info('Sua sessão expirou. Entre novamente para continuar.');
      routerNavigate(PAGE_PATHS.login, { state: { from: location.pathname }, replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionExpired]);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  const navigateToPage = (page: Page) => {
    if (page === 'detail') {
      routerNavigate(PAGE_PATHS.catalog);
      return;
    }
    routerNavigate(PAGE_PATHS[page]);
  };

  const handleSelectEdital = (id: number) => {
    routerNavigate(`/editais/${id}`);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        onNavigate={(p) => navigateToPage(p as Page)}
        currentPage={currentPage}
        onOpenCreateEdital={() => setIsCreateModalOpen(true)}
      />

      <main className="flex-1">
        <Routes>
          <Route
            path={PAGE_PATHS.catalog}
            element={
              <CatalogPage
                key={refreshKey}
                onSelectEdital={handleSelectEdital}
                onOpenCreateEdital={() => setIsCreateModalOpen(true)}
              />
            }
          />
          <Route path="/editais/:id" element={<EditalDetailRoute onNavigate={navigateToPage} />} />
          <Route path={PAGE_PATHS.login} element={<LoginRoute />} />
          <Route
            path={PAGE_PATHS['my-applications']}
            element={
              <ProtectedRoute roles={['ESTUDANTE']}>
                <MyApplicationsPage onSelectEdital={handleSelectEdital} />
              </ProtectedRoute>
            }
          />
          <Route
            path={PAGE_PATHS.review}
            element={
              <ProtectedRoute roles={['PRO_REITOR']}>
                <DocumentReviewPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={PAGE_PATHS.evaluation}
            element={
              <ProtectedRoute roles={['AVALIADOR', 'PRO_REITOR']}>
                <EvaluationQueuePage />
              </ProtectedRoute>
            }
          />
          <Route path={PAGE_PATHS.results} element={<PreliminaryResultsPage />} />
          <Route
            path={PAGE_PATHS.approval}
            element={
              <ProtectedRoute roles={['PRO_REITOR']}>
                <ExecutiveApprovalPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={PAGE_PATHS.audit}
            element={
              <ProtectedRoute roles={['PRO_REITOR']}>
                <AuditLogsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path={PAGE_PATHS.users}
            element={
              <ProtectedRoute roles={['PRO_REITOR']}>
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to={PAGE_PATHS.catalog} replace />} />
        </Routes>
      </main>

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
  <ErrorBoundary>
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <MainLayout />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  </ErrorBoundary>
);

export default App;
