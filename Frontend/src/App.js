import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

import ProtectedRoute from './components/ProtectedRoute';

import AuthPage from './pages/auth/AuthPage';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import OnboardingPage from './pages/onboarding/OnboardingPage';
import LandingPage from './pages/LandingPage';

import HomePage from './pages/client/HomePage';
import RecipesPage from './pages/client/RecipesPage';
import RecipeDetailPage from './pages/client/RecipeDetailPage';
import RecommendationsPage from './pages/client/RecommendationsPage';
import FridgePage from './pages/client/FridgePage';
import SavedRecipesPage from './pages/client/SavedRecipesPage';
import SettingsPage from './pages/client/SettingsPage';
import ProfilePage from './pages/client/ProfilePage';

import AdminDashboard from './pages/admin/AdminDashboard';
import AdminUsers from './pages/admin/AdminUsers';
import AdminRecipes from './pages/admin/AdminRecipes';

import Loader from './components/ui/Loader';

function FullScreenLoader() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh',
      background: 'linear-gradient(160deg, #FFF3E8 0%, #FDE8DA 45%, #F7D9C4 100%)',
    }}>
      <Loader label="Préparation de votre expérience culinaire…" />
    </div>
  );
}

/** Redirects an already-authenticated user away from /login or /register */
function PublicOnlyRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (user) {
    if (user.role === 'admin') return <Navigate to="/admin" replace />;
    return <Navigate to={user.onboarding_done ? '/home' : '/onboarding'} replace />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      {/* ── Public ──────────────────────────────────────────── */}
      <Route path="/login" element={<PublicOnlyRoute><AuthPage mode="login" /></PublicOnlyRoute>} />
      <Route path="/register" element={<PublicOnlyRoute><AuthPage mode="register" /></PublicOnlyRoute>} />
      <Route path="/forgot-password" element={<PublicOnlyRoute><ForgotPasswordPage /></PublicOnlyRoute>} />

      {/* ── Onboarding (authenticated, before quiz) ───────────── */}
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute requireOnboarding={false}>
            <OnboardingPage />
          </ProtectedRoute>
        }
      />

      {/* ── Client app ─────────────────────────────────────── */}
      <Route path="/home" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
      <Route path="/recipes" element={<ProtectedRoute><RecipesPage /></ProtectedRoute>} />
      <Route path="/recipe/:id" element={<ProtectedRoute><RecipeDetailPage /></ProtectedRoute>} />
      <Route path="/recommendations" element={<ProtectedRoute><RecommendationsPage /></ProtectedRoute>} />
      <Route path="/fridge" element={<ProtectedRoute><FridgePage /></ProtectedRoute>} />
      <Route path="/saved" element={<ProtectedRoute><SavedRecipesPage /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

      {/* ── Admin app ──────────────────────────────────────── */}
      <Route path="/admin" element={<ProtectedRoute requireAdmin><AdminDashboard /></ProtectedRoute>} />
      <Route path="/admin/users" element={<ProtectedRoute requireAdmin><AdminUsers /></ProtectedRoute>} />
      <Route path="/admin/recipes" element={<ProtectedRoute requireAdmin><AdminRecipes /></ProtectedRoute>} />

      {/* ── Fallback ───────────────────────────────────────── */}
      <Route path="/" element={<LandingPage />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}