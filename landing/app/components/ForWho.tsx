import SectionWrapper from "./SectionWrapper";
import FadeIn from "./FadeIn";

const personas = [
  {
    emoji: "⚡",
    title: "Vibecoder",
    description:
      "Hai buildato il tuo SaaS con Cursor, Bolt o Lovable. È live, ha utenti. Ma non hai idea di cosa sia una cohort e perché il churn ti sta uccidendo. Per te \"analytics\" significa guardare il numero di utenti su Stripe.",
  },
  {
    emoji: "🛠️",
    title: "Founder dev-first",
    description:
      "Sai scrivere codice, shippi veloce, hai utenti paganti. Quando apri Mixpanel non sai cosa guardare. Confondi vanity metrics con segnali reali. Vuoi risposte, non dashboard.",
  },
];

export default function ForWho() {
  return (
    <SectionWrapper>
      <FadeIn>
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14 tracking-tight">
          Per chi è Keepfa.st
        </h2>
      </FadeIn>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-14">
        {personas.map((persona, i) => (
          <FadeIn key={i}>
            <div className="bg-card border border-subtle rounded-2xl p-6 sm:p-8 h-full">
              <span className="text-3xl mb-4 block">{persona.emoji}</span>
              <h3 className="text-xl font-bold text-primary mb-3">
                {persona.title}
              </h3>
              <p className="text-secondary leading-relaxed">
                {persona.description}
              </p>
            </div>
          </FadeIn>
        ))}
      </div>

      <FadeIn>
        <p className="text-center text-lg sm:text-xl font-medium text-primary max-w-2xl mx-auto">
          Se sai buildare ma non sai leggere,
          <br />
          <span className="text-accent">
            Keepfa.st è il PM che non hai mai assunto.
          </span>
        </p>
      </FadeIn>
    </SectionWrapper>
  );
}
