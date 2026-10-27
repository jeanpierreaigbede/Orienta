import { HealthBadge } from "@/lib/HealthBadge";

export default function HomePage() {
  return (
    <main>
      <header className="topbar">
        <a className="brand" href="/">
          Orient<span>a</span>
        </a>
      </header>
      <section className="hero">
        <div className="container">
          <h1>Orienta</h1>
          <p>
            Un assistant de pré-orientation pour les ONG de santé : il recueille les symptômes et oriente vers le bon
            niveau de soins, sans exposer les données des patients.
          </p>
        </div>
      </section>
      <section className="container">
        <div className="card stack">
          <h2>Socle technique</h2>
          <p className="muted">
            Cette branche contient uniquement le socle : Docker, configuration, API et application web. Les
            fonctionnalités se trouvent dans les branches <code>chatbot-without-encryption</code> et{" "}
            <code>chatbot-with-encryption</code>.
          </p>
          <HealthBadge />
        </div>
      </section>
    </main>
  );
}
