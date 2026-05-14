export function FramingOverlay() {
  const corner = 24;
  const strokeW = 0.3;

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <mask id="frame-mask">
        <rect width="100" height="100" fill="white" />
        <rect x="8" y="20" width="84" height="60" rx="2" fill="black" />
      </mask>
      <rect
        width="100"
        height="100"
        fill="rgba(0,0,0,0.45)"
        mask="url(#frame-mask)"
      />
      {/* top-left */}
      <path
        d={`M 8 ${20 + corner} L 8 20 L ${8 + corner} 20`}
        fill="none"
        stroke="white"
        strokeWidth={strokeW}
      />
      {/* top-right */}
      <path
        d={`M ${92 - corner} 20 L 92 20 L 92 ${20 + corner}`}
        fill="none"
        stroke="white"
        strokeWidth={strokeW}
      />
      {/* bottom-left */}
      <path
        d={`M 8 ${80 - corner} L 8 80 L ${8 + corner} 80`}
        fill="none"
        stroke="white"
        strokeWidth={strokeW}
      />
      {/* bottom-right */}
      <path
        d={`M ${92 - corner} 80 L 92 80 L 92 ${80 - corner}`}
        fill="none"
        stroke="white"
        strokeWidth={strokeW}
      />
    </svg>
  );
}
