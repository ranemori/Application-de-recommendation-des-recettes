import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { recommendAPI, recipeAPI } from '../../services/api';
import RecipeCard from '../../components/RecipeCard';
import ClientNavbar from '../../components/ClientNavbar';
import AnimatedPenguin from '../../components/AnimatedPenguin';
import './HomePage.css';

function SkeletonCard() {
  return (
    <div className="skel-card">
      <div className="skeleton" style={{ height: 190 }} />
      <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '.5rem' }}>
        <div className="skeleton" style={{ height: 12, width: '60%' }} />
        <div className="skeleton" style={{ height: 18, width: '90%' }} />
        <div className="skeleton" style={{ height: 14, width: '75%' }} />
      </div>
    </div>
  );
}

export default function HomePage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [recs, setRecs] = useState([]);
  const [popular, setPopular] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      recommendAPI.forMe(8).catch(() => []),
      recipeAPI.list().catch(() => []),
    ]).then(([r, all]) => {
      setRecs(r);
      setPopular(all.sort((a, b) => (b.note_moyenne || 0) - (a.note_moyenne || 0)).slice(0, 8));
    }).finally(() => setLoading(false));
  }, []);

  const cuisinePrefs = user?.preferences_cuisine || [];

  return (
    <div className="home-layout">
      <ClientNavbar />
      <main className="home-main">
        {/* Hero */}
        <section className="home-hero">
          <div className="home-hero__inner">
            <div className="home-hero__text">
              <h1 className="home-hero__title">
                Bonjour, <span className="home-hero__name">{user?.username}</span>
              </h1>
              <p className="home-hero__sub">
                {cuisinePrefs.length > 0
                  ? `Basé sur vos goûts pour la cuisine ${cuisinePrefs[0]}, voici vos recommandations du jour.`
                  : 'Découvrez des recettes personnalisées grâce à notre IA de recommandation.'}
              </p>
              <div className="home-hero__actions">
                <div className="entry-btn-container entry-btn-container--inline">
                  <button className="entry-btn entry-btn--primary" onClick={() => nav('/recommendations')}>
                    <span className="entry-btn__line"></span>
                    <span className="entry-btn__line"></span>
                    <span className="entry-btn__text">Mes recommandations</span>
                    <span className="entry-btn__drow1"></span>
                    <span className="entry-btn__drow2"></span>
                  </button>
                  <button className="entry-btn entry-btn--secondary" onClick={() => nav('/fridge')}>
                    <span className="entry-btn__line"></span>
                    <span className="entry-btn__line"></span>
                    <span className="entry-btn__text">Mon frigo</span>
                    <span className="entry-btn__drow1"></span>
                    <span className="entry-btn__drow2"></span>
                  </button>
                </div>
              </div>
            </div>
            <div className="home-hero__badges">
              {cuisinePrefs.slice(0, 4).map(c => (
                <span key={c} className="home-hero__badge">{c}</span>
              ))}
              {user?.regime_alimentaire && user.regime_alimentaire !== 'normal' && (
                <span className="home-hero__badge home-hero__badge--regime">{user.regime_alimentaire}</span>
              )}
            </div>
          </div>
          <div className="home-hero__burger-slot">
            <AnimatedPenguin />
          </div>
        </section>

        {/* Quick stats */}
        <section className="home-stats">
          <div className="home-stat">
            <span className="home-stat__icon"></span>
            <div><strong>Recommandé par IA</strong><span>Modèle ALS personnalisé</span></div>
          </div>
          <div className="home-stat">
            <span className="home-stat__icon"></span>
            <div><strong>Frigo intelligent</strong><span>Recettes selon vos ingrédients</span></div>
          </div>
          <div className="home-stat">
            <span className="home-stat__icon"></span>
            <div><strong>Cuisines du monde</strong><span>Des milliers de recettes</span></div>
          </div>
        </section>

        {/* Personalized recs */}
        <section className="home-section">
          <div className="home-section__header">
            <h2 className="home-section__title">Rien que pour vous</h2>
            <button className="home-section__more" onClick={() => nav('/recommendations')}>Voir tout</button>
          </div>
          <div className="home-grid">
            {loading
              ? Array(4).fill(0).map((_, i) => <SkeletonCard key={i} />)
              : recs.length > 0
                ? recs.slice(0, 4).map(r => <RecipeCard key={r.recipe.id} {...r} showReason />)
                : <p className="home-empty">Aucune recommandation pour l'instant. Explorez des recettes !</p>
            }
          </div>
        </section>

        {/* Popular */}
        <section className="home-section">
          <div className="home-section__header">
            <h2 className="home-section__title">Tendances du moment</h2>
            <button className="home-section__more" onClick={() => nav('/recipes')}>Voir tout</button>
          </div>
          <div className="home-grid">
            {loading
              ? Array(4).fill(0).map((_, i) => <SkeletonCard key={i} />)
              : popular.slice(0, 4).map(r => <RecipeCard key={r.id} recipe={r} />)
            }
          </div>
        </section>

        {/* Fridge CTA */}
        <section className="home-fridge-cta">
          <div className="home-fridge-cta__inner">
            <div>
              <h3 className="home-fridge-cta__title">Qu'est-ce qu'il y a dans votre frigo ?</h3>
              <p className="home-fridge-cta__desc">
                Entrez vos ingrédients disponibles et découvrez des recettes que vous pouvez préparer maintenant, sans aller faire les courses.
              </p>
            </div>
            <button className="home-fridge-cta__btn" onClick={() => nav('/fridge')}>
              Ouvrir mon frigo
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}