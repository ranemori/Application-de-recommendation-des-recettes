import React, { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import NotificationBell from './NotificationBell';
import { resolveImageUrl } from '../utils/imageUrl';
import './ClientNavbar.css';

export default function ClientNavbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => { logout(); nav('/login'); };

  return (
    <nav className="cnav">
      <div className="cnav__inner">
        {/* Logo */}
        <Link to="/home" className="cnav__logo">
          <span className="cnav__logo-text">À Ton Goût</span>
        </Link>

        {/* Links desktop */}
        <div className="cnav-pill">
          <NavLink to="/home" className={({isActive}) => `cnav-pill__item ${isActive ? 'cnav-pill__item--active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M11.47 3.841a.75.75 0 0 1 1.06 0l8.69 8.69a.75.75 0 1 0 1.06-1.061l-8.689-8.69a2.25 2.25 0 0 0-3.182 0l-8.69 8.69a.75.75 0 1 0 1.061 1.06l8.69-8.689Z" />
              <path d="m12 5.432 8.159 8.159c.03.03.06.058.091.086v6.198c0 1.035-.84 1.875-1.875 1.875H15a.75.75 0 0 1-.75-.75v-4.5a.75.75 0 0 0-.75-.75h-3a.75.75 0 0 0-.75.75V21a.75.75 0 0 1-.75.75H5.625a1.875 1.875 0 0 1-1.875-1.875v-6.198a2.29 2.29 0 0 0 .091-.086L12 5.432Z" />
            </svg>
            <span>Accueil</span>
          </NavLink>
          <NavLink to="/recommendations" className={({isActive}) => `cnav-pill__item ${isActive ? 'cnav-pill__item--active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.004 10.407c.138.435-.216.842-.672.842h-3.465a.75.75 0 0 1-.65-.375l-1.732-3c-.229-.396-.053-.907.393-1.004a5.252 5.252 0 0 1 6.126 3.537ZM8.12 8.464c.307-.338.838-.235 1.066.16l1.732 3a.75.75 0 0 1 0 .75l-1.732 3c-.229.397-.76.5-1.067.161A5.23 5.23 0 0 1 6.75 12a5.23 5.23 0 0 1 1.37-3.536ZM10.878 17.13c-.447-.098-.623-.608-.394-1.004l1.733-3.002a.75.75 0 0 1 .65-.375h3.465c.457 0 .81.407.672.842a5.252 5.252 0 0 1-6.126 3.539Z" />
              <path fillRule="evenodd" clipRule="evenodd" d="M21 12.75a.75.75 0 1 0 0-1.5h-.783a8.22 8.22 0 0 0-.237-1.357l.734-.267a.75.75 0 1 0-.513-1.41l-.735.268a8.24 8.24 0 0 0-.689-1.192l.6-.503a.75.75 0 1 0-.964-1.149l-.6.504a8.3 8.3 0 0 0-1.054-.885l.391-.678a.75.75 0 1 0-1.299-.75l-.39.676a8.188 8.188 0 0 0-1.295-.47l.136-.77a.75.75 0 0 0-1.477-.26l-.136.77a8.36 8.36 0 0 0-1.377 0l-.136-.77a.75.75 0 1 0-1.477.26l.136.77c-.448.121-.88.28-1.294.47l-.39-.676a.75.75 0 0 0-1.3.75l.392.678a8.29 8.29 0 0 0-1.054.885l-.6-.504a.75.75 0 1 0-.965 1.149l.6.503a8.243 8.243 0 0 0-.689 1.192l-.735-.268a.75.75 0 1 0-.513 1.41l.735.267a8.222 8.222 0 0 0-.238 1.356h-.783a.75.75 0 0 0 0 1.5h.783c.042.464.122.917.238 1.356l-.735.268a.75.75 0 0 0 .513 1.41l.735-.268c.197.417.428.816.69 1.191l-.6.504a.75.75 0 0 0 .963 1.15l.601-.505c.326.323.679.62 1.054.885l-.392.68a.75.75 0 0 0 1.3.75l.39-.679c.414.192.847.35 1.294.471l-.136.77a.75.75 0 0 0 1.477.261l.137-.772a8.332 8.332 0 0 0 1.376 0l.136.772a.75.75 0 1 0 1.477-.26l-.136-.771a8.19 8.19 0 0 0 1.294-.47l.391.677a.75.75 0 0 0 1.3-.75l-.393-.679a8.29 8.29 0 0 0 1.054-.885l.601.504a.75.75 0 0 0 .964-1.15l-.6-.503c.261-.375.492-.774.69-1.191l.735.267a.75.75 0 1 0 .512-1.41l-.734-.267c.115-.439.195-.892.237-1.356h.784Z" />
            </svg>
            <span>Recommandations</span>
          </NavLink>
          <NavLink to="/fridge" className={({isActive}) => `cnav-pill__item ${isActive ? 'cnav-pill__item--active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path fillRule="evenodd" clipRule="evenodd" d="M6.75 2.25A.75.75 0 0 1 7.5 3v1.5h9V3A.75.75 0 0 1 18 3v1.5h.75a3 3 0 0 1 3 3v11.25a3 3 0 0 1-3 3H5.25a3 3 0 0 1-3-3V7.5a3 3 0 0 1 3-3H6V3a.75.75 0 0 1 .75-.75Zm13.5 9a1.5 1.5 0 0 0-1.5-1.5H5.25a1.5 1.5 0 0 0-1.5 1.5v7.5a1.5 1.5 0 0 0 1.5 1.5h13.5a1.5 1.5 0 0 0 1.5-1.5v-7.5Z" />
            </svg>
            <span>Mon Frigo</span>
          </NavLink>
          <NavLink to="/recipes" className={({isActive}) => `cnav-pill__item ${isActive ? 'cnav-pill__item--active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.5 21a3 3 0 0 0 3-3v-4.5a3 3 0 0 0-3-3h-15a3 3 0 0 0-3 3V18a3 3 0 0 0 3 3h15ZM1.5 10.146V6a3 3 0 0 1 3-3h5.379a2.25 2.25 0 0 1 1.59.659l2.122 2.121c.14.141.331.22.53.22H19.5a3 3 0 0 1 3 3v1.146A4.483 4.483 0 0 0 19.5 9h-15a4.483 4.483 0 0 0-3 1.146Z" />
            </svg>
            <span>Recettes</span>
          </NavLink>
          <NavLink to="/saved" className={({isActive}) => `cnav-pill__item ${isActive ? 'cnav-pill__item--active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" />
            </svg>
            <span>Sauvegardées</span>
          </NavLink>
        </div>

        {/* User menu */}
        <div className="cnav__right">
          <NotificationBell />
          <div className="cnav__avatar-wrap" onClick={() => setOpen(!open)}>
            <div className="cnav__avatar">
              {user?.avatar_url
                ? <img src={resolveImageUrl(user.avatar_url)} alt="" />
                : <span>{(user?.username || 'U')[0].toUpperCase()}</span>
              }
            </div>
            <span className="cnav__username">{user?.username}</span>
            <span className="cnav__chevron">{open ? '▲' : '▼'}</span>
          </div>
          {open && (
            <div className="cnav__dropdown" onMouseLeave={() => setOpen(false)}>
              <div className="cnav__dropdown-head">
                <p className="cnav__dropdown-label">Connecté en tant que</p>
                <div className="cnav__dropdown-id">
                  <div className="cnav__dropdown-avatar">
                    {user?.avatar_url
                      ? <img src={resolveImageUrl(user.avatar_url)} alt="" />
                      : <span>{(user?.username || 'U')[0].toUpperCase()}</span>
                    }
                  </div>
                  <p className="cnav__dropdown-email">{user?.email}</p>
                </div>
              </div>

              <div className="cnav__dropdown-body">
                <Link to="/profile" className="cnav__drop-item" onClick={() => setOpen(false)}>
                  <span className="cnav__drop-icon">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" clipRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" /></svg>
                  </span>
                  <span className="cnav__drop-text">Mon profil</span>
                  <span className="cnav__drop-chevron">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" clipRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" /></svg>
                  </span>
                </Link>

                <Link to="/settings" className="cnav__drop-item" onClick={() => setOpen(false)}>
                  <span className="cnav__drop-icon">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" clipRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" /></svg>
                  </span>
                  <span className="cnav__drop-text">Paramètres</span>
                  <span className="cnav__drop-chevron">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" clipRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" /></svg>
                  </span>
                </Link>

                <button className="cnav__drop-item cnav__drop-item--danger" onClick={handleLogout}>
                  <span className="cnav__drop-icon cnav__drop-icon--danger">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" clipRule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z" /></svg>
                  </span>
                  <span className="cnav__drop-text">Déconnexion</span>
                  <span className="cnav__drop-chevron">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" clipRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" /></svg>
                  </span>
                </button>
              </div>
            </div>
          )}
          {/* Mobile burger */}
          <button className="cnav__burger" onClick={() => setMenuOpen(!menuOpen)}>Menu</button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="cnav__mobile">
          <NavLink to="/home" className="cnav__mob-link" onClick={() => setMenuOpen(false)}>Accueil</NavLink>
          <NavLink to="/recommendations" className="cnav__mob-link" onClick={() => setMenuOpen(false)}>Recommandations</NavLink>
          <NavLink to="/fridge" className="cnav__mob-link" onClick={() => setMenuOpen(false)}>Mon Frigo</NavLink>
          <NavLink to="/recipes" className="cnav__mob-link" onClick={() => setMenuOpen(false)}>Recettes</NavLink>
          <NavLink to="/saved" className="cnav__mob-link" onClick={() => setMenuOpen(false)}>Sauvegardées</NavLink>
          <NavLink to="/profile" className="cnav__mob-link" onClick={() => setMenuOpen(false)}>Profil</NavLink>
          <NavLink to="/settings" className="cnav__mob-link" onClick={() => setMenuOpen(false)}>Paramètres</NavLink>
          <button className="cnav__mob-link cnav__mob-link--danger" onClick={handleLogout}>Déconnexion</button>
        </div>
      )}
    </nav>
  );
}