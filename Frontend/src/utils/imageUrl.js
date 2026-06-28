

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
// Strip the trailing "/api/v1" (or similar) to get just the backend's origin.
const BACKEND_ORIGIN = API_BASE.replace(/\/api\/v\d+\/?$/, '');

export function resolveImageUrl(url) {
  if (!url) return url;
  if (/^https?:\/\//i.test(url)) return url; // already absolute
  return `${BACKEND_ORIGIN}${url.startsWith('/') ? '' : '/'}${url}`;
}