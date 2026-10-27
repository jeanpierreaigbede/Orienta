"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { StatusBadge } from "@/components/Badge";
import { ErrorBox } from "@/components/ErrorBox";
import { Segmented } from "@/components/Segmented";
import { api, ApiError, User } from "@/lib/api";
import { formatDate, ROLE_LABELS } from "@/lib/texts";

interface Member { id: string; role: string; status: string; email: string; fullName: string; callbacksInProgress: number; callbacksClosed30Days: number; lastLoginAt: string | null }
type Filter = "ALL" | "HEALTH_AGENT" | "ADMIN";

export default function AdminAgents() {
  const [me, setMe] = useState<User | null>(null);
  const [filter, setFilter] = useState<Filter>("ALL");
  const [items, setItems] = useState<Member[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [invite, setInvite] = useState({ fullName: "", email: "", role: "HEALTH_AGENT" });
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    const page = await api<{ items: Member[]; counts: Record<string, number> }>(`/admin/team${filter === "ALL" ? "" : `?role=${filter}`}`);
    setItems(page.items);
    setCounts(page.counts);
  }, [filter]);
  useEffect(() => {
    api<User>("/auth/me").then(setMe);
    load();
  }, [load]);

  async function run(action: () => Promise<unknown>, success?: string) {
    setError(null);
    setInfo(null);
    try {
      await action();
      if (success) setInfo(success);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    run(async () => {
      await api("/admin/team", { method: "POST", body: invite });
      setInvite({ fullName: "", email: "", role: "HEALTH_AGENT" });
    }, "Invitation envoyée : la personne reçoit un code par e-mail.");
  }

  const n = (k: string) => (counts[k] !== undefined ? ` · ${counts[k]}` : "");
  return (
    <>
      <div className="page-head">
        <div><h1>Agents de santé</h1><p>L'équipe qui rappelle les patients orientés en urgence, et les administrateurs.</p></div>
        <Segmented label="Filtrer par rôle" value={filter} onChange={setFilter} options={[
          { value: "ALL", label: `Tous${n("ALL")}` }, { value: "HEALTH_AGENT", label: `Agents${n("HEALTH_AGENT")}` }, { value: "ADMIN", label: `Administrateurs${n("ADMIN")}` },
        ]} />
      </div>
      <form className="card stack" onSubmit={submit}>
        <h2>Inviter un membre de l'équipe</h2>
        <div className="row" style={{ alignItems: "flex-end" }}>
          <label className="field" style={{ flex: "1 1 200px", fontSize: 13 }}>Nom complet
            <input className="input" required minLength={2} value={invite.fullName} onChange={(e) => setInvite({ ...invite, fullName: e.target.value })} style={{ height: 44 }} />
          </label>
          <label className="field" style={{ flex: "1 1 240px", fontSize: 13 }}>Adresse e-mail
            <input className="input" type="email" required value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} style={{ height: 44 }} />
          </label>
          <label className="field" style={{ flex: "0 1 190px", fontSize: 13 }}>Rôle
            <select className="input" value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })} style={{ height: 44 }}>
              <option value="HEALTH_AGENT">Agent de santé</option>
              <option value="ADMIN">Administrateur</option>
            </select>
          </label>
          <button className="btn" style={{ minHeight: 44 }}>Envoyer l'invitation</button>
        </div>
        <p className="muted" style={{ fontSize: 13 }}>La personne reçoit un code par e-mail et choisit elle-même son mot de passe.</p>
      </form>
      <ErrorBox code={error} />
      {info && <div className="alert info">{info}</div>}
      <section className="card stack">
        <h2>Équipe</h2>
        <div className="table-box">
          <table style={{ minWidth: 960 }}>
            <thead><tr><th>Nom</th><th>E-mail</th><th>Rôle</th><th>Rappels en cours</th><th>Traités (30 j)</th><th>Dernière connexion</th><th>Statut</th><th /></tr></thead>
            <tbody>
              {items.map((m) => (
                <tr key={m.id}>
                  <td><strong>{m.fullName}</strong></td>
                  <td style={{ color: "#33405A" }}>{m.email}</td>
                  <td>{ROLE_LABELS[m.role]}</td>
                  <td>{m.role === "HEALTH_AGENT" ? m.callbacksInProgress : "—"}</td>
                  <td>{m.role === "HEALTH_AGENT" ? m.callbacksClosed30Days : "—"}</td>
                  <td className="muted">{m.lastLoginAt ? formatDate(m.lastLoginAt) : "Jamais"}</td>
                  <td><StatusBadge status={m.status} label={m.status === "PENDING_VERIFICATION" ? "Invitation envoyée" : undefined} /></td>
                  <td style={{ textAlign: "right" }}>
                    {m.id === me?.id ? <span className="muted" style={{ fontSize: 13 }}>Vous</span>
                      : m.status === "PENDING_VERIFICATION" ? <button className="btn small soft" onClick={() => run(() => api(`/admin/team/${m.id}/resend-invitation`, { method: "POST" }), "Invitation renvoyée.")}>Renvoyer l'invitation</button>
                      : m.status === "ACTIVE" ? <button className="btn small warn" onClick={() => run(() => api(`/admin/users/${m.id}/status`, { method: "PATCH", body: { status: "DISABLED" } }))}>Désactiver</button>
                      : <button className="btn small soft" onClick={() => run(() => api(`/admin/users/${m.id}/status`, { method: "PATCH", body: { status: "ACTIVE" } }))}>Réactiver</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
