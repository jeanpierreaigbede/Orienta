"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ErrorBox } from "@/components/ErrorBox";
import { TopBar } from "@/components/TopBar";
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
      // The role decides the space: /patient, /oriagent or /oriadmin.
      router.replace(HOME_BY_ROLE[user.role]);
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "HTTP_ERROR";
      if (code === "EMAIL_NOT_VERIFIED") router.push(`/verify?email=${encodeURIComponent(email)}`);
      setError(code);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <TopBar />
      <div className="container narrow">
        <h1>Connexion</h1>
        <p className="lead">Patients, agents de santé et administrateurs utilisent le même formulaire.</p>
        <form className="card stack" onSubmit={submit}>
          <ErrorBox code={error} />
          <label>
            Adresse e-mail
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </label>
          <label>
            Mot de passe
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </label>
          <button className="btn" disabled={busy}>Se connecter</button>
          <p className="muted">Pas encore de compte ? <a href="/register">Créer un compte patient</a></p>
        </form>
      </div>
    </main>
  );
}
