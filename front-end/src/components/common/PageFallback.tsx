import React from 'react';

export const PageFallback: React.FC = () => (
  <div
    style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100%',
      minHeight: '200px',
      color: '#94a3b8',
      fontSize: '0.875rem',
    }}
  >
    Loading…
  </div>
);

export default PageFallback;
