"use client";

import { useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { Chat } from "@/components/Chat";
import { ErrorBox } from "@/components/ErrorBox";
import { TopBar } from "@/components/TopBar";
import { api, ApiError } from "@/lib/api";
import { DISCLAIMER, ORIENTATION_ADVICE, ORIENTATION_LABELS } from "@/lib/texts";
import { Conversation } from "@/lib/types";
import { useSession } from "@/lib/useSession";

export default function ConversationPage() {
  const user = useSession("PATIENT");
  const { id } = useParams<{ id: string }>();
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) api<Conversation>(`/conversations/${id}`).then(setConversation).catch(() => setError("HTTP_ERROR"));
  }, [user, id]);

  async function send(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setConversation(await api<Conversation>(`/conversations/${id}/messages`, { method: "POST", body: { content } }));
      setContent("");
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "HTTP_ERROR");
    } finally {
      setBusy(false);
    }
  }

  if (!user || !conversation) return <TopBar user={user} />;
  const level = conversation.orientationLevel;

  return (
    <main>
      <TopBar user={user} />
      <div className="container stack">
        <a href="/patient">← Mes demandes</a>
        <div className="card stack">
          <Chat messages={conversation.messages} />
          {level && (
            <div className={`alert ${level === "EMERGENCY" ? "error" : "info"}`}>
              <strong>{ORIENTATION_LABELS[level]}.</strong> {ORIENTATION_ADVICE[level]}
            </div>
          )}
          <ErrorBox code={error} />
          {conversation.status === "IN_PROGRESS" && (
            <form className="row" onSubmit={send}>
              <input style={{ flex: 1 }} required maxLength={2000} value={content} onChange={(e) => setContent(e.target.value)} placeholder="Votre réponse…" />
              <button className="btn" disabled={busy}>{busy ? "…" : "Envoyer"}</button>
            </form>
          )}
          <p className="muted">{DISCLAIMER}</p>
        </div>
      </div>
    </main>
  );
}
