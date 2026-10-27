"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { ErrorBox } from "@/components/ErrorBox";
import { PasswordInput } from "@/components/PasswordInput";
import { api, ApiError, HOME_BY_ROLE, User } from "@/lib/api";

/** Shared by e-mail verification (patients) and invitation acceptance (team members). */
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
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      await api("/auth/resend-code", { method: "POST", body: { email } });
      setInfo("Un nouveau code vient d'être envoyé.");
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
    }
  }

  return (
    <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <ErrorBox code={error} />
      {info && <div className="alert info">{info}</div>}
      {!params.get("email") && (
        <label className="field">Adresse e-mail
          <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
      )}
      <label className="field">Code reçu par e-mail
        <input className="input" required inputMode="numeric" pattern="\d{6}" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)}
          placeholder="••••••" style={{ height: 58, fontSize: 26, fontWeight: 700, letterSpacing: 14, textAlign: "center" }} autoComplete="one-time-code" />
      </label>
      {mode === "invitation" && (
        <label className="field">Choisissez un mot de passe
          <PasswordInput value={password} onChange={setPassword} autoComplete="new-password" minLength={10} />
          <small>10 caractères minimum.</small>
        </label>
      )}
      <div className="row" style={{ justifyContent: "space-between", fontSize: 14 }}>
        <span className="muted">Pas reçu ? Vérifiez vos spams.</span>
        <button type="button" className="btn small soft" onClick={resend}>Renvoyer le code</button>
      </div>
      <button className="btn block" disabled={busy}>{mode === "verify" ? "Vérifier mon adresse" : "Activer mon compte"}</button>
    </form>
  );
}
