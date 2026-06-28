import React, { useState, useEffect } from 'react';
import { recommendAPI } from '../../services/api';
import RecipeCard from '../../components/RecipeCard';
import ClientNavbar from '../../components/ClientNavbar';
import './RecommendationsPage.css';

export default function RecommendationsPage() {
  const [recs, setRecs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [n, setN] = useState(12);
  const [error, setError] = useState('');

  const load = async (count = n) => {
    setLoading(true); setError('');
    try {
      const data = await recommendAPI.forMe(count);
      setRecs(data);
    } catch { setError('Impossible de charger les recommandations.'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const reasonCounts = recs.reduce((acc, r) => {
    acc[r.reason] = (acc[r.reason] || 0) + 1; return acc;
  }, {});

  const REASON_INFO = {
    ALS: { label: 'IA personnalisée', emoji: '', color: '#8B5CF6' },
    popularity: { label: 'Populaire', emoji: '', color: '#F59E0B' },
    content: { label: 'Similaire', emoji: '', color: '#3B82F6' },
    fridge: { label: 'Frigo', emoji: '', color: '#10B981' },
  };

  return (
    <div className="rpage-layout">
      <ClientNavbar />
      <main className="rpage-main">
        {/* Header */}
        <div className="rpage-header">
          <div>
            <h1 className="rpage-title">Mes recommandations</h1>
            <p className="rpage-sub">Recettes selon vos goûts et interactions</p>
          </div>
          <div className="rpage-controls">
            <select className="rpage-select" value={n} onChange={e => { setN(+e.target.value); load(+e.target.value); }}>
              <option value={12}>12 recettes</option>
              <option value={24}>24 recettes</option>
              <option value={36}>36 recettes</option>
            </select>
            <button className="rpage-refresh" onClick={() => load()}>Actualiser</button>
          </div>
        </div>

        {/* Reason pills */}
        {!loading && recs.length > 0 && (
          <div className="rpage-reasons">
            {Object.entries(reasonCounts).map(([reason, count]) => {
              const info = REASON_INFO[reason] || { label: reason, emoji: '•', color: '#666' };
              return (
                <span key={reason} className="rpage-reason-pill" style={{ background: `${info.color}18`, color: info.color, borderColor: `${info.color}35` }}>
                  {info.emoji} {info.label}: {count}
                </span>
              );
            })}
          </div>
        )}

        {/* ALS info banner */}
        <div className="rpage-als-banner">
          <div>
            <strong>Pour vous</strong>
            <span> — Vous consultez, aimez ou notez.</span>
          </div>
        </div>

        {/* Error */}
        {error && <div className="rpage-error">{error}</div>}

        {/* Grid */}
        {loading ? (
          <div className="rpage-grid">
            {Array(12).fill(0).map((_, i) => (
              <div key={i} className="skel-card">
                <div className="skeleton" style={{ height: 190 }} />
                <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '.5rem' }}>
                  <div className="skeleton" style={{ height: 12, width: '60%' }} />
                  <div className="skeleton" style={{ height: 18, width: '90%' }} />
                  <div className="skeleton" style={{ height: 12, width: '70%' }} />
                </div>
              </div>
            ))}
          </div>
        ) : recs.length > 0 ? (
          <div className="rpage-grid">
            {recs.map((r, i) => (
              <div key={r.recipe.id} className="animate-fade" style={{ animationDelay: `${i * 0.04}s` }}>
                <RecipeCard {...r} showReason />
              </div>
            ))}
          </div>
        ) : (
          <div className="rpage-empty">
            <div className="rpage-empty__icon"></div>
            <h3>Aucune recommandation pour l'instant</h3>
            <p>Explorez des recettes et interagissez avec elles pour que nous affichions vos goûts.</p>
          </div>
        )}
      </main>
    </div>
  );
}