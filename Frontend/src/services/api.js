import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({ baseURL: BASE, timeout: 15000 });

/* ── Auth token injection ─────────────────────────────────────── */
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

/* ── Auto-refresh on 401 ──────────────────────────────────────── */
const AUTH_ENDPOINTS = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/change-password'];

api.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config;
    const isAuthEndpoint = AUTH_ENDPOINTS.some(p => original?.url?.includes(p));

    if (isAuthEndpoint) {
      return Promise.reject(err);
    }

    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      const rt = localStorage.getItem('refresh_token');
      if (rt) {
        try {
          const { data } = await axios.post(`${BASE}/auth/refresh`, { refresh_token: rt });
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(err);
  }
);

/* ── Auth ─────────────────────────────────────────────────────── */
export const authAPI = {
  register : d => api.post('/auth/register', d).then(r => r.data),
  login : d => api.post('/auth/login', d).then(r => r.data),
  refresh : d => api.post('/auth/refresh', d).then(r => r.data),
  changePassword : d => api.post('/auth/change-password', d).then(r => r.data),
  forgotPassword : email => api.post('/auth/forgot-password', { email }).then(r => r.data),
  resetPassword : (token, new_password) => api.post('/auth/reset-password', { token, new_password }).then(r => r.data),
};

/* ── Notifications ─────────────────────────────────────────────── */
export const notificationAPI = {
  list : () => api.get('/notifications/me').then(r => r.data),
  unreadCount : () => api.get('/notifications/me/unread-count').then(r => r.data),
  markRead : id => api.post(`/notifications/${id}/read`).then(r => r.data),
  markAllRead : () => api.post('/notifications/me/read-all').then(r => r.data),
};

/* ── Users ────────────────────────────────────────────────────── */
export const userAPI = {
  me : () => api.get('/users/me').then(r => r.data),
  update : d => api.patch('/users/me', d).then(r => r.data),
  onboarding : d => api.post('/users/onboarding', d).then(r => r.data),
  getFridge : () => api.get('/users/fridge').then(r => r.data),
  setFridge : d => api.put('/users/fridge', d).then(r => r.data),
  removeFridge: id => api.delete(`/users/fridge/${id}`).then(r => r.data),
  saved : () => api.get('/users/me/saved').then(r => r.data),
  uploadAvatar : file => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/users/me/avatar', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data);
  },
  deactivate : () => api.post('/users/me/deactivate').then(r => r.data),
};

/* ── Recipes ──────────────────────────────────────────────────── */
export const recipeAPI = {
  list : () => api.get('/recipes/').then(r => r.data),
  detail: id => api.get(`/recipes/${id}`).then(r => r.data),
};

/* ── Recommendations ──────────────────────────────────────────── */
export const recommendAPI = {
  forMe : (n=12) => api.get(`/recommendations/me?n=${n}`).then(r => r.data),
  myFridge : (strict=true) => api.get(`/recommendations/my-fridge?strict=${strict}`).then(r => r.data),
  fridge : d => api.post('/recommendations/fridge', d).then(r => r.data),
  similar : (id, n=6) => api.get(`/recommendations/similar/${id}?n=${n}`).then(r => r.data),
};

/* ── Ingredients ──────────────────────────────────────────────── */
export const ingredientAPI = {
  list : (search='', limit=50) => api.get(`/ingredients/?search=${search}&limit=${limit}`).then(r => r.data),
};

/* ── Interactions ─────────────────────────────────────────────── */
export const interactionAPI = {
  add: d => api.post('/interactions/', d).then(r => r.data),
};

/* ── Comments ─────────────────────────────────────────────────── */
export const commentAPI = {
  list   : recipeId => api.get(`/comments/recipe/${recipeId}`).then(r => r.data),
  add    : (recipeId, content) => api.post('/comments/', { recipe_id: recipeId, content }).then(r => r.data),
  remove : commentId => api.delete(`/comments/${commentId}`).then(r => r.data),
};

/* ── Admin ────────────────────────────────────────────────────── */
export const adminAPI = {
  stats : () => api.get('/admin/stats').then(r => r.data),
  listUsers : () => api.get('/admin/users').then(r => r.data),
  toggleUser : id => api.patch(`/admin/users/${id}/toggle-active`).then(r => r.data),
  deleteUser : id => api.delete(`/admin/users/${id}`).then(r => r.data),
  listRecipes : () => api.get('/admin/recipes').then(r => r.data),
  createRecipe : d => api.post('/admin/recipes', d).then(r => r.data),
  updateRecipe : (id, d) => api.patch(`/admin/recipes/${id}`, d).then(r => r.data),
  deleteRecipe : id => api.delete(`/admin/recipes/${id}`).then(r => r.data),
  listIngredients : () => api.get('/admin/ingredients-all').then(r => r.data),
  userInteractions : (id, type) => api.get(`/admin/users/${id}/interactions`, { params: type ? { interaction_type: type } : {} }).then(r => r.data),
};

export default api;