import { Calendar, Home, Lock, Warning } from "@/components/Icons";
import { Logo, LogoMark } from "@/components/Logo";

// Placeholders to fill in before going live.
const NGO_NAME = "[NOM DE L'ONG]";
const EMERGENCY_NUMBER = "[NUMÉRO]";

const Check = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1769E0" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0, marginTop: 2 }}>
    <path d="M5 12l5 5L20 7" />
  </svg>
);

const POINTS = [
  "Disponible à tout moment, depuis un simple téléphone.",
  "En français, avec des questions courtes et claires.",
  "Relié à l'équipe de santé de l'ONG, qui rappelle en cas d'urgence.",
  "Vos données sont chiffrées et ne sont lues que par qui vous soigne.",
];
const STEPS = [
  ["Créez votre compte", "Avec votre adresse e-mail et un mot de passe. Un code vous est envoyé pour vérifier l'adresse."],
  ["Décrivez ce que vous ressentez", "Avec vos propres mots. L'assistant vous pose quelques questions sur la durée, l'intensité et les signes d'alerte."],
  ["Recevez votre orientation", "Urgence, consultation sous 48 heures ou conseils à domicile. En cas d'urgence, un agent de santé vous rappelle."],
];
const LEVELS = [
  { icon: <Warning size={24} />, color: "#B45309", bg: "#FFF1E0", title: "Urgence", text: "Des signes d'alerte : rendez-vous aux urgences ou appelez les secours. Un agent de santé de l'ONG vous rappelle." },
  { icon: <Calendar size={24} />, color: "#1769E0", bg: "#E8F1FD", title: "Consultation sous 48 heures", text: "Votre état demande l'avis d'un soignant : consultez le centre de santé le plus proche dans les deux jours." },
  { icon: <Home size={24} />, color: "#0F766E", bg: "#E3F4F1", title: "Conseils à domicile", text: "Des soins simples suffisent pour l'instant. Si les symptômes durent ou s'aggravent, consultez." },
];
const PRIVACY = [
  ["Chiffrées avant d'être enregistrées", "Vos messages, votre nom et votre numéro sont illisibles dans la base de données, même pour qui y aurait accès."],
  ["Lues seulement par qui vous rappelle", "Seul l'agent de santé qui prend votre rappel peut lire votre conversation. Les administrateurs n'y ont pas accès."],
  ["Chaque lecture est tracée", "Qui a ouvert votre dossier, et quand : tout est inscrit dans un journal."],
];
const FAQ = [
  ["Est-ce qu'Orienta pose un diagnostic ?", "Non. Orienta vous indique seulement vers quel niveau de soins vous tourner. Seul un professionnel de santé peut poser un diagnostic."],
  ["Qui peut lire ce que j'écris ?", "L'assistant pour vous répondre, puis, en cas d'urgence, l'agent de santé qui vous rappelle. Les administrateurs ne voient pas le contenu de vos conversations."],
  ["Pourquoi donner mon numéro de téléphone ?", "Pour qu'un agent de santé puisse vous rappeler si l'assistant vous oriente en urgence. Il est facultatif."],
  ["Que faire en cas d'urgence vitale ?", `N'attendez pas l'assistant : appelez directement les secours au ${EMERGENCY_NUMBER} ou rendez-vous aux urgences les plus proches.`],
];

function SectionHead({ eyebrow, title, lead, dark }: { eyebrow: string; title: string; lead?: string; dark?: boolean }) {
  return (
    <div className="lp-head">
      <span className="lp-eyebrow" style={dark ? { color: "#7FB2FF" } : undefined}>{eyebrow}</span>
      <h2 style={dark ? { color: "#fff" } : undefined}>{title}</h2>
      {lead && <p style={dark ? { color: "#C9D8EE" } : undefined}>{lead}</p>}
    </div>
  );
}

export default function LandingPage() {
  return (
    <main className="lp">
      <section className="lp-dark">
        <div className="lp-wrap">
          <header className="lp-nav">
            <Logo />
            <nav aria-label="Navigation principale">
              <a className="link" href="#orienta">Orienta</a>
              <a className="link" href="#fonctionnement">Comment ça marche</a>
              <a className="link" href="#confidentialite">Confidentialité</a>
              <a className="link" href="#questions">Questions</a>
              <a className="ghost" href="/login">Connexion</a>
              <a className="solid" href="/register">Créer mon compte</a>
            </nav>
          </header>
          <div className="lp-hero">
            <div>
              <span className="lp-pill">Assistant de pré-orientation santé</span>
              <h1>Le bon niveau de soins, au bon moment.</h1>
              <p className="lead">Décrivez vos symptômes à l'assistant de votre ONG de santé. En quelques questions, il vous dit s'il faut consulter en urgence, dans les 48 heures, ou si des soins à domicile suffisent.</p>
              <div className="row">
                <a className="lp-btn blue" href="/register">Créer mon compte patient</a>
                <a className="lp-btn white" href="#fonctionnement">Voir comment ça marche</a>
              </div>
              <p style={{ fontSize: 13, color: "#9DB4D6" }}>Orienta ne pose aucun diagnostic et ne remplace pas un professionnel de santé.</p>
            </div>
            <div>
              <img src="/login-illustration.svg" alt="Un patient échange avec l'assistant sur son téléphone, ses données sont protégées et un agent de santé le rappelle" />
            </div>
          </div>
        </div>
      </section>

      <section id="orienta" className="lp-wrap">
        <div className="lp-section lp-split">
          <img className="lp-photo" src="/orienta-patiente.jpg" alt="Une patiente écrit à l'assistant Orienta sur son téléphone, chez elle" />
          <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
            <SectionHead eyebrow="Qu'est-ce qu'Orienta ?" title="Un premier avis, avant de vous déplacer."
              lead="Orienta est l'assistant de pré-orientation de votre ONG de santé. Il ne remplace pas un soignant : il vous aide à savoir où aller, et quand, à partir de ce que vous ressentez." />
            <ul className="lp-checks">
              {POINTS.map((p) => <li key={p}><Check />{p}</li>)}
            </ul>
          </div>
        </div>
      </section>

      <section id="fonctionnement" className="lp-band">
        <div className="lp-wrap lp-section">
          <SectionHead eyebrow="Comment ça marche" title="Trois étapes, depuis votre téléphone." />
          <div className="lp-grid">
            {STEPS.map(([title, text], i) => (
              <div key={title} className="lp-card" style={{ background: "#F5F7FB" }}>
                <span className="lp-num">{i + 1}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-wrap lp-section">
        <SectionHead eyebrow="Les orientations" title="Trois réponses possibles, toujours claires." />
        <div className="lp-grid">
          {LEVELS.map((l) => (
            <div key={l.title} className="lp-card">
              <span className="level-icon" style={{ width: 48, height: 48, borderRadius: 14, background: l.bg, color: l.color }}>{l.icon}</span>
              <h3>{l.title}</h3>
              <p>{l.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="confidentialite" className="lp-dark">
        <div className="lp-wrap lp-privacy">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <span style={{ width: 56, height: 56, borderRadius: 16, background: "#14304F", display: "flex", alignItems: "center", justifyContent: "center" }}><Lock size={28} /></span>
            <SectionHead dark eyebrow="Confidentialité" title="Vos données de santé restent les vôtres."
              lead="Un symptôme, une grossesse, un traitement : ce sont des informations sensibles. Orienta est conçu pour les protéger." />
          </div>
          <div>
            {PRIVACY.map(([title, text], i) => (
              <div key={title} className="item">
                <b>0{i + 1}</b>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <strong style={{ fontSize: 17 }}>{title}</strong>
                  <span style={{ fontSize: 15, lineHeight: 1.55, color: "#C9D8EE" }}>{text}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-wrap lp-section">
        <SectionHead eyebrow="Pour qui ?" title="Un compte pour chaque rôle." />
        <div className="lp-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
          <div className="lp-card" style={{ border: "2px solid #1769E0" }}>
            <span className="lp-eyebrow">Patients</span>
            <h3 style={{ fontSize: 24 }}>Vous cherchez à savoir où vous soigner</h3>
            <p>Créez votre compte vous-même, gratuitement, avec votre adresse e-mail. Vous retrouvez ensuite toutes vos demandes et leur suivi.</p>
            <a className="lp-btn blue" href="/register" style={{ alignSelf: "flex-start", marginTop: 6 }}>Créer mon compte patient</a>
          </div>
          <div className="lp-card">
            <span className="lp-eyebrow" style={{ color: "#51607A" }}>Équipe de l'ONG</span>
            <h3 style={{ fontSize: 24 }}>Vous êtes agent de santé ou administrateur</h3>
            <p>Votre compte est créé par un administrateur de l'ONG. Vous recevez une invitation par e-mail avec un code pour l'activer.</p>
            <a className="lp-btn soft" href="/login" style={{ alignSelf: "flex-start", marginTop: 6 }}>Se connecter</a>
          </div>
        </div>
      </section>

      <section id="questions" className="lp-band">
        <div className="lp-wrap lp-section lp-faq">
          <SectionHead eyebrow="Questions fréquentes" title="Ce qu'on nous demande le plus." />
          <div>
            {FAQ.map(([q, a], i) => (
              <details key={q} open={i === 0}>
                <summary>{q}</summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-wrap" style={{ padding: "96px 24px 72px" }}>
        <div className="lp-cta">
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 620 }}>
            <h2>Vous ne vous sentez pas bien ?</h2>
            <p style={{ fontSize: 17, color: "#E1EDFF" }}>Créez votre compte en une minute et décrivez vos symptômes.</p>
          </div>
          <a className="lp-btn white" href="/register">Créer mon compte patient</a>
        </div>
      </section>

      <footer className="lp-foot">
        <div className="lp-wrap">
          <span className="row" style={{ gap: 10 }}>
            <span className="logo-tile" style={{ width: 28, height: 28, borderRadius: 8 }}><LogoMark size={20} /></span>
            <strong style={{ color: "#0B1F3A" }}>Orienta</strong> · Une initiative de {NGO_NAME}
          </span>
          <span>En cas d'urgence vitale, appelez directement les secours : {EMERGENCY_NUMBER}.</span>
        </div>
      </footer>
    </main>
  );
}
