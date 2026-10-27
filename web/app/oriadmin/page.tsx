"use client";

import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/Badge";
import { api } from "@/lib/api";
import { formatDate, waiting } from "@/lib/texts";

interface Overview {
  patients: number;
  patientsThisWeek: number;
  activeAgents: number;
  pendingInvitations: number;
  conversationsInProgress: number;
  urgentWaiting: number;
  oldestUrgentMinutes: number | null;
  urgent: { callbackId: string; patientName: string; orientedAt: string | null; waitingMinutes: number | null; status: string; agentName: string | null }[];
}

export default function AdminOverview() {
  const [data, setData] = useState<Overview | null>(null);
  useEffect(() => {
    api<Overview>("/admin/overview").then(setData);
  }, []);
  if (!data) return null;

  const kpis = [
    { label: "Patients inscrits", value: data.patients, sub: `+${data.patientsThisWeek} cette semaine` },
    { label: "Agents de santé actifs", value: data.activeAgents, sub: data.pendingInvitations ? `${data.pendingInvitations} invitation(s) en attente` : "Aucune invitation en attente" },
    { label: "Orientations en cours", value: data.conversationsInProgress, sub: "conversations ouvertes" },
    { label: "Urgences à rappeler", value: data.urgentWaiting, sub: data.oldestUrgentMinutes !== null ? `la plus ancienne : ${waiting(data.oldestUrgentMinutes)}` : "aucune en attente", urgent: true },
  ];

  return (
    <>
      <div className="page-head"><div><h1>Vue d'ensemble</h1><p>Activité de l'assistant et de l'équipe de rappel.</p></div></div>
      <div className="kpis">
        {kpis.map((k) => (
          <div key={k.label} className="card kpi">
            <span className="label">{k.label}</span>
            <span className={`value ${k.urgent && k.value > 0 ? "urgent" : ""}`}>{k.value}</span>
            <span className="muted" style={{ fontSize: 13 }}>{k.sub}</span>
          </div>
        ))}
      </div>
      <section className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2>Urgences en attente de rappel</h2>
          <a href="/oriadmin/orientations" style={{ fontSize: 14, fontWeight: 700, textDecoration: "none", padding: "10px 0" }}>Toutes les orientations</a>
        </div>
        {data.urgent.length === 0 && <p className="muted" style={{ paddingTop: 8 }}>Aucune urgence en attente.</p>}
        {data.urgent.map((u) => (
          <div key={u.callbackId} className="row" style={{ justifyContent: "space-between", padding: "12px 0", borderBottom: "1px solid #EEF2F6" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <strong style={{ fontSize: 15 }}>{u.patientName}</strong>
              <span className="muted" style={{ fontSize: 13 }}>Orientée {formatDate(u.orientedAt)}{u.waitingMinutes !== null ? ` · en attente depuis ${waiting(u.waitingMinutes)}` : ""}</span>
            </div>
            {u.agentName ? <StatusBadge status="ASSIGNED" label={u.agentName} /> : <StatusBadge status="PENDING" label="Non attribué" />}
          </div>
        ))}
      </section>
    </>
  );
}
