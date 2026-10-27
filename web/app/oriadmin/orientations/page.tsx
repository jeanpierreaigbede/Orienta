"use client";

import { useEffect, useState } from "react";

import { LevelBadge, StatusBadge } from "@/components/Badge";
import { Segmented } from "@/components/Segmented";
import { api } from "@/lib/api";
import { formatDate, waiting } from "@/lib/texts";

interface Item {
  id: string; createdAt: string; patientName: string; status: string; orientationLevel: string | null; followUpCount: number;
  callback: { status: string; agentName: string | null; waitingMinutes: number | null } | null;
}
interface Page {
  stats: { inProgress: number; urgentWaiting: number; averageCallbackDelayMinutes: number | null; averageQuestions: number | null };
  counts: Record<string, number>;
  items: Item[];
}
type Status = "ALL" | "IN_PROGRESS" | "ORIENTED" | "ABANDONED";
type Level = "ALL" | "EMERGENCY" | "CONSULTATION_48H" | "HOME_CARE";

function callbackText(c: Item["callback"]) {
  if (!c) return <span className="muted">—</span>;
  if (c.status === "PENDING") return <strong style={{ color: "#8A3F06" }}>En attente · {waiting(c.waitingMinutes)}</strong>;
  if (c.status === "ASSIGNED") return <span>Pris par {c.agentName}</span>;
  return <StatusBadge status={c.status} />;
}

export default function AdminOrientations() {
  const [status, setStatus] = useState<Status>("ALL");
  const [level, setLevel] = useState<Level>("ALL");
  const [page, setPage] = useState<Page | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (status !== "ALL") params.set("status", status);
    if (level !== "ALL") params.set("level", level);
    api<Page>(`/admin/orientations?${params}`).then(setPage);
  }, [status, level]);

  const n = (k: string) => (page?.counts[k] !== undefined ? ` · ${page.counts[k]}` : "");
  const s = page?.stats;
  const stats = [
    { label: "Conversations en cours", value: s?.inProgress ?? "—" },
    { label: "Urgences en attente", value: s?.urgentWaiting ?? "—", urgent: true },
    { label: "Délai moyen de rappel", value: s?.averageCallbackDelayMinutes != null ? `${s.averageCallbackDelayMinutes} min` : "—" },
    { label: "Questions posées en moyenne", value: s?.averageQuestions != null ? String(s.averageQuestions).replace(".", ",") : "—" },
  ];

  return (
    <>
      <div className="page-head"><div><h1>Orientations</h1><p>Les demandes des patients et leur suivi. Le contenu des conversations n'est visible que par l'agent qui prend le rappel.</p></div></div>
      <div className="kpis">
        {stats.map((k) => (
          <div key={k.label} className="card kpi" style={{ padding: "16px 18px" }}>
            <span className="label">{k.label}</span>
            <span className={`value ${k.urgent && Number(k.value) > 0 ? "urgent" : ""}`} style={{ fontSize: 26 }}>{k.value}</span>
          </div>
        ))}
      </div>
      <div className="row">
        <Segmented label="Filtrer par statut" value={status} onChange={setStatus} options={[
          { value: "ALL", label: `Toutes${n("ALL")}` }, { value: "IN_PROGRESS", label: `En cours${n("IN_PROGRESS")}` },
          { value: "ORIENTED", label: `Orientées${n("ORIENTED")}` }, { value: "ABANDONED", label: `Abandonnées${n("ABANDONED")}` },
        ]} />
        <Segmented label="Filtrer par niveau" value={level} onChange={setLevel} options={[
          { value: "ALL", label: "Tous niveaux" }, { value: "EMERGENCY", label: "Urgence" }, { value: "CONSULTATION_48H", label: "48 h" }, { value: "HOME_CARE", label: "Domicile" },
        ]} />
      </div>
      <section className="card">
        <div className="table-box">
          <table style={{ minWidth: 820 }}>
            <thead><tr><th>Reçue</th><th>Patient</th><th>Statut</th><th>Niveau</th><th>Questions</th><th>Rappel</th></tr></thead>
            <tbody>
              {page?.items.map((i) => (
                <tr key={i.id}>
                  <td className="muted">{formatDate(i.createdAt)}</td>
                  <td><strong>{i.patientName}</strong></td>
                  <td><StatusBadge status={i.status} /></td>
                  <td><LevelBadge level={i.orientationLevel} /></td>
                  <td>{i.followUpCount}</td>
                  <td>{callbackText(i.callback)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {page && page.items.length === 0 && <p className="muted" style={{ padding: 12 }}>Aucune orientation.</p>}
        </div>
      </section>
    </>
  );
}
