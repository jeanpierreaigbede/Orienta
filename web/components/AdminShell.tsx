"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { api, initials, logout } from "@/lib/api";
import { useSession } from "@/lib/useSession";

import { Compass, FileText, Grid, Logout, Shield, UserIcon, Users } from "./Icons";
import { Logo } from "./Logo";

const NAV = [
  { href: "/oriadmin", label: "Vue d'ensemble", icon: <Grid /> },
  { href: "/oriadmin/users", label: "Utilisateurs", icon: <Users /> },
  { href: "/oriadmin/agents", label: "Agents de santé", icon: <Shield /> },
  { href: "/oriadmin/orientations", label: "Orientations", icon: <Compass />, urgent: true },
  { href: "/oriadmin/audit", label: "Journal d'audit", icon: <FileText /> },
];

/** Layout of every /oriadmin page: sidebar with navigation, profile and logout. */
export function AdminShell({ children }: { children: React.ReactNode }) {
  const user = useSession("ADMIN");
  const path = usePathname();
  const [urgent, setUrgent] = useState(0);

  useEffect(() => {
    if (user) api<{ urgentWaiting: number }>("/admin/overview").then((o) => setUrgent(o.urgentWaiting)).catch(() => undefined);
  }, [user, path]);

  if (!user) return null;

  return (
    <div className="admin">
      <aside className="sidebar">
        <div style={{ padding: "0 6px" }}>
          <Logo href="/oriadmin" subtitle="Administration" />
        </div>
        <nav aria-label="Administration">
          {NAV.map((item) => (
            <a key={item.href} href={item.href} aria-current={path === item.href ? "page" : undefined}>
              {item.icon}
              {item.label}
              {item.urgent && urgent > 0 && <span className="count">{urgent}</span>}
            </a>
          ))}
        </nav>
        <div className="me">
          <div className="row" style={{ padding: "0 6px", gap: 10, flexWrap: "nowrap" }}>
            <span className="avatar" style={{ width: 38, height: 38 }}>{initials(user.fullName)}</span>
            <div style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
              <span style={{ fontSize: 14, fontWeight: 700 }}>{user.fullName}</span>
              <span style={{ fontSize: 12, color: "#9DB4D6", overflow: "hidden", textOverflow: "ellipsis" }}>{user.email}</span>
            </div>
          </div>
          <a className="profile" href="/profil"><UserIcon /> Mon profil</a>
          <button className="logout" onClick={logout}><Logout /> Se déconnecter</button>
        </div>
      </aside>
      <main>{children}</main>
    </div>
  );
}
