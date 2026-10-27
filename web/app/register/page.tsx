"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ErrorBox } from "@/components/ErrorBox";
import { Back } from "@/components/Icons";
import { PasswordInput } from "@/components/PasswordInput";
import { api, ApiError } from "@/lib/api";
import { CONSENT_VERSION } from "@/lib/texts";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ fullName: "", email: "", phone: "" });
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/register", { method: "POST", body: { ...form, password, phone: form.phone || null, consentVersion: CONSENT_VERSION } });
      router.push(`/verify?email=${encodeURIComponent(form.email)}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
      setBusy(false);
    }
  }

  return (
    <main className="phone">
      <header style={{ background: "#0B1F3A", color: "#fff", padding: "12px 12px 24px" }}>
        <a className="icon-btn" href="/" aria-label="Retour à l'accueil"><Back /></a>
        <div style={{ padding: "8px 12px 0" }}>
          <h1 style={{ color: "#fff", fontSize: 26 }}>Créer mon compte</h1>
          <p style={{ color: "#C9D8EE", fontSize: 14, marginTop: 6 }}>Un code de vérification vous sera envoyé par e-mail.</p>
        </div>
      </header>
      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", flex: 1 }}>
        <div className="phone-body">
          <ErrorBox code={error} />
          <label className="field">Nom complet
            <input className="input" required minLength={2} value={form.fullName} onChange={set("fullName")} autoComplete="name" />
          </label>
          <label className="field">Adresse e-mail
            <input className="input" type="email" required value={form.email} onChange={set("email")} autoComplete="email" />
          </label>
          <label className="field">Téléphone
            <input className="input" type="tel" value={form.phone} onChange={set("phone")} placeholder="+229 01 97 12 34 56" autoComplete="tel" />
            <small>Pour qu'un agent puisse vous rappeler en cas d'urgence.</small>
          </label>
          <label className="field">Mot de passe
            <PasswordInput value={password} onChange={setPassword} autoComplete="new-password" minLength={10} />
            <small>10 caractères minimum.</small>
          </label>
          <label style={{ display: "flex", gap: 12, alignItems: "flex-start", fontSize: 13, lineHeight: 1.5, color: "#33405A", background: "#fff", border: "1px solid #DCE3EC", borderRadius: 12, padding: 14 }}>
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ width: 20, height: 20, margin: "1px 0 0", accentColor: "#1769E0", flexShrink: 0 }} />
            J'accepte que mes symptômes soient traités par l'assistant pour m'orienter, et qu'un agent de santé de l'ONG me rappelle en cas d'urgence.
          </label>
        </div>
        <div className="phone-foot">
          <button className="btn block" disabled={busy || !consent}>Recevoir mon code</button>
          <p className="muted" style={{ textAlign: "center", fontSize: 13 }}>Déjà inscrit ? <a href="/login" style={{ fontWeight: 700, textDecoration: "none" }}>Se connecter</a></p>
        </div>
      </form>
    </main>
  );
}
