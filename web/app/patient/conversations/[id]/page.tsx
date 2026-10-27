"use client";

import { useParams } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";

import { ErrorBox } from "@/components/ErrorBox";
import { Back, Lock, Phone, Send, Warning } from "@/components/Icons";
import { LogoMark } from "@/components/Logo";
import { api, ApiError } from "@/lib/api";
import { DISCLAIMER, ORIENTATION_ADVICE, ORIENTATION_LABELS, STATUS_LABELS } from "@/lib/texts";
import { Conversation } from "@/lib/types";
import { useSession } from "@/lib/useSession";

export default function ConversationPage() {
  const user = useSession("PATIENT");
  const { id } = useParams<{ id: string }>();
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user) api<Conversation>(`/conversations/${id}`).then(setConversation).catch(() => setError("HTTP_ERROR"));
  }, [user, id]);
  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [conversation, busy]);

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

  if (!user || !conversation) return null;
  const level = conversation.orientationLevel;
  const open = conversation.status === "IN_PROGRESS";

  return (
    <main className="phone" style={{ height: "100vh" }}>
      <header className="phone-head">
        <a className="icon-btn" href="/patient" aria-label="Mes demandes"><Back /></a>
        <span className="logo-tile"><LogoMark size={22} /></span>
        <span style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <strong style={{ fontSize: 16 }}>Assistant Orienta</strong>
          <span style={{ fontSize: 12, color: "#BFD6FF" }}>{STATUS_LABELS[conversation.status]}</span>
        </span>
      </header>
      <div className="phone-body" style={{ overflowY: "auto" }}>
        <div className="chat">
          {conversation.messages.map((m) => <div key={m.id} className={`bubble ${m.sender}`}>{m.content}</div>)}
          {busy && <div className="bubble ASSISTANT muted">L'assistant réfléchit…</div>}
        </div>
        {level && (
          <div className={`orientation ${level}`}>
            <span className="row" style={{ gap: 10 }}>{level === "EMERGENCY" && <Warning />}<span className="level">{ORIENTATION_LABELS[level]}</span></span>
            <p style={{ fontSize: 15, lineHeight: 1.55 }}>{ORIENTATION_ADVICE[level]}</p>
            {level === "EMERGENCY" && (
              <p className="row" style={{ gap: 8, fontWeight: 700 }}><Phone size={18} /> Un agent de santé va vous rappeler.</p>
            )}
          </div>
        )}
        <ErrorBox code={error} />
        <div ref={end} />
      </div>
      {open ? (
        <div className="composer">
          <form onSubmit={send}>
            <label className="sr-only" htmlFor="answer">Votre réponse</label>
            <input id="answer" required maxLength={2000} value={content} onChange={(e) => setContent(e.target.value)} placeholder="Votre réponse…" />
            <button className="send" disabled={busy} aria-label="Envoyer"><Send /></button>
          </form>
          <p className="row muted" style={{ justifyContent: "center", gap: 6, fontSize: 12 }}><Lock size={13} /> Chiffré avant enregistrement · ne remplace pas un soignant</p>
        </div>
      ) : (
        <p className="disclaimer" style={{ padding: "12px 24px 24px" }}>{DISCLAIMER}</p>
      )}
    </main>
  );
}
