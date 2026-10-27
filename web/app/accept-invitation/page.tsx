import { Suspense } from "react";

import { CodeForm } from "@/components/CodeForm";
import { TopBar } from "@/components/TopBar";

export default function AcceptInvitationPage() {
  return (
    <main>
      <TopBar />
      <div className="container narrow">
        <h1>Activer votre compte</h1>
        <p className="lead">Un administrateur vous a invité. Saisissez le code reçu par e-mail et choisissez votre mot de passe.</p>
        <Suspense>
          <CodeForm mode="invitation" />
        </Suspense>
      </div>
    </main>
  );
}
