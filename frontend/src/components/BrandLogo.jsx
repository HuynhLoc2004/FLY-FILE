const BrandLogo = ({ size = 32, showText = true, className = '' }) => {
  return (
    <div className={`brand-logo-container ${className}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0, display: 'block' }}
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="bl-bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0b1326" />
            <stop offset="100%" stopColor="#020617" />
          </linearGradient>
          <linearGradient id="bl-wingMain" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0284c7" />
            <stop offset="45%" stopColor="#0ea5e9" />
            <stop offset="85%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#5eead4" />
          </linearGradient>
          <linearGradient id="bl-wingCrease" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="60%" stopColor="#bae6fd" />
            <stop offset="100%" stopColor="#38bdf8" />
          </linearGradient>
          <linearGradient id="bl-wingShadow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0369a1" />
            <stop offset="100%" stopColor="#0c4a6e" />
          </linearGradient>
          <linearGradient id="bl-border" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(56, 189, 248, 0.65)" />
            <stop offset="100%" stopColor="rgba(45, 212, 191, 0.25)" />
          </linearGradient>
          <filter id="bl-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#38bdf8" floodOpacity="0.4" />
          </filter>
        </defs>

        {/* Icon Base Squircle */}
        <rect
          x="2"
          y="2"
          width="60"
          height="60"
          rx="16"
          fill="url(#bl-bgGrad)"
          stroke="url(#bl-border)"
          strokeWidth="2.2"
        />

        {/* Folded Document Sheet in Background */}
        <path
          d="M14 46V18C14 15.8 15.8 14 18 14H34L46 26V46C46 48.2 44.2 50 42 50H18C15.8 50 14 48.2 14 46Z"
          fill="#0e223d"
          fillOpacity="0.85"
        />
        <path
          d="M34 14V24C34 25.1 34.9 26 36 26H46"
          stroke="#38bdf8"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Aerodynamic Paper Plane Wing Ascent (The "Fly" Vector) */}
        <g filter="url(#bl-glow)">
          {/* Underwing Shadow */}
          <path d="M23 44L52 16L37 43L27 38Z" fill="url(#bl-wingShadow)" />

          {/* Main Lifting Wing */}
          <path d="M13 32L52 16L30 46L23 44Z" fill="url(#bl-wingMain)" />

          {/* Fold / Dorsal Ridge specular highlight */}
          <path d="M30 46L52 16L40 40L30 46Z" fill="url(#bl-wingCrease)" />

          {/* Speed particle accent */}
          <circle cx="16" cy="46" r="3" fill="#38bdf8" />
          <circle cx="16" cy="46" r="1.5" fill="#ffffff" />
        </g>
      </svg>

      {showText && (
        <span className="brand-logo-text" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ fontWeight: 800, fontSize: '18px', color: '#f8fafc', letterSpacing: '-0.02em' }}>Fly</span>
          <span
            style={{
              fontWeight: 900,
              fontSize: '17px',
              letterSpacing: '0.04em',
              background: 'linear-gradient(135deg, #38bdf8, #2dd4bf)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            FILE
          </span>
        </span>
      )}
    </div>
  );
};

export default BrandLogo;
