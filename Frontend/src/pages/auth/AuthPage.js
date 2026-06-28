import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui';
import Input from '../../components/ui/Input';
import ErrorAlert from '../../components/ui/ErrorAlert';
import './AuthPage.css';

export default function AuthPage({ mode = 'login' }) {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [tab, setTab] = useState(mode);
  const [form, setForm] = useState({ username:'', email:'', password:'', confirm:'' });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [serverErr, setServerErr] = useState('');

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const validateLogin = () => {
    const e = {};
    if (!form.email) e.email = 'Email requis';
    if (!form.password) e.password = 'Mot de passe requis';
    return e;
  };
  const validateRegister = () => {
    const e = {};
    if (!form.username || form.username.length < 3) e.username = 'Minimum 3 caractères';
    if (!/\S+@\S+\.\S+/.test(form.email)) e.email = 'Email invalide';
    if (form.password.length < 8) e.password = 'Minimum 8 caractères';
    if (form.password !== form.confirm) e.confirm = 'Les mots de passe ne correspondent pas';
    return e;
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setServerErr('');
    const errs = tab === 'login' ? validateLogin() : validateRegister();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    try {
      if (tab === 'login') {
        const u = await login({ email: form.email, password: form.password });
        nav(u.role === 'admin' ? '/admin' : (u.onboarding_done ? '/home' : '/onboarding'));
      } else {
        await register({ username: form.username, email: form.email, password: form.password });
        nav('/onboarding');
      }
    } catch (err) {
      setServerErr(err.response?.data?.detail || 'Une erreur est survenue');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth">
      {/* Left decorative panel */}
      <div className={`auth__panel ${tab === 'login' ? 'auth__panel--login' : 'auth__panel--register'}`}>
        <div className="auth__panel-gif" />
        <div className="auth__panel-content">
          <h1 className="auth__panel-title">À Ton Goût</h1>
          <p className="auth__panel-sub">Votre moteur de recommandation culinaire intelligent</p>
          <div className="auth__features">
            <div className="auth__feat">Recommandations personnalisées par IA</div>
            <div className="auth__feat">Recettes selon votre frigo</div>
            <div className="auth__feat">Cuisines du monde entier</div>
            <div className="auth__feat">Notez et sauvegardez vos favoris</div>
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="auth__form-panel">
        <div className="auth__form-wrap animate-fade">
          {/* Tabs */}
          <div className="auth__tabs">
            <button className={`auth__tab ${tab==='login' ? 'auth__tab--active' : ''}`} onClick={() => { setTab('login'); setErrors({}); setServerErr(''); }}>
              Connexion
            </button>
            <button className={`auth__tab ${tab==='register' ? 'auth__tab--active' : ''}`} onClick={() => { setTab('register'); setErrors({}); setServerErr(''); }}>
              Inscription
            </button>
          </div>

          <h2 className="auth__title">
            {tab === 'login' ? 'Bon retour ' : 'Créer un compte '}
          </h2>
          <p className="auth__sub">
            {tab === 'login' ? 'Connectez-vous pour accéder à vos recommandations' : 'Rejoignez la communauté et découvrez des recettes personnalisées'}
          </p>

          {serverErr && (
            <div className="auth__error-wrap">
              <ErrorAlert
                message="Veuillez réessayer"
                detail={serverErr}
                onClose={() => setServerErr('')}
              />
            </div>
          )}

          <form className="auth__fields" onSubmit={handleSubmit} noValidate>
            {tab === 'register' && (
              <Input label="Nom d'utilisateur" placeholder="chef_paul" value={form.username}
                onChange={set('username')} error={errors.username} icon="" />
            )}
            <Input label="Email" type="email" placeholder="vous@exemple.com"
              value={form.email} onChange={set('email')} error={errors.email} icon="️" />
            <Input label="Mot de passe" type="password" placeholder="••••••••"
              value={form.password} onChange={set('password')} error={errors.password} icon="" />
            {tab === 'login' && (
              <Link to="/forgot-password" className="auth__forgot-link">Mot de passe oublié ?</Link>
            )}
            {tab === 'register' && (
              <Input label="Confirmer le mot de passe" type="password" placeholder="••••••••"
                value={form.confirm} onChange={set('confirm')} error={errors.confirm} icon="" />
            )}

            <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
              {tab === 'login' ? 'Se connecter' : "S'inscrire"}
            </Button>
          </form>

          <p className="auth__switch">
            {tab === 'login'
              ? <>Pas encore de compte ? <button className="auth__switch-btn" onClick={() => setTab('register')}>S'inscrire</button></>
              : <>Déjà un compte ? <button className="auth__switch-btn" onClick={() => setTab('login')}>Se connecter</button></>
            }
          </p>
        </div>
      </div>
    </div>
  );
}