import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function FullScreenLoader() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', background: 'var(--bg)'
    }}>
      <div className="spinner spinner-lg" />
    </div>
  );
}

/**
 * Guards a route behind authentication.
 * - requireAdmin: only role === 'admin' may pass
 * - requireOnboarding: redirects non-onboarded users to /onboarding
 */
export default function ProtectedRoute({ children, requireAdmin = false, requireOnboarding = true }) {
  const { user, loading } = useAuth();

  if (loading) return <FullScreenLoader />;

  if (!user) return <Navigate to="/login" replace />;

  if (requireAdmin && user.role !== 'admin') {
    return <Navigate to="/home" replace />;
  }

  if (!requireAdmin && requireOnboarding && !user.onboarding_done) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}
