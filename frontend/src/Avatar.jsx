import React from 'react';

export default function Avatar({ username, size = 'md' }) {
  const name = (username || '?').toString();
  let hue = 7;
  for (const ch of name) hue = (hue * 31 + ch.charCodeAt(0)) % 360;
  return (
    <span
      className={`avatar avatar-${size}`}
      style={{
        background: `hsl(${hue}, 72%, 88%)`,
        color: `hsl(${hue}, 52%, 30%)`,
      }}
      aria-hidden="true"
    >
      {name.slice(0, 2).toUpperCase()}
    </span>
  );
}
