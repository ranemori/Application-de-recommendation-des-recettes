import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { adminAPI } from '../../services/api';
import AdminLayout from '../../components/AdminLayout';
import './AdminDashboard.css';

export default function AdminDashboard() {
  const nav = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    adminAPI.stats()
      .then(setStats)
      .catch(() => setError('Impossible de charger les statistiques.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <AdminLayout>
        <div className="adash-loading"><div className="spinner spinner-lg" /></div>
      </AdminLayout>
    );
  }

  if (error || !stats) {
    return (
      <AdminLayout>
        <div className="adash-error">{error || 'Aucune donnée'}</div>
      </AdminLayout>
    );
  }

  const chartData = (stats.top_recipes || []).map(r => ({
    name: r.title.length > 16 ? r.title.slice(0, 16) + '…' : r.title,
    note: r.note_moyenne || 0,
  }));

  return (
    <AdminLayout>
      <div className="adash-header">
        <h1 className="adash-title">Tableau de bord</h1>
        <p className="adash-sub">Vue d'ensemble du système de recommandation</p>
      </div>

      <div className="adash-stats">
        <div className="adash-stat">
          <span className="adash-stat__icon"></span>
          <div>
            <strong>{stats.total_users}</strong>
            <span>Utilisateurs</span>
          </div>
        </div>
        <div className="adash-stat">
          <span className="adash-stat__icon"></span>
          <div>
            <strong>{stats.active_users_last_30d}</strong>
            <span>Actifs (30j)</span>
          </div>
        </div>
        <div className="adash-stat">
          <span className="adash-stat__icon"></span>
          <div>
            <strong>{stats.total_recipes}</strong>
            <span>Recettes</span>
          </div>
        </div>
        <div className="adash-stat">
          <span className="adash-stat__icon"></span>
          <div>
            <strong>{stats.total_interactions}</strong>
            <span>Interactions (ALS)</span>
          </div>
        </div>
      </div>

      <div className="adash-grid">
        <div className="adash-card">
          <h2 className="adash-card-title">Top recettes</h2>
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 5]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="note" fill="var(--primary)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="adash-card">
          <h2 className="adash-card-title">🆕 Derniers inscrits</h2>
          <ul className="adash-userlist">
            {(stats.recent_users || []).map(u => (
              <li key={u.id} className="adash-userlist__item">
                <div className="adash-userlist__avatar">{u.username[0].toUpperCase()}</div>
                <div className="adash-userlist__info">
                  <strong>{u.username}</strong>
                  <span>{u.email}</span>
                </div>
                <span className={`adash-badge ${u.is_active ? 'adash-badge--active' : 'adash-badge--inactive'}`}>
                  {u.is_active ? 'Actif' : 'Inactif'}
                </span>
              </li>
            ))}
            {(!stats.recent_users || stats.recent_users.length === 0) && (
              <p className="adash-empty">Aucun utilisateur récent.</p>
            )}
          </ul>
          <button className="adash-link" onClick={() => nav('/admin/users')}>Voir tous les utilisateurs</button>
        </div>
      </div>
    </AdminLayout>
  );
}
