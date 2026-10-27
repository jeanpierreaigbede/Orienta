import { TopBar } from "@/components/TopBar";
import { HealthBadge } from "@/lib/HealthBadge";

export default function HomePage() {
  return (
    <main>
      <TopBar />
      <section className="hero">
        <div className="container">
          <h1>Décrivez vos symptômes, on vous oriente.</h1>
          <p>
            Orienta est l'assistant de pré-orientation de votre ONG de santé. Il vous indique s'il faut consulter en
            urgence, dans les 48 heures, ou si des soins à domicile suffisent.
          </p>
          <div className="row" style={{ marginTop: 24 }}>
            <a className="btn" href="/register">Créer un compte</a>
            <a className="btn secondary" href="/login">Se connecter</a>
          </div>
        </div>
      </section>
      <section className="container stack">
        <div className="alert warning">Orienta ne remplace pas un professionnel de santé et ne pose aucun diagnostic.</div>
        <HealthBadge />
      </section>
    </main>
  );
}
