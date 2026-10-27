"use client";

import { useEffect, useState } from "react";

export function HealthBadge() {
  const [state, setState] = useState<"loading" | "ok" | "down">("loading");

  useEffect(() => {
    fetch("/api/v1/health/ready")
      .then((r) => setState(r.ok ? "ok" : "down"))
      .catch(() => setState("down"));
  }, []);

  if (state === "loading") return <div className="alert info">Vérification de l'API…</div>;
  if (state === "ok") return <div className="alert info">API et base de données joignables.</div>;
  return <div className="alert error">L'API ne répond pas : vérifiez qu'elle tourne sur le port 8000.</div>;
}
