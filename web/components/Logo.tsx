/** Logo A, "Boussole": a health cross whose top arm is a compass needle. */
export function LogoMark({ size = 26, tone = "onBlue" }: { size?: number; tone?: "onBlue" | "onWhite" }) {
  const ring = tone === "onBlue" ? "#FFFFFF" : "#0B1F3A";
  const needle = tone === "onBlue" ? "#0B1F3A" : "#1769E0";
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden="true">
      <circle cx="60" cy="60" r="52" fill="none" stroke={ring} strokeWidth="9" />
      <path d="M60 14 L72 48 H48 Z" fill={needle} />
      <rect x="48" y="48" width="24" height="44" rx="4" fill={ring} />
      <rect x="26" y="48" width="68" height="24" rx="4" fill={ring} />
    </svg>
  );
}

export function Logo({ href = "/", subtitle }: { href?: string; subtitle?: string }) {
  return (
    <a className="logo" href={href} aria-label="Orienta, accueil">
      <span className="logo-tile">
        <LogoMark />
      </span>
      <span style={{ display: "flex", flexDirection: "column" }}>
        <span className="logo-word">Orienta</span>
        {subtitle && <span style={{ fontSize: 12, color: "#9DB4D6" }}>{subtitle}</span>}
      </span>
    </a>
  );
}
