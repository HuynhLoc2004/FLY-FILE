const productionApiUrl = 'https://flyfile-backend-production-4bb2.up.railway.app';

export const API_URL = import.meta.env.VITE_API_URL || (
  import.meta.env.PROD ? productionApiUrl : 'http://localhost:8000'
);
