"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { ErrorBox } from "@/components/ErrorBox";
import { TopBar } from "@/components/TopBar";
import { api, ApiError } from "@/lib/api";
import { DISCLAIMER, formatDate, ORIENTATION_LABELS, STATUS_LABELS } from "@/lib/texts";
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

  if (!user) return <TopBar />;

  return (
    <main>
      <TopBar user={user} />
      <div className="container stack">
        <h1>Bonjour {user.fullName.split(" ")[0]}</h1>
        <div className="alert warning">{DISCLAIMER}</div>
        <form className="card stack" onSubmit={start}>
          <h2>Nouvelle demande</h2>
          <ErrorBox code={error} />
          <label>
            Décrivez ce que vous ressentez
            <textarea rows={4} required maxLength={2000} value={content} onChange={(e) => setContent(e.target.value)}
              placeholder="Par exemple : j'ai de la fièvre et mal à la tête depuis hier." />
          </label>
          <button className="btn" disabled={busy}>{busy ? "L'assistant réfléchit…" : "Envoyer"}</button>
        </form>
        <div className="card">
          <h2>Mes demandes</h2>
          {items.length === 0 ? (
            <p className="muted">Aucune demande pour le moment.</p>
          ) : (
            <table>
              <thead>
                <tr><th>Date</th><th>Statut</th><th>Orientation</th><th /></tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <tr key={c.id}>
                    <td>{formatDate(c.createdAt)}</td>
                    <td><span className={`badge ${c.status}`}>{STATUS_LABELS[c.status]}</span></td>
                    <td>{c.orientationLevel ? <span className={`badge ${c.orientationLevel}`}>{ORIENTATION_LABELS[c.orientationLevel]}</span> : "—"}</td>
                    <td><a href={`/patient/conversations/${c.id}`}>Ouvrir</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </main>
  );
}
