import React, { useState, useEffect } from 'react';
import { recipeAPI } from '../../services/api';
import RecipeCard from '../../components/RecipeCard';
import ClientNavbar from '../../components/ClientNavbar';
import './RecipesPage.css';

const CUISINES_FILTER = [
  'Toutes', 'Marocaine', 'Française', 'Italienne', 'Japonaise', 'Mexicaine',
  'Libanaise', 'Indienne', 'Américaine', 'Chinoise', 'Espagnole', 'Turque',
  'Thaïlandaise', 'Coréenne', 'Grecque', 'Hawaïenne', 'Indonésienne',
  'Malaisienne', 'Moyen-orientale', 'Peruvienne', 'Russe', 'Venezuelienne',
  'Vietnamienne',
];
const DIFF_FILTER = ['Tous', 'facile', 'moyen', 'difficile'];
const REGIME_FILTER = ['Tous', 'normal', 'végétarien', 'végétalien', 'sans gluten'];

export default function RecipesPage() {
  const [all, setAll] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [cuisine, setCuisine] = useState('Toutes');
  const [diff, setDiff] = useState('Tous');
  const [regime, setRegime] = useState('Tous');
  const [sortBy, setSortBy] = useState('note');

  useEffect(() => {
    recipeAPI.list().then(d => {
      setAll(d); setFiltered(d);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let res = [...all];
    if (search) res = res.filter(r => r.title.toLowerCase().includes(search.toLowerCase()) || (r.description || '').toLowerCase().includes(search.toLowerCase()));
    if (cuisine !== 'Toutes') res = res.filter(r => (r.cuisine || '').toLowerCase() === cuisine.toLowerCase());
    if (diff !== 'Tous') res = res.filter(r => r.difficulte === diff);
    if (regime !== 'Tous') res = res.filter(r => r.regime === regime);
    if (sortBy === 'note') res.sort((a, b) => (b.note_moyenne || 0) - (a.note_moyenne || 0));
    else if (sortBy === 'time') res.sort((a, b) => (a.temps_preparation || 999) - (b.temps_preparation || 999));
    else if (sortBy === 'recent') res.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    setFiltered(res);
  }, [all, search, cuisine, diff, regime, sortBy]);

  const reset = () => { setSearch(''); setCuisine('Toutes'); setDiff('Tous'); setRegime('Tous'); setSortBy('note'); };

  return (
    <div className="rlist-layout">
      <ClientNavbar />
      <main className="rlist-main">
        <div className="rlist-header">
          <h1 className="rlist-title">Toutes les recettes</h1>
          <p className="rlist-sub">{filtered.length} recette(s) disponible(s)</p>
        </div>

        {/* Filters */}
        <div className="rlist-filters">
          <div className="rlist-search-wrap">
            <span></span>
            <input className="rlist-search" placeholder="Rechercher une recette…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>

          <div className="rlist-filter-row">
            <div className="rlist-filter-group">
              <label>Cuisine</label>
              <select value={cuisine} onChange={e => setCuisine(e.target.value)}>
                {CUISINES_FILTER.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div className="rlist-filter-group">
              <label>Difficulté</label>
              <select value={diff} onChange={e => setDiff(e.target.value)}>
                {DIFF_FILTER.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div className="rlist-filter-group">
              <label>Régime</label>
              <select value={regime} onChange={e => setRegime(e.target.value)}>
                {REGIME_FILTER.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
            <div className="rlist-filter-group">
              <label>Trier par</label>
              <select value={sortBy} onChange={e => setSortBy(e.target.value)}>
                <option value="note">Mieux notées</option>
                <option value="time">Temps de préparation</option>
                <option value="recent">Plus récentes</option>
              </select>
            </div>
            <button className="rlist-reset" onClick={reset}>Réinitialiser</button>
          </div>
        </div>

        {/* Cuisine tabs */}
        <div className="rlist-cuisine-tabs">
          {CUISINES_FILTER.map(c => (
            <button key={c} className={`rlist-ctab ${cuisine === c ? 'rlist-ctab--active' : ''}`} onClick={() => setCuisine(c)}>{c}</button>
          ))}
        </div>

        {/* Grid */}
        {loading ? (
          <div className="rlist-grid">
            {Array(12).fill(0).map((_, i) => (
              <div key={i} className="skel-card">
                <div className="skeleton" style={{ height: 190 }} />
                <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '.5rem' }}>
                  <div className="skeleton" style={{ height: 12, width: '60%' }} />
                  <div className="skeleton" style={{ height: 18 }} />
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length > 0 ? (
          <div className="rlist-grid">
            {filtered.map((r, i) => (
              <div key={r.id} className="animate-fade" style={{ animationDelay: `${Math.min(i * 0.03, 0.5)}s` }}>
                <RecipeCard recipe={r} />
              </div>
            ))}
          </div>
        ) : (
          <div className="rlist-empty">
            <span></span>
            <p>Aucune recette ne correspond à vos critères.</p>
            <button className="rlist-reset-btn" onClick={reset}>Réinitialiser les filtres</button>
          </div>
        )}
      </main>
    </div>
  );
}