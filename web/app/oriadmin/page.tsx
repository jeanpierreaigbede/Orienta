"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { ErrorBox } from "@/components/ErrorBox";
import { TopBar } from "@/components/TopBar";
import { api, ApiError, User } from "@/lib/api";
import { formatDate, ROLE_LABELS, STATUS_LABELS } from "@/lib/texts";
import { useSession } from "@/lib/useSession";

interface AuditLog {
  id: string;
  actorRole: string | null;
  action: string;
  resourceType: string;
  createdAt: string;
}

export default function AdminSpace() {
  const user = useSession("ADMIN");
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [invite, setInvite] = useState({ email: "", fullName: "", role: "HEALTH_AGENT" });
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    setUsers(await api<User[]>("/admin/users"));
    setLogs(await api<AuditLog[]>("/admin/audit-logs?limit=30"));
  }, []);
  useEffect(() => {
    if (user) load();
  }, [user, load]);

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

  function submitInvite(e: FormEvent) {
    e.preventDefault();
    run(async () => {
      await api("/admin/users", { method: "POST", body: invite });
      setInvite({ email: "", fullName: "", role: "HEALTH_AGENT" });
    }, "Invitation envoyée. Le code d'activation est dans la boîte mail de la personne invitée.");
  }

  if (!user) return <TopBar />;

  return (
    <main>
      <TopBar user={user} />
      <div className="container stack">
        <h1>Administration</h1>
        <ErrorBox code={error} />
        {info && <div className="alert info">{info}</div>}
        <form className="card stack" onSubmit={submitInvite}>
          <h2>Inviter un membre de l'équipe</h2>
          <div className="row">
            <input required placeholder="Nom complet" value={invite.fullName} onChange={(e) => setInvite({ ...invite, fullName: e.target.value })} />
            <input required type="email" placeholder="Adresse e-mail" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} />
            <select value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}>
              <option value="HEALTH_AGENT">Agent de santé</option>
              <option value="ADMIN">Administrateur</option>
            </select>
            <button className="btn">Inviter</button>
          </div>
        </form>
        <div className="card">
          <h2>Comptes</h2>
          <table>
            <thead><tr><th>Nom</th><th>E-mail</th><th>Rôle</th><th>Statut</th><th /></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.fullName}</td>
                  <td>{u.email}</td>
                  <td>{ROLE_LABELS[u.role]}</td>
                  <td><span className={`badge ${u.status}`}>{STATUS_LABELS[u.status]}</span></td>
                  <td>
                    {u.id !== user.id && u.status === "ACTIVE" && (
                      <button className="btn small danger" onClick={() => run(() => api(`/admin/users/${u.id}/status`, { method: "PATCH", body: { status: "DISABLED" } }))}>Désactiver</button>
                    )}
                    {u.status === "DISABLED" && (
                      <button className="btn small secondary" onClick={() => run(() => api(`/admin/users/${u.id}/status`, { method: "PATCH", body: { status: "ACTIVE" } }))}>Réactiver</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h2>Journal d'audit (30 derniers événements)</h2>
          <table>
            <thead><tr><th>Date</th><th>Action</th><th>Rôle</th><th>Ressource</th></tr></thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td className="muted">{formatDate(l.createdAt)}</td>
                  <td className="mono">{l.action}</td>
                  <td>{l.actorRole ? ROLE_LABELS[l.actorRole] : "Système"}</td>
                  <td>{l.resourceType}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
