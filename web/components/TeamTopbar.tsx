"use client";

import { initials, logout, User } from "@/lib/api";

import { Logout } from "./Icons";
import { Logo } from "./Logo";

/** Header of the health agent space: logo, space name, profile and logout. */
export function TeamTopbar({ user, space }: { user: User | null; space: string }) {
  return (
    <header className="topbar">
      <div className="row" style={{ gap: 12 }}>
        <Logo href="/oriagent" />
        <span className="space">{space}</span>
      </div>
      {user && (
        <div className="topbar-user">
          <a className="me" href="/profil">
            <span className="avatar">{initials(user.fullName)}</span>
            {user.fullName}
          </a>
          <button className="logout" onClick={logout}>
            <Logout size={16} /> Se déconnecter
          </button>
        </div>
      )}
    </header>
  );
}
