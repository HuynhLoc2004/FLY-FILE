let rawApiUrl = (import.meta.env.VITE_API_URL || '').trim();

// Automatic fallback from obsolete Railway deployment to live Render backend
if (rawApiUrl.includes('railway.app')) {
  rawApiUrl = 'https://fly-file-backend.onrender.com';
}

// Normalize: remove trailing slash if present
// In production, fallback directly to the deployed Render backend
export const API_URL = rawApiUrl
  ? rawApiUrl.replace(/\/+$/, '')
  : (import.meta.env.PROD ? 'https://fly-file-backend.onrender.com' : 'http://localhost:8000');

/**
 * Robust fetch wrapper that automatically retries on network drop or Render free-tier cold-start
 */
export async function apiFetch(url, options = {}, retries = 2, delayMs = 2500) {
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(url, options);
      return response;
    } catch (err) {
      lastError = err;
      const isNetworkError =
        err?.name === 'TypeError' ||
        err?.message?.includes('Failed to fetch') ||
        err?.message?.includes('NetworkError') ||
        err?.message?.includes('Load failed');
      if (isNetworkError && attempt < retries) {
        // Wait for server spin-up / transient network glitch to settle
        await new Promise((r) => setTimeout(r, delayMs * (attempt + 1)));
        continue;
      }
      throw err;
    }
  }
  throw lastError;
}

export function formatErrorMessage(err) {
  if (!err) return 'Lỗi không xác định';
  const msg = typeof err === 'string' ? err : err.message || '';
  if (
    msg === 'Failed to fetch' ||
    msg.includes('Failed to fetch') ||
    msg.includes('NetworkError') ||
    msg.includes('Load failed')
  ) {
    return 'Máy chủ đang khởi động hoặc mất kết nối mạng tạm thời. Vui lòng nhấn "Thử lại".';
  }
  return msg;
}

