import React, { useState } from 'react';
import './DeactivateAccountModal.css';

export default function DeactivateAccountModal({ onConfirm, onCancel }) {
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    await onConfirm();
    setLoading(false);
  };

  return (
    <div className="deact-overlay" onClick={onCancel}>
      <div className="deact-card" onClick={e => e.stopPropagation()}>
        <div className="deact-header">
          <div className="deact-image">
            <svg viewBox="0 0 24 24" fill="none" strokeWidth="1.5" stroke="currentColor">
              <path
                strokeLinecap="round" strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
          </div>
          <div className="deact-content">
            <span className="deact-title">Désactiver le compte</span>
            <p className="deact-message">
              Voulez-vous vraiment désactiver votre compte ? Vous serez déconnecté
              immédiatement et ne pourrez plus vous reconnecter tant qu'un
              administrateur n'aura pas réactivé votre compte.
            </p>
          </div>
          <div className="deact-actions">
            <button className="deact-confirm" type="button" onClick={handleConfirm} disabled={loading}>
              {loading ? 'Désactivation…' : 'Désactiver'}
            </button>
            <button className="deact-cancel" type="button" onClick={onCancel} disabled={loading}>
              Annuler
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}