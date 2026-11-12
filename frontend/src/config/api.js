const rawApiUrl = (import.meta.env.VITE_API_URL || '').trim();

// Normalize: remove trailing slash if present
export const API_URL = rawApiUrl
  ? rawApiUrl.replace(/\/+$/, '')
  : (import.meta.env.PROD ? '' : 'http://localhost:8000');

if (import.meta.env.PROD && !rawApiUrl) {
  console.warn(
    '[Fly FILE] Warning: VITE_API_URL environment variable is not defined. ' +
    'Please set VITE_API_URL in your Vercel Project Settings (e.g., https://your-backend.onrender.com).'
  );
}
