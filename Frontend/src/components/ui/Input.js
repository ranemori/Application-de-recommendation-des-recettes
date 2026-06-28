import React from 'react';
import './Input.css';

export default function Input({ label, error, icon, className='', ...props }) {
  return (
    <div className={`input-wrap ${error ? 'input-wrap--error' : ''} ${className}`}>
      {label && <label className="input-label">{label}</label>}
      <div className="input-box">
        {icon && <span className="input-icon">{icon}</span>}
        <input className={`input-field ${icon ? 'input-field--icon' : ''}`} {...props} />
      </div>
      {error && <span className="input-error">{error}</span>}
    </div>
  );
}