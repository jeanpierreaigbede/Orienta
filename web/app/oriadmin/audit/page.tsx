"use client";

import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/Badge";
import { Search } from "@/components/Icons";
import { Segmented } from "@/components/Segmented";
import { api } from "@/lib/api";
import { formatDate, ROLE_LABELS } from "@/lib/texts";

interface Log { id: string; actorName: string | null; actorRole: string | null; action: string; resourceType: string; metadata: Record<string, unknown>; createdAt: string }
type Category = "ALL" | "auth" | "accounts" | "conversations" | "callbacks";

const RESOURCES: Record<string, string> = { user: "Utilisateur", conversation: "Conversation", callback_request: "Rappel", key_encryption_key: "Clé", demo: "Démo" };
const ROLE_BADGE: Record<string, string> = { PATIENT: "", HEALTH_AGENT: "ASSIGNED", ADMIN: "ACTIVE" };

function detail(m: Record<string, unknown>): string {
  return Object.entries(m).map(([k, v]) => `${k} : ${v}`).join(", ") || "—";
}

export default function AdminAudit() {
  const [category, setCategory] = useState<Category>("ALL");
  const [action, setAction] = useState("");
  const [logs, setLogs] = useState<Log[]>([]);

  useEffect(() => {
    const params = new URLSearchParams({ limit: "200" });
    if (category !== "ALL") params.set("category", category);
    if (action.trim()) params.set("action", action.trim());
    const t = setTimeout(() => api<Log[]>(`/admin/audit-logs?${params}`).then(setLogs), 250);
    return () => clearTimeout(t);
  }, [category, action]);

  return (
    <>
      <div className="page-head"><div><h1>Journal d'audit</h1><p>Qui a fait quoi, et quand. Le journal ne contient jamais le contenu des messages.</p></div></div>
      <div className="row">
        <label className="search">
          <Search />
          <span className="sr-only">Filtrer par action</span>
          <input type="search" placeholder="Filtrer par action, ex. conversation.read" value={action} onChange={(e) => setAction(e.target.value)} />
        </label>
        <Segmented label="Catégorie" value={category} onChange={setCategory} options={[
          { value: "ALL", label: "Tout" }, { value: "auth", label: "Connexions" }, { value: "accounts", label: "Comptes" },
          { value: "conversations", label: "Conversations" }, { value: "callbacks", label: "Rappels" },
        ]} />
      </div>
      <section className="card">
        <div className="table-box">
          <table style={{ minWidth: 900 }}>
            <thead><tr><th>Date</th><th>Action</th><th>Acteur</th><th>Rôle</th><th>Ressource</th><th>Détail</th></tr></thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td className="muted" style={{ whiteSpace: "nowrap" }}>{formatDate(l.createdAt)}</td>
                  <td className="mono">{l.action}</td>
                  <td><strong>{l.actorName ?? "—"}</strong></td>
                  <td>{l.actorRole ? <StatusBadge status={ROLE_BADGE[l.actorRole]} label={ROLE_LABELS[l.actorRole]} /> : <span className="muted">Inconnu</span>}</td>
                  <td>{RESOURCES[l.resourceType] ?? l.resourceType}</td>
                  <td className="muted">{detail(l.metadata)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {logs.length === 0 && <p className="muted" style={{ padding: 12 }}>Aucun événement.</p>}
        </div>
      </section>
    </>
  );
}
