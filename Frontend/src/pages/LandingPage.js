import React from 'react';
import { useNavigate } from 'react-router-dom';
import CharacterMascot from '../components/CharacterMascot';
import './LandingPage.css';

export default function LandingPage() {
  const nav = useNavigate();

  return (
    <div className="landing">
      <nav className="landing-nav">
        <span className="landing-nav__logo">À Ton Goût</span>
        <div className="landing-nav__actions">
          <button className="landing-nav__btn landing-nav__btn--ghost" onClick={() => nav('/login')}>
            Connexion
          </button>
          <button className="landing-nav__btn landing-nav__btn--primary" onClick={() => nav('/register')}>
            S'inscrire
          </button>
        </div>
      </nav>

      <header className="landing-hero">
        <div className="landing-hero__text">
          <span className="landing-hero__kicker">Cuisine du monde · Propulsé par l'IA</span>
          <h1 className="landing-hero__title">
            Le goût du monde,<br /><span>juste pour toi.</span>
          </h1>
          <p className="landing-hero__sub">
            À Ton Goût apprend ce que tu aimes vraiment manger — et te propose
            des recettes du monde entier, des plus exotiques aux plus
            réconfortantes. Notre IA connaît ton goût mieux que tes proches.
          </p>
          <div className="landing-hero__cta">
            <button className="landing-nav__btn landing-nav__btn--primary landing-hero__cta-btn" onClick={() => nav('/register')}>
              Commencer gratuitement
            </button>
            <button className="landing-nav__btn landing-nav__btn--ghost" onClick={() => nav('/login')}>
              J'ai déjà un compte
            </button>
          </div>
        </div>
        <div className="landing-hero__mascot">
          <CharacterMascot caption="Tu vas pas manger ça sans moi ?" />
        </div>
      </header>

      <section className="landing-features">
        <h2 className="landing-section-title">Pourquoi À Ton Goût ?</h2>
        <div className="landing-features__grid">
          <div className="landing-feature">
            <span className="landing-feature__icon">🧠</span>
            <h3>Recommandé par IA</h3>
            <p>Un modèle de recommandation personnalisé qui apprend de tes goûts à chaque interaction.</p>
          </div>
          <div className="landing-feature">
            <span className="landing-feature__icon">🥬</span>
            <h3>Frigo intelligent</h3>
            <p>Donne-nous tes ingrédients disponibles, on te trouve des recettes réalisables tout de suite.</p>
          </div>
          <div className="landing-feature">
            <span className="landing-feature__icon">🌍</span>
            <h3>Cuisines du monde entier</h3>
            <p>Des centaines de recettes, du tajine marocain au bibimbap coréen, en passant par la pastilla.</p>
          </div>
          <div className="landing-feature">
            <span className="landing-feature__icon">❤️</span>
            <h3>Connaît ton goût</h3>
            <p>Plus tu likes, sauvegardes et notes, plus À Ton Goût te connaît — mieux que tes proches amis.</p>
          </div>
        </div>
      </section>

      <section className="landing-banner">
        <h2>Ton prochain repas préféré t'attend.</h2>
        <button className="landing-nav__btn landing-nav__btn--primary" onClick={() => nav('/register')}>
          Créer mon compte gratuit
        </button>
      </section>

      <footer className="landing-footer">
        <div className="landing-footer__top">
          <span className="landing-footer__logo">À Ton Goût</span>
          <p>Votre moteur de recommandation culinaire intelligent.</p>
        </div>
        <div className="landing-footer__contact">
          <span>Contact :</span>
          <a href="mailto:contact@atongout.app">contact@atongout.app</a>
        </div>
        <p className="landing-footer__copy">© {new Date().getFullYear()} À Ton Goût — Tous droits réservés.</p>
      </footer>
    </div>
  );
}