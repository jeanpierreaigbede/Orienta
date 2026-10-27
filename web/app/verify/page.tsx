"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { CodeForm } from "@/components/CodeForm";
import { Back, Mail } from "@/components/Icons";

function Intro() {
  const email = useSearchParams().get("email");
  return (
    <p className="muted" style={{ fontSize: 15, lineHeight: 1.55 }}>
      Nous avons envoyé un code à 6 chiffres{email ? <> à <strong style={{ color: "#0F1B2D" }}>{email}</strong></> : null}. Il est valable 10 minutes.
    </p>
  );
}

export default function VerifyPage() {
  return (
    <main className="phone">
      <div style={{ padding: 12 }}><a className="icon-btn" href="/register" aria-label="Retour à l'inscription" style={{ color: "#0B1F3A" }}><Back /></a></div>
      <div className="phone-body" style={{ gap: 24, paddingTop: 8 }}>
        <span style={{ width: 64, height: 64, borderRadius: 20, background: "#0B1F3A", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}><Mail /></span>
        <h1 style={{ fontSize: 28 }}>Vérifiez votre e-mail</h1>
        <Suspense>
          <Intro />
          <CodeForm mode="verify" />
        </Suspense>
      </div>
    </main>
  );
}
