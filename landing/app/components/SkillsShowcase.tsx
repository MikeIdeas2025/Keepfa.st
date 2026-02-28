import SectionWrapper from "./SectionWrapper";
import FadeIn from "./FadeIn";
import TerminalBlock from "./TerminalBlock";

const skills = [
  {
    label: "Health Check",
    title: "Chi sta per andarsene?",
    description:
      "Quali clienti stanno bene, quali stanno per andarsene, e perché.",
    prompt: '"Come stanno i miei clienti?"',
    output: `Ho controllato la salute dei tuoi 47 clienti:

  ✅ In salute: 31
  ⚠️  A rischio: 12
  🔴 Critici: 4

Stai rischiando di perdere €890/mese
dai clienti a rischio e critici.

I problemi principali:
  → Nessun login da 14+ giorni
  → Subscription cancellata
  → Attività in calo del 60%`,
  },
  {
    label: "Journey Map",
    title: "Dove si bloccano?",
    description:
      "Dove si bloccano le persone tra la registrazione e la fedeltà.",
    prompt: '"Dove si bloccano le persone dopo la registrazione?"',
    output: `Ecco dove si trovano i tuoi 47 clienti:

  Awareness:  ████░░░░░░  8  (17%)
  Activation: ██████░░░░  14 (30%)
  Adoption:   █████░░░░░  12 (26%)
  Retention:  ████░░░░░░  9  (19%)
  Advocacy:   ██░░░░░░░░  4  (9%)

⚠️ Punto critico: tra Activation e Adoption
   perdi il 35% delle persone.

→ Suggerimento: il tuo onboarding non porta
  le persone al momento "aha". Parti da lì.`,
  },
  {
    label: "Customer Value",
    title: "Quanto vale ogni cliente?",
    description:
      "Quanto vale ogni cliente e un piano per farli restare più a lungo.",
    prompt: '"Quanto vale ogni cliente?"',
    output: `Valore totale del portfolio: €24.500

  🏆 Champions:  5  (valore medio: €1.200)
  💎 Advocates:  12 (valore medio: €680)
  💰 Affluents:  18 (valore medio: €340)
  🪙 Misers:     12 (valore medio: €85)

Piano d'azione:
  1. Contatta i 4 clienti critici questa settimana
  2. Crea un onboarding email per i nuovi utenti
  3. Offri un upgrade ai 12 Advocates`,
  },
];

export default function SkillsShowcase() {
  return (
    <SectionWrapper>
      <FadeIn>
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4 tracking-tight">
          3 skill, <span className="text-accent">zero gergo</span>
        </h2>
        <p className="text-secondary text-center max-w-xl mx-auto mb-14 text-lg">
          Chiedi in linguaggio naturale. Ricevi risposte che capisci al volo.
        </p>
      </FadeIn>

      <div className="space-y-10">
        {skills.map((skill, i) => (
          <FadeIn key={i}>
            <div className="bg-card border border-subtle rounded-2xl p-6 sm:p-8">
              {/* Skill header */}
              <div className="mb-5">
                <span className="inline-block text-xs font-mono font-semibold text-accent bg-accent/10 border border-accent/20 rounded-full px-3 py-1 mb-3">
                  {skill.label}
                </span>
                <h3 className="text-xl sm:text-2xl font-bold text-primary">
                  {skill.title}
                </h3>
                <p className="text-secondary mt-1">{skill.description}</p>
              </div>

              {/* Terminal */}
              <TerminalBlock prompt={skill.prompt} output={skill.output} />
            </div>
          </FadeIn>
        ))}
      </div>
    </SectionWrapper>
  );
}
