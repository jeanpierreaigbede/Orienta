"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { ErrorBox } from "@/components/ErrorBox";
import { api, ApiError, HOME_BY_ROLE, User } from "@/lib/api";

/** Shared by e-mail verification (patients) and invitation acceptance (agents, admins). */
export function CodeForm({ mode }: { mode: "verify" | "invitation" }) {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const path = mode === "verify" ? "/auth/verify-email" : "/auth/accept-invitation";
      const body = mode === "verify" ? { email, code } : { email, code, password };
      const { user } = await api<{ user: User }>(path, { method: "POST", body });
      router.replace(HOME_BY_ROLE[user.role]);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      await api("/auth/resend-code", { method: "POST", body: { email } });
      setInfo("Si l'adresse est en attente de vérification, un nouveau code vient d'être envoyé.");
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
    }
  }

  return (
    <form className="card stack" onSubmit={submit}>
      <ErrorBox code={error} />
      {info && <div className="alert info">{info}</div>}
      <label>
        Adresse e-mail
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>
        Code reçu par e-mail
        <input required inputMode="numeric" pattern="\d{6}" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" />
      </label>
      {mode === "invitation" && (
        <label>
          Choisissez un mot de passe (10 caractères minimum)
          <input type="password" required minLength={10} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
        </label>
      )}
      <button className="btn" disabled={busy}>{mode === "verify" ? "Vérifier mon adresse" : "Activer mon compte"}</button>
      <button type="button" className="btn secondary" onClick={resend}>Renvoyer un code</button>
    </form>
  );
}
