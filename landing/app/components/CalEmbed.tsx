"use client";

import dynamic from "next/dynamic";
import SectionWrapper from "./SectionWrapper";
import FadeIn from "./FadeIn";

// Lazy-load Cal.com embed to avoid SSR issues and reduce initial bundle
const Cal = dynamic(() => import("@calcom/embed-react").then((m) => m.default), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[500px] rounded-2xl bg-card border border-subtle flex items-center justify-center">
      <p className="text-secondary text-sm">Caricamento calendario...</p>
    </div>
  ),
});

// TODO: Replace with your actual Cal.com link when ready
const CAL_LINK = "miclau93/keepfast-design-partner";

export default function CalEmbed() {
  return (
    <SectionWrapper id="prenota">
      <FadeIn>
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-primary mb-4 tracking-tight">
            Diventa Design Partner
          </h2>
          <p className="text-lg text-secondary max-w-xl mx-auto">
            Cerchiamo 10-15 builder per la beta. Una call di 15 minuti per
            capire se Keepfa.st fa al caso tuo.
          </p>
        </div>
      </FadeIn>

      <FadeIn>
        <div className="max-w-3xl mx-auto rounded-2xl overflow-hidden border border-subtle">
          <Cal
            calLink={CAL_LINK}
            config={{ theme: "dark" }}
            style={{
              width: "100%",
              height: "500px",
              overflow: "scroll",
            }}
          />
        </div>
      </FadeIn>

      <FadeIn>
        <p className="text-center mt-6 text-sm text-secondary">
          Non riesci a prenotare?{" "}
          <a
            href="https://x.com/MicLau93"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent hover:text-accent-hover transition-colors underline underline-offset-4"
          >
            Scrivimi su X
          </a>
        </p>
      </FadeIn>
    </SectionWrapper>
  );
}
