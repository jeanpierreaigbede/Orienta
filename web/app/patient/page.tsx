"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { LevelBadge, StatusBadge } from "@/components/Badge";
import { ErrorBox } from "@/components/ErrorBox";
import { PatientHeader } from "@/components/PatientHeader";
import { api, ApiError } from "@/lib/api";
import { DISCLAIMER, formatDate } from "@/lib/texts";
import { Conversation, ConversationSummary } from "@/lib/types";
import { useSession } from "@/lib/useSession";

export default function PatientHome() {
  const user = useSession("PATIENT");
  const router = useRouter();
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) api<{ items: ConversationSummary[] }>("/conversations").then((p) => setItems(p.items));
  }, [user]);

  async function start(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const conversation = await api<Conversation>("/conversations", { method: "POST", body: { content } });
      router.push(`/patient/conversations/${conversation.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <main className="phone">
      <PatientHeader />
      <div className="phone-body">
        <h1 style={{ fontSize: 26 }}>Bonjour {user.fullName.split(" ")[0]}</h1>
        <form className="card stack" onSubmit={start} style={{ padding: 18 }}>
          <h2>Nouvelle demande</h2>
          <ErrorBox code={error} />
          <label className="field">Décrivez ce que vous ressentez
            <textarea className="input" rows={4} required maxLength={2000} value={content} onChange={(e) => setContent(e.target.value)}
              placeholder="Par exemple : j'ai de la fièvre et mal à la tête depuis hier." />
          </label>
          <button className="btn block" disabled={busy}>{busy ? "L'assistant réfléchit…" : "Envoyer"}</button>
        </form>
        <h2 style={{ marginTop: 8 }}>Mes demandes</h2>
        {items.length === 0 ? (
          <p className="muted">Aucune demande pour le moment.</p>
        ) : (
          items.map((c) => (
            <a key={c.id} href={`/patient/conversations/${c.id}`} className="level-card" style={{ justifyContent: "space-between", textDecoration: "none", color: "inherit" }}>
              <span style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <strong style={{ fontSize: 15 }}>{formatDate(c.createdAt)}</strong>
                <StatusBadge status={c.status} />
              </span>
              <LevelBadge level={c.orientationLevel} />
            </a>
          ))
        )}
        <p className="disclaimer">{DISCLAIMER}</p>
      </div>
    </main>
  );
}
