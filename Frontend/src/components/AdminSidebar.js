import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './AdminSidebar.css';

const NAV = [
  { to: '/admin', label: 'Tableau de bord' },
  { to: '/admin/users', label: 'Utilisateurs' },
  { to: '/admin/recipes', label: 'Recettes' },
];

export default function AdminSidebar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => { logout(); nav('/login'); };

  return (
    <aside className={`asidebar ${collapsed ? 'asidebar--collapsed' : ''}`}>
      <div className="asidebar__header">
        {!collapsed && (
          <div className="asidebar__logo">
            <span className="asidebar__logo-text">Admin Panel</span>
          </div>
        )}
        <button className="asidebar__toggle" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? 'Ouvrir' : 'Réduire'}
        </button>
      </div>

      <nav className="asidebar__nav">
        {NAV.map(item => (
          <NavLink
            key={item.to} to={item.to} end={item.to === '/admin'}
            className={({ isActive }) => `asidebar__link ${isActive ? 'asidebar__link--active' : ''}`}
          >
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="asidebar__footer">
        <div className="asidebar__user">
          <div className="asidebar__avatar">
            {(user?.username || 'A')[0].toUpperCase()}
          </div>
          {!collapsed && (
            <div className="asidebar__user-info">
              <span className="asidebar__user-name">{user?.username}</span>
              <span className="asidebar__user-role">Administrateur</span>
            </div>
          )}
        </div>
        <button className="asidebar__logout" onClick={handleLogout} title="Déconnexion">
          {!collapsed && 'Déconnexion'}
        </button>
      </div>
    </aside>
  );
}