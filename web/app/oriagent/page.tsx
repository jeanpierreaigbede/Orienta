"use client";

import { useCallback, useEffect, useState } from "react";

import { Chat } from "@/components/Chat";
import { ErrorBox } from "@/components/ErrorBox";
import { TopBar } from "@/components/TopBar";
import { api, ApiError } from "@/lib/api";
import { formatDate, ORIENTATION_LABELS, STATUS_LABELS } from "@/lib/texts";
import { Callback, Conversation } from "@/lib/types";
import { useSession } from "@/lib/useSession";

export default function AgentSpace() {
  const user = useSession("HEALTH_AGENT");
  const [callbacks, setCallbacks] = useState<Callback[]>([]);
  const [selected, setSelected] = useState<Callback | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => api<Callback[]>("/agent/callbacks").then(setCallbacks), []);
  useEffect(() => {
    if (user) load();
  }, [user, load]);

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
    }
  }

  async function open(callback: Callback) {
    setSelected(callback);
    setConversation(await api<Conversation>(`/agent/callbacks/${callback.id}/conversation`));
  }

  function close(outcome: "COMPLETED" | "UNREACHABLE") {
    if (!selected) return;
    run(async () => {
      await api(`/agent/callbacks/${selected.id}/close`, { method: "POST", body: { outcome, note: note || null } });
      setSelected(null);
      setConversation(null);
      setNote("");
    });
  }

  if (!user) return <TopBar />;

  return (
    <main>
      <TopBar user={user} />
      <div className="container stack">
        <h1>Patients à rappeler</h1>
        <p className="lead">Patients orientés en urgence par l'assistant. Prenez un rappel pour lire la conversation.</p>
        <ErrorBox code={error} />
        <div className="grid-2">
          <div className="card">
            {callbacks.length === 0 ? (
              <p className="muted">Aucun rappel en attente.</p>
            ) : (
              <table>
                <thead><tr><th>Patient</th><th>Statut</th><th>Reçu</th><th /></tr></thead>
                <tbody>
                  {callbacks.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <strong>{c.patientName}</strong>
                        <div className="muted">{c.patientPhone ?? "Pas de téléphone"}</div>
                      </td>
                      <td><span className={`badge ${c.status}`}>{STATUS_LABELS[c.status]}</span></td>
                      <td className="muted">{formatDate(c.createdAt)}</td>
                      <td>
                        {c.status === "PENDING" && (
                          <button className="btn small" onClick={() => run(() => api(`/agent/callbacks/${c.id}/assign`, { method: "POST" }))}>Prendre</button>
                        )}
                        {c.assignedToMe && c.status === "ASSIGNED" && (
                          <button className="btn small secondary" onClick={() => open(c)}>Ouvrir</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="card stack">
            {selected && conversation ? (
              <>
                <h2>{selected.patientName}</h2>
                <p className="muted">
                  {selected.patientPhone ?? "Pas de téléphone"} · {selected.orientationLevel ? ORIENTATION_LABELS[selected.orientationLevel] : ""}
                </p>
                <Chat messages={conversation.messages} />
                <label>
                  Note de suivi
                  <textarea rows={3} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />
                </label>
                <div className="row">
                  <button className="btn" onClick={() => close("COMPLETED")}>Patient joint</button>
                  <button className="btn secondary" onClick={() => close("UNREACHABLE")}>Injoignable</button>
                  <button className="btn secondary" onClick={() => run(async () => {
                    await api(`/agent/callbacks/${selected.id}/release`, { method: "POST" });
                    setSelected(null);
                    setConversation(null);
                  })}>Relâcher</button>
                </div>
                <p className="muted">Votre lecture de cette conversation est inscrite dans le journal d'audit.</p>
              </>
            ) : (
              <p className="muted">Sélectionnez un rappel que vous avez pris pour afficher la conversation.</p>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
