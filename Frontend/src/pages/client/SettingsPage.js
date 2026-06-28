import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI, userAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import ClientNavbar from '../../components/ClientNavbar';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import ErrorAlert from '../../components/ui/ErrorAlert';
import DeactivateAccountModal from '../../components/DeactivateAccountModal';
import './SettingsPage.css';

export default function SettingsPage() {
  const nav = useNavigate();
  const { logout } = useAuth();
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [deactivateError, setDeactivateError] = useState('');

  const handleChangePassword = async () => {
    setPwError('');
    setPwSuccess('');
    if (pwForm.new_password.length < 8) {
      setPwError('Le nouveau mot de passe doit contenir au moins 8 caractères');
      return;
    }
    if (pwForm.new_password !== pwForm.confirm) {
      setPwError('Les mots de passe ne correspondent pas');
      return;
    }
    setPwLoading(true);
    try {
      await authAPI.changePassword({
        current_password: pwForm.current_password,
        new_password: pwForm.new_password,
      });
      setPwSuccess('Mot de passe mis à jour');
      setPwForm({ current_password: '', new_password: '', confirm: '' });
    } catch (err) {
      setPwError(err.response?.data?.detail || 'Une erreur est survenue');
    } finally {
      setPwLoading(false);
    }
  };

  const handleDeactivate = async () => {
    setDeactivateError('');
    try {
      await userAPI.deactivate();
      logout();
      nav('/login');
    } catch (err) {
      setDeactivateError(err.response?.data?.detail || 'Une erreur est survenue');
      setShowDeactivate(false);
    }
  };

  return (
    <div className="settings-layout">
      <ClientNavbar />
      <main className="settings-main">
        <h1 className="settings-title">Paramètres</h1>

        <div className="settings-card">
          <h2 className="settings-section-title">Mot de passe</h2>
          <p className="settings-section-sub">
            Choisissez un mot de passe d'au moins 8 caractères que vous n'utilisez pas ailleurs.
          </p>

          <div className="settings-grid">
            <Input
              label="Mot de passe actuel" type="password" placeholder="••••••••"
              value={pwForm.current_password}
              onChange={e => setPwForm(f => ({ ...f, current_password: e.target.value }))}
            />
            <Input
              label="Nouveau mot de passe" type="password" placeholder="••••••••"
              value={pwForm.new_password}
              onChange={e => setPwForm(f => ({ ...f, new_password: e.target.value }))}
            />
            <Input
              label="Confirmer le nouveau mot de passe" type="password" placeholder="••••••••"
              value={pwForm.confirm}
              onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))}
            />
          </div>

          {pwError && (
            <div style={{ marginTop: '.9rem' }}>
              <ErrorAlert message="Veuillez réessayer" detail={pwError} onClose={() => setPwError('')} />
            </div>
          )}
          {pwSuccess && <div className="settings-success" style={{ marginTop: '.9rem' }}>{pwSuccess}</div>}

          <div className="settings-actions">
            <Button
              variant="primary"
              loading={pwLoading}
              onClick={handleChangePassword}
              disabled={!pwForm.current_password || !pwForm.new_password}
            >
              Changer le mot de passe
            </Button>
          </div>
        </div>

        <div className="settings-card settings-card--danger">
          <h2 className="settings-section-title">Zone dangereuse</h2>
          <p className="settings-section-sub">
            Désactiver votre compte vous déconnectera immédiatement. Vos données
            sont conservées et un administrateur peut réactiver votre compte plus tard.
          </p>

          {deactivateError && (
            <div style={{ marginTop: '.9rem' }}>
              <ErrorAlert message="Veuillez réessayer" detail={deactivateError} onClose={() => setDeactivateError('')} />
            </div>
          )}

          <div className="settings-actions">
            <Button variant="danger" onClick={() => setShowDeactivate(true)}>
              Désactiver mon compte
            </Button>
          </div>
        </div>

        {showDeactivate && (
          <DeactivateAccountModal
            onConfirm={handleDeactivate}
            onCancel={() => setShowDeactivate(false)}
          />
        )}
      </main>
    </div>
  );
}