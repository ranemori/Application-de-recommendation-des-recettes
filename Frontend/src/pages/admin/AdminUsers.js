import React, { useState, useEffect } from 'react';
import { adminAPI } from '../../services/api';
import AdminLayout from '../../components/AdminLayout';
import './AdminUsers.css';

const TYPE_LABEL = { view: 'Vues', like: 'Aimées', save: 'Sauvegardées', rating: 'Notées' };
const TYPE_TABS = ['view', 'like', 'save', 'rating'];

function UserActivityModal({ user, onClose }) {
  const [tab, setTab] = useState('like');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    adminAPI.userInteractions(user.id, tab)
      .then(setItems)
      .catch(() => setError('Erreur de chargement'))
      .finally(() => setLoading(false));
  }, [user.id, tab]);

  return (
    <div className="auser-activity-backdrop" onClick={onClose}>
      <div className="auser-activity-modal" onClick={e => e.stopPropagation()}>
        <div className="auser-activity-header">
          <div>
            <h2>Activité de {user.username}</h2>
            <p>{user.email}</p>
          </div>
          <button className="auser-activity-close" onClick={onClose}>×</button>
        </div>

        <div className="auser-activity-tabs">
          {TYPE_TABS.map(t => (
            <button
              key={t}
              className={`auser-activity-tab ${tab === t ? 'auser-activity-tab--active' : ''}`}
              onClick={() => setTab(t)}
            >
              {TYPE_LABEL[t]}
            </button>
          ))}
        </div>

        <div className="auser-activity-body">
          {loading ? (
            <div className="ausers-loading"><div className="spinner spinner-lg" /></div>
          ) : error ? (
            <p className="auser-activity-empty">{error}</p>
          ) : items.length === 0 ? (
            <p className="auser-activity-empty">Aucune recette dans cette catégorie.</p>
          ) : (
            <ul className="auser-activity-list">
              {items.map(i => (
                <li
                  key={i.id}
                  className={`auser-activity-item ${(tab === 'like' || tab === 'save') && i.score <= 0 ? 'auser-activity-item--off' : ''}`}
                >
                  <span className="auser-activity-recipe">{i.recipe?.title || `#${i.recipe_id}`}</span>
                  <span className="auser-activity-cuisine">{i.recipe?.cuisine || '—'}</span>
                  {tab === 'rating' && i.score != null && (
                    <span className="auser-activity-score">{Math.round(i.score * 5)}/5</span>
                  )}
                  {(tab === 'like' || tab === 'save') && (
                    <span className={`auser-activity-badge ${i.score > 0 ? 'auser-activity-badge--on' : 'auser-activity-badge--off'}`}>
                      {i.score > 0
                        ? (tab === 'like' ? '+ Aimé' : '+ Sauvegardé')
                        : (tab === 'like' ? '− Retiré' : '− Retiré')}
                    </span>
                  )}
                  <span className="auser-activity-date">{new Date(i.created_at).toLocaleString('fr-FR')}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');
  const [activityUser, setActivityUser] = useState(null);

  const load = () => {
    setLoading(true);
    adminAPI.listUsers().then(setUsers).catch(() => setError('Erreur de chargement')).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const toggleActive = async id => {
    setBusyId(id);
    try {
      const updated = await adminAPI.toggleUser(id);
      setUsers(prev => prev.map(u => (u.id === id ? updated : u)));
    } catch {
      setError('Action impossible');
    } finally {
      setBusyId(null);
    }
  };

  const remove = async id => {
    if (!window.confirm('Supprimer définitivement cet utilisateur ?')) return;
    setBusyId(id);
    try {
      await adminAPI.deleteUser(id);
      setUsers(prev => prev.filter(u => u.id !== id));
    } catch {
      setError('Suppression impossible');
    } finally {
      setBusyId(null);
    }
  };

  const filtered = users.filter(u =>
    u.username.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AdminLayout>
      <div className="ausers-header">
        <div>
          <h1 className="ausers-title">Utilisateurs</h1>
          <p className="ausers-sub">{users.length} compte(s) enregistré(s)</p>
        </div>
        <input
          className="ausers-search"
          placeholder="Rechercher un utilisateur…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {error && <div className="ausers-error">{error}</div>}

      <div className="ausers-table-wrap">
        {loading ? (
          <div className="ausers-loading"><div className="spinner spinner-lg" /></div>
        ) : (
          <table className="ausers-table">
            <thead>
              <tr>
                <th>Utilisateur</th>
                <th>Email</th>
                <th>Rôle</th>
                <th>Région</th>
                <th>Statut</th>
                <th>Inscrit le</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(u => (
                <tr key={u.id}>
                  <td className="ausers-name-cell">
                    <div className="ausers-avatar">{u.username[0].toUpperCase()}</div>
                    {u.username}
                  </td>
                  <td>{u.email}</td>
                  <td><span className={`ausers-role ausers-role--${u.role}`}>{u.role}</span></td>
                  <td>{u.region || u.pays || '—'}</td>
                  <td>
                    <span className={`ausers-status ${u.is_active ? 'ausers-status--active' : 'ausers-status--inactive'}`}>
                      {u.is_active ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  <td>{new Date(u.created_at).toLocaleDateString('fr-FR')}</td>
                  <td className="ausers-actions">
                    <button
                      className="ausers-btn"
                      onClick={() => setActivityUser(u)}
                    >
                      Activité
                    </button>
                    <button
                      className="ausers-btn"
                      disabled={busyId === u.id || u.role === 'admin'}
                      onClick={() => toggleActive(u.id)}
                    >
                      {u.is_active ? 'Désactiver' : 'Activer'}
                    </button>
                    <button
                      className="ausers-btn ausers-btn--danger"
                      disabled={busyId === u.id || u.role === 'admin'}
                      onClick={() => remove(u.id)}
                    >
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="ausers-empty">Aucun utilisateur trouvé.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {activityUser && (
        <UserActivityModal user={activityUser} onClose={() => setActivityUser(null)} />
      )}
    </AdminLayout>
  );
}