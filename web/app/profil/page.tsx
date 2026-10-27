"use client";

import { useEffect, useState } from "react";

import { Back, Logout } from "@/components/Icons";
import { api, HOME_BY_ROLE, initials, logout, User } from "@/lib/api";
import { formatDate, ROLE_LABELS } from "@/lib/texts";

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api<User>("/auth/me").then(setUser).catch(() => (window.location.href = "/login"));
  }, []);

  if (!user) return null;
  const rows = [
    ["Nom", user.fullName],
    ["Adresse e-mail", user.email],
    ["Téléphone", user.phone ?? "Non renseigné"],
    ["Rôle", ROLE_LABELS[user.role]],
    ["Compte créé le", formatDate(user.createdAt)],
  ];

  return (
    <main className="content" style={{ maxWidth: 560 }}>
      <a href={HOME_BY_ROLE[user.role]} className="row" style={{ gap: 4, fontWeight: 700, textDecoration: "none" }}><Back size={18} /> Retour</a>
      <div className="row" style={{ gap: 16 }}>
        <span className="avatar" style={{ width: 64, height: 64, fontSize: 22 }}>{initials(user.fullName)}</span>
        <div>
          <h1 style={{ fontSize: 26 }}>{user.fullName}</h1>
          <p className="muted">{ROLE_LABELS[user.role]}</p>
        </div>
      </div>
      <section className="card" style={{ padding: 0 }}>
        {rows.map(([label, value]) => (
          <div key={label} className="list-row">
            <span className="muted">{label}</span>
            <strong style={{ fontSize: 15 }}>{value}</strong>
          </div>
        ))}
      </section>
      <button className="btn outline" onClick={logout} style={{ alignSelf: "flex-start" }}><Logout /> Se déconnecter</button>
    </main>
  );
}
