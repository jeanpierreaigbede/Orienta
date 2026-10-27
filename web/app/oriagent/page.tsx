"use client";

import { useCallback, useEffect, useState } from "react";

import { LevelBadge, StatusBadge } from "@/components/Badge";
import { ErrorBox } from "@/components/ErrorBox";
import { Segmented } from "@/components/Segmented";
import { TeamTopbar } from "@/components/TeamTopbar";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/texts";
import { Callback, Conversation } from "@/lib/types";
import { useSession } from "@/lib/useSession";

type View = "OPEN" | "CLOSED";

export default function AgentSpace() {
  const user = useSession("HEALTH_AGENT");
  const [view, setView] = useState<View>("OPEN");
  const [callbacks, setCallbacks] = useState<Callback[]>([]);
  const [selected, setSelected] = useState<Callback | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (view === "OPEN") setCallbacks(await api<Callback[]>("/agent/callbacks"));
    else {
      const [done, unreachable] = await Promise.all([
        api<Callback[]>("/agent/callbacks?status=COMPLETED"),
        api<Callback[]>("/agent/callbacks?status=UNREACHABLE"),
      ]);
      setCallbacks([...done, ...unreachable].sort((a, b) => (b.closedAt ?? "").localeCompare(a.closedAt ?? "")));
    }
  }, [view]);
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
    setNote("");
    setConversation(await api<Conversation>(`/agent/callbacks/${callback.id}/conversation`));
  }

  function clear() {
    setSelected(null);
    setConversation(null);
    setNote("");
  }

  const close = (outcome: "COMPLETED" | "UNREACHABLE") =>
    selected && run(async () => {
      await api(`/agent/callbacks/${selected.id}/close`, { method: "POST", body: { outcome, note: note || null } });
      clear();
    });

  const openCount = view === "OPEN" ? callbacks.length : undefined;

  return (
    <>
      <TeamTopbar user={user} space="Espace agent de santé" />
      {user && (
        <div className="content">
          <div className="page-head">
            <div>
              <h1>Patients à rappeler</h1>
              <p>Patients orientés en urgence par l'assistant. Prenez un rappel pour lire la conversation.</p>
            </div>
            <Segmented label="Afficher" value={view} onChange={(v) => { setView(v); clear(); }}
              options={[{ value: "OPEN", label: openCount !== undefined ? `À traiter · ${openCount}` : "À traiter" }, { value: "CLOSED", label: "Clôturés" }]} />
          </div>
          <ErrorBox code={error} />
          <div className="two-cols">
            <section className="card narrow" style={{ padding: 0, overflow: "hidden" }}>
              {callbacks.length === 0 && <p className="muted" style={{ padding: 20 }}>{view === "OPEN" ? "Aucun patient à rappeler." : "Aucun rappel clôturé."}</p>}
              {callbacks.map((c) => (
                <div key={c.id} className={`list-row ${selected?.id === c.id ? "selected" : ""}`}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <strong style={{ fontSize: 15 }}>{c.patientName}</strong>
                    <span className="muted" style={{ fontSize: 13 }}>{c.patientPhone ?? "Pas de téléphone"} · reçu {formatDate(c.createdAt)}</span>
                  </div>
                  {c.status === "PENDING" && <button className="btn small" onClick={() => run(() => api(`/agent/callbacks/${c.id}/assign`, { method: "POST" }))}>Prendre</button>}
                  {c.status === "ASSIGNED" && c.assignedToMe && (
                    selected?.id === c.id ? <StatusBadge status="ASSIGNED" label="Pris par vous" /> : <button className="btn small soft" onClick={() => open(c)}>Ouvrir</button>
                  )}
                  {(c.status === "COMPLETED" || c.status === "UNREACHABLE") && <StatusBadge status={c.status} />}
                </div>
              ))}
            </section>
            <section className="card wide stack" style={{ padding: 24 }}>
              {selected && conversation ? (
                <>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <div>
                      <h2 style={{ fontSize: 22 }}>{selected.patientName}</h2>
                      <p className="muted">{selected.patientPhone ?? "Pas de téléphone"}</p>
                    </div>
                    <LevelBadge level={selected.orientationLevel} />
                  </div>
                  <div className="chat" style={{ background: "#F5F7FB", borderRadius: 12, padding: 16 }}>
                    {conversation.messages.map((m) => <div key={m.id} className={`bubble ${m.sender}`} style={{ fontSize: 14 }}>{m.content}</div>)}
                  </div>
                  <label className="field">Note de suivi
                    <textarea className="input" rows={3} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />
                  </label>
                  <div className="row">
                    <button className="btn" onClick={() => close("COMPLETED")}>Patient joint</button>
                    <button className="btn soft" onClick={() => close("UNREACHABLE")}>Injoignable</button>
                    <button className="btn outline" onClick={() => run(async () => { await api(`/agent/callbacks/${selected.id}/release`, { method: "POST" }); clear(); })}>Relâcher</button>
                  </div>
                  <p className="muted" style={{ fontSize: 13 }}>Votre lecture de cette conversation est inscrite dans le journal d'audit.</p>
                </>
              ) : (
                <p className="muted">Prenez un rappel, puis ouvrez-le pour lire la conversation du patient.</p>
              )}
            </section>
          </div>
        </div>
      )}
    </>
  );
}
