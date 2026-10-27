"use client";

import { useState } from "react";

import { Eye, EyeOff } from "./Icons";

/** Password field with an eye button to show or hide the value. */
export function PasswordInput(props: { value: string; onChange: (v: string) => void; autoComplete: string; minLength?: number }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="password">
      <input
        type={visible ? "text" : "password"}
        required
        minLength={props.minLength}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        autoComplete={props.autoComplete}
      />
      <button type="button" aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"} aria-pressed={visible} onClick={() => setVisible(!visible)}>
        {visible ? <EyeOff /> : <Eye />}
      </button>
    </div>
  );
}
