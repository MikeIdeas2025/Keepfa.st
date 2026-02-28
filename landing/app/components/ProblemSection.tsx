import SectionWrapper from "./SectionWrapper";
import FadeIn from "./FadeIn";

const pains = [
  {
    emoji: "🔍",
    title: "PostHog installato, zero insight",
    description:
      "Hai configurato il tracking, hai 2 eventi, ti sei perso nei dashboard e l'hai abbandonato dopo una settimana.",
  },
  {
    emoji: "📊",
    title: "Stripe e speranza",
    description:
      "Il tuo processo di analytics: apri Stripe, guardi il numero, speri che salga. Fine.",
  },
  {
    emoji: "👋",
    title: "Churn misterioso",
    description:
      "Un cliente se ne va e non hai idea del perché. Non sai se è colpa tua, del prodotto, o se semplicemente non ne aveva bisogno.",
  },
];

export default function ProblemSection() {
  return (
    <SectionWrapper>
      <FadeIn>
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4 tracking-tight">
          Sai buildare.{" "}
          <span className="text-accent">Ma sai leggere i dati?</span>
        </h2>
        <p className="text-secondary text-center max-w-xl mx-auto mb-14 text-lg">
          Hai il prodotto live. Hai gli utenti. Ma quando devi capire cosa
          non funziona, sei nel buio.
        </p>
      </FadeIn>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {pains.map((pain, i) => (
          <FadeIn key={i}>
            <div className="bg-card border border-subtle rounded-2xl p-6 h-full">
              <span className="text-3xl mb-4 block">{pain.emoji}</span>
              <h3 className="text-lg font-semibold text-primary mb-2">
                {pain.title}
              </h3>
              <p className="text-secondary text-sm leading-relaxed">
                {pain.description}
              </p>
            </div>
          </FadeIn>
        ))}
      </div>

      <FadeIn>
        <p className="text-center mt-14 text-lg sm:text-xl font-medium text-primary max-w-2xl mx-auto">
          Non ti serve una dashboard.
          <br />
          <span className="text-accent">
            Ti serve qualcuno che ti dica cosa sta succedendo.
          </span>
        </p>
      </FadeIn>
    </SectionWrapper>
  );
}
