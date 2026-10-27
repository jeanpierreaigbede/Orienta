"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ErrorBox } from "@/components/ErrorBox";
import { Logo } from "@/components/Logo";
import { PasswordInput } from "@/components/PasswordInput";
import { api, ApiError, HOME_BY_ROLE, User } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { user } = await api<{ user: User }>("/auth/login", { method: "POST", body: { email, password } });
      router.replace(HOME_BY_ROLE[user.role]);
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "HTTP_ERROR";
      if (code === "EMAIL_NOT_VERIFIED") router.push(`/verify?email=${encodeURIComponent(email)}`);
      setError(code);
      setBusy(false);
    }
  }

  return (
    <main className="split">
      <section className="split-art">
        <Logo />
        <img src="/login-illustration.svg" alt="Un patient échange avec l'assistant sur son téléphone, ses données sont protégées et un agent de santé le rappelle" />
        <p>Décrivez vos symptômes, Orienta vous oriente vers le bon niveau de soins.</p>
      </section>
      <section className="split-form">
        <form onSubmit={submit}>
          <div>
            <h1>Connexion</h1>
            <p className="muted" style={{ fontSize: 15, marginTop: 6 }}>Retrouvez vos demandes et leur suivi.</p>
          </div>
          <ErrorBox code={error} />
          <label className="field">
            Adresse e-mail
            <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </label>
          <label className="field">
            Mot de passe
            <PasswordInput value={password} onChange={setPassword} autoComplete="current-password" />
          </label>
          <button className="btn block" disabled={busy}>Se connecter</button>
          <p className="muted">Pas encore de compte ? <a href="/register" style={{ fontWeight: 700, textDecoration: "none" }}>Créer un compte patient</a></p>
          <p className="muted" style={{ fontSize: 13 }}>Vous faites partie de l'équipe de l'ONG ? Activez votre compte avec le lien reçu par e-mail.</p>
        </form>
      </section>
    </main>
  );
}
