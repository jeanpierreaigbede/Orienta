"use client";

import { logout } from "@/lib/api";

import { Logout, UserIcon } from "./Icons";
import { Logo } from "./Logo";

export function PatientHeader() {
  return (
    <header className="phone-head">
      <span style={{ flex: 1 }}><Logo href="/patient" /></span>
      <a className="icon-btn" href="/profil" aria-label="Mon profil"><UserIcon size={20} /></a>
      <button className="icon-btn" onClick={logout} aria-label="Se déconnecter"><Logout size={20} /></button>
    </header>
  );
}
