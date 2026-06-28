import React, { useState, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { userAPI } from '../../services/api';
import ClientNavbar from '../../components/ClientNavbar';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import { resolveImageUrl } from '../../utils/imageUrl';
import './ProfilePage.css';

const CUISINES = [
  'Marocaine', 'Française', 'Italienne', 'Japonaise', 'Mexicaine', 'Libanaise',
  'Indienne', 'Américaine', 'Chinoise', 'Espagnole', 'Turque', 'Thaïlandaise',
  'Coréenne', 'Grecque', 'Hawaïenne', 'Indonésienne', 'Malaisienne',
  'Moyen-orientale', 'Peruvienne', 'Russe', 'Venezuelienne', 'Vietnamienne',
];
const REGIMES = ['normal', 'végétarien', 'végétalien', 'sans gluten'];

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState({
    username: user?.username || '',
    region: user?.region || '',
    pays: user?.pays || '',
    regime_alimentaire: user?.regime_alimentaire || 'normal',
    preferences_cuisine: user?.preferences_cuisine || [],
  });
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const avatarInputRef = useRef(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarError, setAvatarError] = useState('');

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const toggleCuisine = c => {
    setForm(f => ({
      ...f,
      preferences_cuisine: f.preferences_cuisine.includes(c)
        ? f.preferences_cuisine.filter(x => x !== c)
        : [...f.preferences_cuisine, c],
    }));
    setSaved(false);
  };

  const handleSave = async () => {
    setLoading(true);
    setError('');
    try {
      const { username, ...editable } = form;
      await userAPI.update(editable);
      await refreshUser();
      setSaved(true);
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur lors de la sauvegarde');
    } finally {
      setLoading(false);
    }
  };

  const handleAvatarChange = async e => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarError('');
    setAvatarUploading(true);
    try {
      await userAPI.uploadAvatar(file);
      await refreshUser();
    } catch (err) {
      setAvatarError(err.response?.data?.detail || "Impossible d'envoyer cette image");
    } finally {
      setAvatarUploading(false);
      e.target.value = '';
    }
  };

  if (!user) return null;

  return (
    <div className="profile-layout">
      <ClientNavbar />
      <main className="profile-main">
        <div className="profile-header">
          <div className="profile-avatar profile-avatar--editable" onClick={() => avatarInputRef.current?.click()}>
            {user.avatar_url
              ? <img src={resolveImageUrl(user.avatar_url)} alt="" className="profile-avatar-img" />
              : (user.username || 'U')[0].toUpperCase()
            }
            <div className="profile-avatar-overlay">{avatarUploading ? '…' : 'Modifier'}</div>
          </div>
          <input
            ref={avatarInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            style={{ display: 'none' }}
            onChange={handleAvatarChange}
          />
          <div>
            <h1 className="profile-title">{user.username}</h1>
            <p className="profile-email">{user.email}</p>
            {avatarError && <p className="profile-avatar-error">{avatarError}</p>}
          </div>
        </div>

        <div className="profile-card">
          <h2 className="profile-section-title">Informations générales</h2>
          <div className="profile-grid">
            <Input
              label="Nom d'utilisateur"
              value={form.username}
              disabled
              title="Le nom d'utilisateur ne peut pas être modifié"
            />
            <Input label="Pays" placeholder="ex: Maroc" value={form.pays} onChange={set('pays')} />
            <Input label="Région / Ville" placeholder="ex: Casablanca" value={form.region} onChange={set('region')} />
          </div>
        </div>

        <div className="profile-card">
          <h2 className="profile-section-title">Régime alimentaire</h2>
          <div className="profile-regime-row">
            {REGIMES.map(r => (
              <button
                key={r}
                className={`profile-regime-btn ${form.regime_alimentaire === r ? 'profile-regime-btn--active' : ''}`}
                onClick={() => { setForm(f => ({ ...f, regime_alimentaire: r })); setSaved(false); }}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        <div className="profile-card">
          <h2 className="profile-section-title">Cuisines préférées</h2>
          <div className="profile-cuisine-row">
            {CUISINES.map(c => (
              <button
                key={c}
                className={`profile-cuisine-btn ${form.preferences_cuisine.includes(c) ? 'profile-cuisine-btn--active' : ''}`}
                onClick={() => toggleCuisine(c)}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {error && <div className="profile-error">{error}</div>}
        {saved && <div className="profile-success">Profil mis à jour</div>}

        <div className="profile-actions">
          <Button variant="primary" size="lg" loading={loading} onClick={handleSave}>
            Enregistrer les modifications
          </Button>
        </div>
      </main>
    </div>
  );
}