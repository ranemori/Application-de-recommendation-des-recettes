import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { notificationAPI } from '../services/api';
import './NotificationBell.css';

export default function NotificationBell() {
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const wrapRef = useRef(null);

  const fetchUnread = () => {
    notificationAPI.unreadCount().then(d => setUnreadCount(d.count)).catch(() => {});
  };

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000); // poll every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = e => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToggle = () => {
    const next = !open;
    setOpen(next);
    if (next) {
      notificationAPI.list().then(setNotifications).catch(() => {});
    }
  };

  const handleNotificationClick = async n => {
    if (!n.is_read) {
      await notificationAPI.markRead(n.id).catch(() => {});
      setUnreadCount(c => Math.max(0, c - 1));
      setNotifications(prev => prev.map(x => x.id === n.id ? { ...x, is_read: true } : x));
    }
    setOpen(false);
    if (n.link) nav(n.link);
  };

  const handleMarkAllRead = async () => {
    await notificationAPI.markAllRead().catch(() => {});
    setUnreadCount(0);
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
  };

  const timeAgo = dateStr => {
    const diffSec = Math.floor((Date.now() - new Date(dateStr)) / 1000);
    if (diffSec < 60) return 'à l\'instant';
    if (diffSec < 3600) return `il y a ${Math.floor(diffSec / 60)} min`;
    if (diffSec < 86400) return `il y a ${Math.floor(diffSec / 3600)} h`;
    return `il y a ${Math.floor(diffSec / 86400)} j`;
  };

  return (
    <div className="notif-bell-wrap" ref={wrapRef}>
      <button className="notif-bell" onClick={handleToggle} aria-label="Notifications">
        <svg viewBox="0 0 24 25" fill="none" width="20" height="20">
          <path
            fillRule="evenodd" clipRule="evenodd" fill="currentColor"
            d="m11.9572 4.31201c-3.35401 0-6.00906 2.59741-6.00906 5.67742v3.29037c0 .1986-.05916.3927-.16992.5576l-1.62529 2.4193-.01077.0157c-.18701.2673-.16653.5113-.07001.6868.10031.1825.31959.3528.67282.3528h14.52603c.2546 0 .5013-.1515.6391-.3968.1315-.2343.1117-.4475-.0118-.6093-.0065-.0085-.0129-.0171-.0191-.0258l-1.7269-2.4194c-.121-.1695-.186-.3726-.186-.5809v-3.29037c0-1.54561-.6851-3.023-1.7072-4.00431-1.1617-1.01594-2.6545-1.67311-4.3019-1.67311zm-8.00906 5.67742c0-4.27483 3.64294-7.67742 8.00906-7.67742 2.2055 0 4.1606.88547 5.6378 2.18455.01.00877.0198.01774.0294.02691 1.408 1.34136 2.3419 3.34131 2.3419 5.46596v2.97007l1.5325 2.1471c.6775.8999.6054 1.9859.1552 2.7877-.4464.795-1.3171 1.4177-2.383 1.4177h-14.52603c-2.16218 0-3.55087-2.302-2.24739-4.1777l1.45056-2.1593zm4.05187 11.32257c0-.5523.44772-1 1-1h5.99999c.5523 0 1 .4477 1 1s-.4477 1-1 1h-5.99999c-.55228 0-1-.4477-1-1z"
          />
        </svg>
        {unreadCount > 0 && <span className="notif-bell__badge">{unreadCount > 9 ? '9+' : unreadCount}</span>}
      </button>

      {open && (
        <div className="notif-dropdown">
          <div className="notif-dropdown__head">
            <span>Notifications</span>
            {unreadCount > 0 && (
              <button className="notif-dropdown__markall" onClick={handleMarkAllRead}>Tout marquer lu</button>
            )}
          </div>

          {notifications.length === 0 ? (
            <p className="notif-dropdown__empty">Aucune notification pour le moment.</p>
          ) : (
            <div className="notif-dropdown__list">
              {notifications.map(n => (
                <button
                  key={n.id}
                  className={`notif-toast ${n.is_read ? '' : 'notif-toast--unread'}`}
                  onClick={() => handleNotificationClick(n)}
                >
                  <div className="notif-toast__avatar">
                    <svg viewBox="0 0 20 18" width="14" height="14" fill="#fff">
                      <path d="M18 4H16V9C16 10.0609 15.5786 11.0783 14.8284 11.8284C14.0783 12.5786 13.0609 13 12 13H9L6.846 14.615C7.17993 14.8628 7.58418 14.9977 8 15H11.667L15.4 17.8C15.5731 17.9298 15.7836 18 16 18C16.2652 18 16.5196 17.8946 16.7071 17.7071C16.8946 17.5196 17 17.2652 17 17V15H18C18.5304 15 19.0391 14.7893 19.4142 14.4142C19.7893 14.0391 20 13.5304 20 13V6C20 5.46957 19.7893 4.96086 19.4142 4.58579C19.0391 4.21071 18.5304 4 18 4Z" />
                    </svg>
                  </div>
                  <div className="notif-toast__text">
                    <span className="notif-toast__title">{n.title}</span>
                    {n.message && <p className="notif-toast__message">{n.message}</p>}
                    <span className="notif-toast__time">{timeAgo(n.created_at)}</span>
                  </div>
                  {!n.is_read && <span className="notif-toast__dot" />}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
