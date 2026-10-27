import { Suspense } from "react";

import { CodeForm } from "@/components/CodeForm";
import { TopBar } from "@/components/TopBar";

export default function VerifyPage() {
  return (
    <main>
      <TopBar />
      <div className="container narrow">
        <h1>Vérifiez votre adresse</h1>
        <p className="lead">Saisissez le code à 6 chiffres reçu par e-mail. Il est valable 10 minutes.</p>
        <Suspense>
          <CodeForm mode="verify" />
        </Suspense>
      </div>
    </main>
  );
}
