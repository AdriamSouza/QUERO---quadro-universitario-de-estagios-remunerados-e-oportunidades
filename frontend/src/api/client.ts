import axios from 'axios';

const getBaseUrl = (): string => {
  // Se estiver rodando no navegador no Render
  if (typeof window !== 'undefined' && window.location.hostname.includes('onrender.com')) {
    return 'https://quero-backend.onrender.com/api/v1';
  }

  const envUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (!envUrl) {
    return 'http://localhost:8000/api/v1';
  }

  let url = envUrl.trim();
  if (url === 'quero-backend' || (!url.includes('.') && !url.startsWith('http'))) {
    url = `https://${url}.onrender.com`;
  }
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = `https://${url}`;
  }
  return url.endsWith('/api/v1') ? url : `${url}/api/v1`;
};

export const apiClient = axios.create({
  baseURL: getBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
