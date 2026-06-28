import React from 'react';
import './ErrorAlert.css';

export default function ErrorAlert({ message, detail, onClose }) {
  if (!message) return null;
  return (
    <div className="error-alert">
      <div className="error-alert__left">
        <div className="error-alert__icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
        </div>
        <div className="error-alert__text">
          <p className="error-alert__title">{message}</p>
          {detail && <p className="error-alert__detail">{detail}</p>}
        </div>
      </div>
      {onClose && (
        <button className="error-alert__close" onClick={onClose} aria-label="Fermer">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}
