import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Button from '../../components/ui/Button';
import './OnboardingPage.css';

const CUISINES = [
  { id:'Marocaine', label:'Marocaine' },
  { id:'Française', label:'Française' },
  { id:'Italienne', label:'Italienne' },
  { id:'Japonaise', label:'Japonaise' },
  { id:'Mexicaine', label:'Mexicaine' },
  { id:'Libanaise', label:'Libanaise' },
  { id:'Indienne', label:'Indienne' },
  { id:'Américaine', label:'Américaine' },
  { id:'Chinoise', label:'Chinoise' },
  { id:'Espagnole', label:'Espagnole' },
  { id:'Turque', label:'Turque' },
  { id:'Thaïlandaise', label:'Thaïlandaise' },
  { id:'Coréenne', label:'Coréenne' },
  { id:'Grecque', label:'Grecque' },
  { id:'Hawaïenne', label:'Hawaïenne' },
  { id:'Indonésienne', label:'Indonésienne' },
  { id:'Malaisienne', label:'Malaisienne' },
  { id:'Moyen-orientale', label:'Moyen-orientale' },
  { id:'Peruvienne', label:'Péruvienne' },
  { id:'Russe', label:'Russe' },
  { id:'Venezuelienne', label:'Vénézuélienne' },
  { id:'Vietnamienne', label:'Vietnamienne' },
];

const REGIMES = [
  { id:'normal', label:'Normal', desc:'Je mange de tout' },
  { id:'végétarien', label:'Végétarien', desc:'Pas de viande ni poisson' },
  { id:'végétalien', label:'Végétalien', desc:'Aucun produit animal' },
  { id:'sans gluten', label:'Sans gluten', desc:'Intolérant au gluten' },
];

const STEPS = ['Bienvenue', 'Régime', 'Cuisines', 'Région'];

export default function OnboardingPage() {
  const { user, completeOnboarding } = useAuth();
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [regime, setRegime] = useState('normal');
  const [cuisines, setCuisines] = useState([]);
  const [region, setRegion] = useState('');
  const [pays, setPays] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const toggleCuisine = id => {
    setCuisines(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]);
  };

  const canNext = () => {
    if (step === 2) return cuisines.length > 0;
    return true;
  };

  const handleFinish = async () => {
    setLoading(true);
    setError('');
    try {
      await completeOnboarding({ regime_alimentaire: regime, preferences_cuisine: cuisines, region, pays });
      nav('/home');
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur lors de la sauvegarde');
    } finally {
      setLoading(false);
    }
  };

  const progress = ((step) / (STEPS.length - 1)) * 100;

  return (
    <div className="onboard">
      <div className="onboard__card animate-fade">
        {/* Header */}
        <div className="onboard__header">
          <h1 className="onboard__logo">À Ton Goût</h1>
          <p className="onboard__welcome">Bienvenue, <strong>{user?.username}</strong> ! Personnalisons votre expérience.</p>
        </div>

        {/* Progress */}
        <div className="onboard__progress-wrap">
          <div className="onboard__steps">
            {STEPS.map((s, i) => (
              <div key={s} className={`onboard__step-dot ${i <= step ? 'onboard__step-dot--done' : ''}`}>
                {i < step ? '' : i + 1}
                <span className="onboard__step-label">{s}</span>
              </div>
            ))}
          </div>
          <div className="onboard__bar"><div className="onboard__bar-fill" style={{ width: `${progress}%` }} /></div>
        </div>

        {/* Step 0: Welcome */}
        {step === 0 && (
          <div className="onboard__step animate-fade">
            <div className="onboard__step-icon"></div>
            <h2 className="onboard__step-title">Quelques questions rapides</h2>
            <p className="onboard__step-desc">
              Pour vous proposer des recettes qui vous correspondent vraiment, nous allons vous poser
              3 courtes questions. Cela ne prendra que 30 secondes !
            </p>
            <div className="onboard__tip">
              Vous pourrez modifier ces préférences à tout moment depuis votre profil.
            </div>
          </div>
        )}

        {/* Step 1: Regime */}
        {step === 1 && (
          <div className="onboard__step animate-fade">
            <h2 className="onboard__step-title">Quel est votre régime alimentaire ?</h2>
            <p className="onboard__step-desc">Nous adapterons les recommandations en conséquence.</p>
            <div className="onboard__regime-grid">
              {REGIMES.map(r => (
                <button
                  key={r.id}
                  className={`onboard__regime-card ${regime === r.id ? 'onboard__regime-card--selected' : ''}`}
                  onClick={() => setRegime(r.id)}
                >
                  <span className="onboard__regime-label">{r.label}</span>
                  <span className="onboard__regime-desc">{r.desc}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Cuisines */}
        {step === 2 && (
          <div className="onboard__step animate-fade">
            <h2 className="onboard__step-title">Quelles cuisines vous inspirent ?</h2>
            <p className="onboard__step-desc">Sélectionnez toutes celles qui vous plaisent (minimum 1).</p>
            <div className="onboard__cuisine-grid">
              {CUISINES.map(c => (
                <button
                  key={c.id}
                  className={`onboard__cuisine-btn ${cuisines.includes(c.id) ? 'onboard__cuisine-btn--selected' : ''}`}
                  onClick={() => toggleCuisine(c.id)}
                >
                  <span>{c.label}</span>
                  {cuisines.includes(c.id) && <span className="onboard__check">✓</span>}
                </button>
              ))}
            </div>
            {cuisines.length > 0 && (
              <p className="onboard__sel-count">{cuisines.length} cuisine(s) sélectionnée(s)</p>
            )}
          </div>
        )}

        {/* Step 3: Region */}
        {step === 3 && (
          <div className="onboard__step animate-fade">
            <h2 className="onboard__step-title">Où êtes-vous basé(e) ? (optionnel)</h2>
            <p className="onboard__step-desc">Cela nous aide à trouver des recettes adaptées à votre région.</p>
            <div className="onboard__region-fields">
              <div className="onboard__field">
                <label>Pays</label>
                <input className="onboard__input" placeholder="ex: Maroc" value={pays} onChange={e => setPays(e.target.value)} />
              </div>
              <div className="onboard__field">
                <label>Région / Ville</label>
                <input className="onboard__input" placeholder="ex: Casablanca" value={region} onChange={e => setRegion(e.target.value)} />
              </div>
            </div>
          </div>
        )}

        {error && <div className="onboard__error">{error}</div>}

        {/* Navigation */}
        <div className="onboard__nav">
          {step > 0 && (
            <Button variant="ghost" onClick={() => setStep(s => s - 1)}> Retour</Button>
          )}
          <div style={{ flex: 1 }} />
          {step < STEPS.length - 1 ? (
            <Button variant="primary" size="lg" onClick={() => setStep(s => s + 1)} disabled={!canNext()}>
              {step === 0 ? 'Commencer' : 'Suivant'}
            </Button>
          ) : (
            <Button variant="primary" size="lg" loading={loading} onClick={handleFinish}>
              Voir mes recommandations
            </Button>
          )}
        </div>

        {step === 3 && (
          <button className="onboard__skip" onClick={handleFinish}>
            Passer cette étape
          </button>
        )}
      </div>
    </div>
  );
}