import React from 'react';
import './Button.css';

export default function Button({
  children, variant='primary', size='md', loading=false,
  fullWidth=false, icon, className='', ...props
}) {
  return (
    <button
      className={`btn btn--${variant} btn--${size} ${fullWidth ? 'btn--full' : ''} ${className}`}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading ? <span className="spinner" style={{width:18,height:18,borderWidth:2}} /> : icon && <span className="btn__icon">{icon}</span>}
      {children}
    </button>
  );
}