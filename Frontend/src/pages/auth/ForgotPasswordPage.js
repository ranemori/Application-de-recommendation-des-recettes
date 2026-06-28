import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { authAPI } from '../../services/api';
import { Button } from '../../components/ui';
import Input from '../../components/ui/Input';
import ErrorAlert from '../../components/ui/ErrorAlert';
import './AuthPage.css';

export default function ForgotPasswordPage() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const tokenFromUrl = params.get('token') || '';

  const [step, setStep] = useState(tokenFromUrl ? 'reset' : 'request');
  const [email, setEmail] = useState('');
  const [token, setToken] = useState(tokenFromUrl);
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [devToken, setDevToken] = useState('');

  const handleRequest = async e => {
    e.preventDefault();
    setError(''); setInfo(''); setDevToken('');
    setLoading(true);
    try {
      const res = await authAPI.forgotPassword(email);
      setInfo(res.message || 'Si cet email existe, un lien de réinitialisation a été généré.');
      // No email-sending service is configured yet in this project — the
      // backend returns the token directly so you can test the flow.
      // Remove this in production once a real email provider is wired up.
      if (res.dev_reset_token) {
        setDevToken(res.dev_reset_token);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Une erreur est survenue');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async e => {
    e.preventDefault();
    setError('');
    if (newPassword.length < 8) { setError('Le mot de passe doit contenir au moins 8 caractères'); return; }
    if (newPassword !== confirm) { setError('Les mots de passe ne correspondent pas'); return; }
    setLoading(true);
    try {
      await authAPI.resetPassword(token, newPassword);
      setInfo('Mot de passe réinitialisé. Vous pouvez vous connecter.');
      setTimeout(() => nav('/login'), 1500);
    } catch (err) {
      setError(err.response?.data?.detail || 'Lien invalide ou expiré');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth__panel auth__panel--forgot">
        <div className="auth__panel-gif" />
        <div className="auth__panel-content">
          <h1 className="auth__panel-title">À Ton Goût</h1>
          <p className="auth__panel-sub">Réinitialisation du mot de passe</p>
        </div>
      </div>

      <div className="auth__form-panel">
        <div className="auth__form-wrap animate-fade">
          <h2 className="auth__title">Mot de passe oublié</h2>
          <p className="auth__sub">
            {step === 'request'
              ? 'Entrez votre email pour recevoir un lien de réinitialisation.'
              : 'Choisissez votre nouveau mot de passe.'}
          </p>

          {error && (
            <div className="auth__error-wrap">
              <ErrorAlert message="Veuillez réessayer" detail={error} onClose={() => setError('')} />
            </div>
          )}
          {info && <p className="auth__info">{info}</p>}

          {devToken && (
            <div className="auth__dev-token">
              <p>Aucun service d'envoi d'email n'est configuré — utilisez ce jeton pour tester :</p>
              <code>{devToken}</code>
              <button type="button" onClick={() => { setToken(devToken); setStep('reset'); }}>
                Utiliser ce jeton
              </button>
            </div>
          )}

          {step === 'request' ? (
            <form className="auth__fields" onSubmit={handleRequest} noValidate>
              <Input label="Email" type="email" placeholder="vous@exemple.com" value={email} onChange={e => setEmail(e.target.value)} />
              <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
                Envoyer le lien
              </Button>
            </form>
          ) : (
            <form className="auth__fields" onSubmit={handleReset} noValidate>
              <Input label="Jeton de réinitialisation" value={token} onChange={e => setToken(e.target.value)} />
              <Input label="Nouveau mot de passe" type="password" placeholder="••••••••" value={newPassword} onChange={e => setNewPassword(e.target.value)} />
              <Input label="Confirmer le mot de passe" type="password" placeholder="••••••••" value={confirm} onChange={e => setConfirm(e.target.value)} />
              <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
                Réinitialiser le mot de passe
              </Button>
            </form>
          )}

          <p className="auth__switch">
            <Link to="/login" className="auth__switch-btn">Retour à la connexion</Link>
          </p>
        </div>
      </div>
    </div>
  );
}