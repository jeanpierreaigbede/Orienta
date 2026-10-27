"use client";

import { useRouter } from "next/navigation";

import { api, User } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/texts";

export function TopBar({ user }: { user?: User | null }) {
  const router = useRouter();

  async function logout() {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace("/login");
  }

  return (
    <header className="topbar">
      <a className="brand" href="/">
        Orient<span>a</span>
      </a>
      <nav>
        {user ? (
          <>
            <span>
              {user.fullName} · {ROLE_LABELS[user.role]}
            </span>
            <button className="link" onClick={logout}>
              Se déconnecter
            </button>
          </>
        ) : (
          <>
            <a href="/login">Connexion</a>
            <a href="/register">Créer un compte</a>
          </>
        )}
      </nav>
    </header>
  );
}
