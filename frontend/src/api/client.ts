import axios, { AxiosError } from 'axios';

export const TOKEN_KEY = 'quero_token';
export const SESSION_EXPIRED_EVENT = 'quero:session-expired';

const getBaseUrl = (): string => {
  const envUrl: string | undefined = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (envUrl && envUrl.trim()) {
    let url = envUrl.trim().replace(/\/+$/, '');
    if (!/^https?:\/\//.test(url)) url = `https://${url}`;
    return url.endsWith('/api/v1') ? url : `${url}/api/v1`;
  }
  // Fallback para o deploy padrão no Render quando a variável não foi definida no build
  if (typeof window !== 'undefined' && window.location.hostname.endsWith('.onrender.com')) {
    return 'https://quero-backend.onrender.com/api/v1';
  }
  return 'http://localhost:8000/api/v1';
};

export const apiClient = axios.create({ baseURL: getBaseUrl(), timeout: 60000 });

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const url = error.config?.url || '';
    if (error.response?.status === 401 && localStorage.getItem(TOKEN_KEY) && !url.includes('/auth/login')) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    return Promise.reject(error);
  }
);

/** Extrai uma mensagem legível de erros da API (inclusive erros de validação do FastAPI). */
export const getErrorMessage = (err: unknown, fallback = 'Não foi possível concluir a operação.'): string => {
  const e = err as AxiosError<any>;
  if (!e?.response) {
    return e?.code === 'ECONNABORTED'
      ? 'O servidor demorou para responder. Tente novamente em instantes.'
      : 'Não foi possível conectar ao servidor. Verifique sua conexão.';
  }
  const detail = e.response.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d: any) => String(d?.msg || '').replace(/^Value error, /, ''))
      .filter(Boolean)
      .join(' ');
  }
  return fallback;
};
