import React, { useEffect, useState } from 'react';
import './CharacterMascot.css';

export default function CharacterMascot({ caption = 'Tu vas pas manger ça ?' }) {
  const [look, setLook] = useState('');

  useEffect(() => {
    const onMove = e => {
      if (e.clientX <= window.innerWidth / 2) setLook('look-left');
      else setLook('look-right');
    };
    window.addEventListener('mousemove', onMove);
    return () => window.removeEventListener('mousemove', onMove);
  }, []);

  return (
    <div className="character-mascot">
      <div className="cm-me">
        <div className="cm-hair">
          {['first', 'second', 'third', 'fourth', 'fifth'].map(row => (
            <div key={row} className={`cm-row cm-row--${row}`}>
              {[0, 1, 2, 3, 4].map(i => <span key={i}></span>)}
            </div>
          ))}
        </div>
        <div className="cm-shirt"></div>
        <div className={`cm-neck ${look}`}></div>
        <div className={`cm-head ${look}`}>
          <div className="cm-bangs">
            {[0, 1, 2].map(i => <span key={i}></span>)}
          </div>
          <div className="cm-bangs cm-bangs--upper">
            {[0, 1, 2].map(i => <span key={i}></span>)}
          </div>
          <div className={`cm-face ${look}`}>
            <div className="cm-glasses">
              <div className="cm-glasses__lens cm-glasses__lens--left"><div className="cm-shine"></div></div>
              <div className="cm-glasses__lens cm-glasses__lens--right"><div className="cm-shine"></div></div>
            </div>
            <div className="cm-eyes"></div>
          </div>
        </div>
      </div>
      {caption && <p className="cm-caption">{caption}</p>}
    </div>
  );
}