import React from 'react';
import './Loader.css';

export default function Loader({ label = 'Chargement…' }) {
  return (
    <div className="loader-wrap">
      <div aria-label={label} role="img" className="pan-loader">
        <div className="pan-loader__flip"></div>
        <div className="pan-loader__pan-container">
          <div className="pan-loader__pan"></div>
          <div className="pan-loader__handle"></div>
        </div>
        <div className="pan-loader__shadow"></div>
      </div>
      {label && <p className="loader-wrap__label">{label}</p>}
    </div>
  );
}