import axios from 'axios';

const getBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (!envUrl) {
    return 'http://localhost:8000/api/v1';
  }
  if (envUrl.startsWith('http://') || envUrl.startsWith('https://')) {
    return envUrl.endsWith('/api/v1') ? envUrl : `${envUrl}/api/v1`;
  }
  return `https://${envUrl}/api/v1`;
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
