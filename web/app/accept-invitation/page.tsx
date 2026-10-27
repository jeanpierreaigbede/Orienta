import { Suspense } from "react";

import { CodeForm } from "@/components/CodeForm";
import { Logo } from "@/components/Logo";

export default function AcceptInvitationPage() {
  return (
    <main className="split">
      <section className="split-art">
        <Logo />
        <img src="/login-illustration.svg" alt="" />
        <p>Bienvenue dans l'équipe Orienta.</p>
      </section>
      <section className="split-form">
        <div className="panel">
          <div>
            <h1>Activer votre compte</h1>
            <p className="muted" style={{ fontSize: 15, marginTop: 6 }}>Saisissez le code reçu par e-mail et choisissez votre mot de passe.</p>
          </div>
          <Suspense>
            <CodeForm mode="invitation" />
          </Suspense>
        </div>
      </section>
    </main>
  );
}
