"use client";

import { useCallback, useEffect, useState } from "react";

import { StatusBadge } from "@/components/Badge";
import { ErrorBox } from "@/components/ErrorBox";
import { Search } from "@/components/Icons";
import { Segmented } from "@/components/Segmented";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/texts";

interface Patient { id: string; status: string; email: string; fullName: string; phoneMasked: string | null; conversations: number; createdAt: string }
type Filter = "ALL" | "ACTIVE" | "PENDING_VERIFICATION" | "DISABLED";

export default function AdminUsers() {
  const [filter, setFilter] = useState<Filter>("ALL");
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Patient[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (filter !== "ALL") params.set("status", filter);
    if (q.trim()) params.set("q", q.trim());
    const page = await api<{ items: Patient[]; counts: Record<string, number> }>(`/admin/patients?${params}`);
    setItems(page.items);
    setCounts(page.counts);
  }, [filter, q]);
  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  async function setStatus(id: string, status: "ACTIVE" | "DISABLED") {
    setError(null);
    try {
      await api(`/admin/users/${id}/status`, { method: "PATCH", body: { status } });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
    }
  }

  const n = (k: string) => (counts[k] !== undefined ? ` · ${counts[k]}` : "");
  return (
    <>
      <div className="page-head"><div><h1>Utilisateurs</h1><p>Les patients inscrits sur Orienta. Les numéros sont masqués ; le contenu des conversations n'est jamais visible ici.</p></div></div>
      <div className="row">
        <label className="search">
          <Search />
          <span className="sr-only">Rechercher un patient</span>
          <input type="search" placeholder="Rechercher par nom ou e-mail" value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <Segmented label="Filtrer par statut" value={filter} onChange={setFilter} options={[
          { value: "ALL", label: `Tous${n("ALL")}` }, { value: "ACTIVE", label: `Actifs${n("ACTIVE")}` },
          { value: "PENDING_VERIFICATION", label: `Non vérifiés${n("PENDING_VERIFICATION")}` }, { value: "DISABLED", label: `Désactivés${n("DISABLED")}` },
        ]} />
      </div>
      <ErrorBox code={error} />
      <section className="card">
        <div className="table-box">
          <table style={{ minWidth: 860 }}>
            <thead><tr><th>Nom</th><th>E-mail</th><th>Téléphone</th><th>Inscrit le</th><th>Demandes</th><th>Statut</th><th /></tr></thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td><strong>{p.fullName}</strong></td>
                  <td style={{ color: "#33405A" }}>{p.email}</td>
                  <td style={{ color: "#33405A" }}>{p.phoneMasked ?? "—"}</td>
                  <td className="muted">{formatDate(p.createdAt)}</td>
                  <td>{p.conversations}</td>
                  <td><StatusBadge status={p.status} /></td>
                  <td style={{ textAlign: "right" }}>
                    {p.status === "ACTIVE" && <button className="btn small warn" onClick={() => setStatus(p.id, "DISABLED")}>Désactiver</button>}
                    {p.status === "DISABLED" && <button className="btn small soft" onClick={() => setStatus(p.id, "ACTIVE")}>Réactiver</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 && <p className="muted" style={{ padding: 12 }}>Aucun patient trouvé.</p>}
        </div>
      </section>
    </>
  );
}
