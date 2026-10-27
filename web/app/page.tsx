import { Calendar, Home, Lock, Warning } from "@/components/Icons";
import { Logo } from "@/components/Logo";
import { DISCLAIMER } from "@/lib/texts";

const LEVELS = [
  { title: "Urgence", text: "Aller aux urgences, un agent vous rappelle", icon: <Warning />, color: "#B45309", bg: "#FFF1E0" },
  { title: "Consultation sous 48 h", text: "Dans le centre de santé le plus proche", icon: <Calendar />, color: "#1769E0", bg: "#E8F1FD" },
  { title: "Conseils à domicile", text: "Et consulter si cela ne passe pas", icon: <Home />, color: "#0F766E", bg: "#E3F4F1" },
];

export default function HomePage() {
  return (
    <main className="phone">
      <section className="hero">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <Logo />
          <a href="/login" style={{ color: "#BFD6FF", fontWeight: 600, fontSize: 14, textDecoration: "none", padding: "12px 4px" }}>Connexion</a>
        </div>
        <div>
          <h1>Décrivez vos symptômes, on vous oriente.</h1>
          <p>L'assistant de votre ONG de santé vous dit, en quelques questions, quel niveau de soins choisir.</p>
        </div>
      </section>
      <section className="phone-body" style={{ gap: 12 }}>
        <p className="muted" style={{ fontSize: 13, fontWeight: 700, letterSpacing: 0.8, textTransform: "uppercase" }}>Trois orientations possibles</p>
        {LEVELS.map((l) => (
          <div key={l.title} className="level-card">
            <span className="level-icon" style={{ background: l.bg, color: l.color }}>{l.icon}</span>
            <span style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <strong style={{ fontSize: 15 }}>{l.title}</strong>
              <span className="muted" style={{ fontSize: 13 }}>{l.text}</span>
            </span>
          </div>
        ))}
        <p className="row" style={{ gap: 8, fontSize: 13, fontWeight: 600, color: "#0B1F3A" }}>
          <Lock /> Vos messages sont chiffrés avant d'être enregistrés.
        </p>
      </section>
      <section className="phone-foot">
        <a className="btn block" href="/register">Créer mon compte</a>
        <a className="btn soft block" href="/login">J'ai déjà un compte</a>
        <p className="disclaimer">{DISCLAIMER}</p>
      </section>
    </main>
  );
}
