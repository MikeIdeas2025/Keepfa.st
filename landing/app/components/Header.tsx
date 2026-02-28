"use client";

import { useEffect, useState } from "react";

export default function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-bgprimary/80 backdrop-blur-xl border-b border-subtle"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-5xl mx-auto flex items-center justify-between px-4 sm:px-6 h-16">
        <a href="#" className="flex items-center gap-2">
          <span className="text-xl font-extrabold tracking-tight text-primary">
            Keepfa<span className="text-accent">.</span>st
          </span>
        </a>

        <a
          href="#prenota"
          className="text-sm font-semibold text-accent hover:text-accent-hover transition-colors"
        >
          Prenota una call &rarr;
        </a>
      </div>
    </header>
  );
}
