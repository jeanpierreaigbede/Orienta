"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ErrorBox } from "@/components/ErrorBox";
import { TopBar } from "@/components/TopBar";
import { api, ApiError } from "@/lib/api";
import { CONSENT_VERSION } from "@/lib/texts";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ fullName: "", email: "", phone: "", password: "" });
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/register", {
        method: "POST",
        body: { ...form, phone: form.phone || null, consentVersion: CONSENT_VERSION },
      });
      router.push(`/verify?email=${encodeURIComponent(form.email)}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <TopBar />
      <div className="container narrow">
        <h1>Créer un compte</h1>
        <p className="lead">Un code de vérification vous sera envoyé par e-mail.</p>
        <form className="card stack" onSubmit={submit}>
          <ErrorBox code={error} />
          <label>
            Nom complet
            <input required minLength={2} value={form.fullName} onChange={set("fullName")} autoComplete="name" />
          </label>
          <label>
            Adresse e-mail
            <input type="email" required value={form.email} onChange={set("email")} autoComplete="email" />
          </label>
          <label>
            Téléphone (pour être rappelé en cas d'urgence)
            <input type="tel" value={form.phone} onChange={set("phone")} placeholder="+229 01 97 12 34 56" autoComplete="tel" />
          </label>
          <label>
            Mot de passe (10 caractères minimum)
            <input type="password" required minLength={10} value={form.password} onChange={set("password")} autoComplete="new-password" />
          </label>
          <label style={{ flexDirection: "row", fontWeight: 400, alignItems: "flex-start" }}>
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 3 }} />
            J'accepte que mes symptômes soient traités par l'assistant pour m'orienter, et qu'un agent de santé de l'ONG
            puisse me rappeler en cas d'urgence.
          </label>
          <button className="btn" disabled={busy || !consent}>Créer mon compte</button>
        </form>
      </div>
    </main>
  );
}
