import FadeIn from "./FadeIn";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center px-4 sm:px-6 pt-16 overflow-hidden">
      {/* Coral glow */}
      <div
        className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(231,132,104,0.08) 0%, transparent 70%)",
        }}
      />

      <div className="relative max-w-3xl mx-auto text-center">
        <FadeIn>
          {/* Badge */}
          <div className="inline-flex items-center gap-2 mb-8 px-4 py-1.5 rounded-full border border-accent/30 bg-accent/5">
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <span className="text-sm font-medium text-accent">
              Beta aperta — Posti limitati
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6 text-balance">
            Tu buildi. L&apos;AI legge.
            <br />
            <span className="text-accent">Tu decidi. L&apos;AI misura.</span>
          </h1>

          {/* Sub-headline */}
          <p className="text-lg sm:text-xl text-secondary max-w-2xl mx-auto mb-10 leading-relaxed">
            Connetti PostHog e Stripe, chiedi in linguaggio semplice, ricevi
            risposte che ti dicono cosa fixare oggi.{" "}
            <span className="text-primary font-medium">
              Direttamente dentro Cursor.
            </span>
          </p>

          {/* CTA */}
          <a
            href="#prenota"
            className="inline-block bg-accent hover:bg-accent-hover text-white font-semibold px-8 py-4 rounded-full text-lg transition-colors"
          >
            Diventa Design Partner
          </a>

          {/* Sub-CTA */}
          <p className="mt-4 text-sm text-secondary">
            Gratis durante la beta. Nessuna carta richiesta.
          </p>
        </FadeIn>
      </div>
    </section>
  );
}
