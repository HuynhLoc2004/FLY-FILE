const rawApiUrl = (import.meta.env.VITE_API_URL || '').trim();

// Normalize: remove trailing slash if present
// In production, fallback directly to the deployed Render backend
export const API_URL = rawApiUrl
  ? rawApiUrl.replace(/\/+$/, '')
  : (import.meta.env.PROD ? 'https://fly-file-backend.onrender.com' : 'http://localhost:8000');
