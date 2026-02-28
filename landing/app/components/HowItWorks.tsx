import SectionWrapper from "./SectionWrapper";
import FadeIn from "./FadeIn";

const steps = [
  {
    number: "1",
    title: "Connetti",
    description:
      "Dai a Keepfa.st le API key di PostHog e Stripe. Due minuti, una volta sola.",
    detail: "PostHog + Stripe → fatto",
  },
  {
    number: "2",
    title: "Chiedi",
    description:
      "Fai domande dentro Cursor o Claude. In italiano o inglese, come ti viene.",
    detail: '"Come stanno i miei clienti?"',
  },
  {
    number: "3",
    title: "Agisci",
    description:
      "Ricevi risposte in linguaggio semplice. Sai cosa fixare oggi, non tra un mese.",
    detail: "→ 3 clienti a rischio. Ecco perché.",
  },
];

export default function HowItWorks() {
  return (
    <SectionWrapper>
      <FadeIn>
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14 tracking-tight">
          Come funziona
        </h2>
      </FadeIn>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {steps.map((step, i) => (
          <FadeIn key={i}>
            <div className="relative bg-card border border-subtle rounded-2xl p-6 h-full">
              {/* Step number */}
              <div className="w-10 h-10 rounded-full bg-accent text-white flex items-center justify-center font-bold text-lg mb-5">
                {step.number}
              </div>

              <h3 className="text-xl font-bold text-primary mb-2">
                {step.title}
              </h3>
              <p className="text-secondary text-sm leading-relaxed mb-4">
                {step.description}
              </p>
              <p className="text-xs font-mono text-accent bg-accent/5 border border-accent/10 rounded-lg px-3 py-2 inline-block">
                {step.detail}
              </p>

              {/* Connector arrow (desktop only, not on last item) */}
              {i < steps.length - 1 && (
                <div className="hidden md:block absolute top-1/2 -right-3 text-subtle text-2xl">
                  →
                </div>
              )}
            </div>
          </FadeIn>
        ))}
      </div>
    </SectionWrapper>
  );
}
