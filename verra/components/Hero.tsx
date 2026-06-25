"use client";

import React, { useEffect, useRef } from "react";
import Link from "next/link";

export function Hero() {
  const textRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = textRef.current;
    if (!el) return;
    const items = el.querySelectorAll("[data-reveal]");
    items.forEach((item, i) => {
      setTimeout(() => {
        (item as HTMLElement).style.opacity = "1";
        (item as HTMLElement).style.transform = "translateY(0)";
      }, 400 + i * 200);
    });
  }, []);

  return (
    <section className="relative min-h-screen flex items-end pb-24 md:pb-32 overflow-hidden">
      {/* Background image with slow zoom */}
      <div className="absolute inset-0 animate-slow-zoom">
        <div
          className="w-full h-full bg-cover bg-center"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=1920&q=85')",
          }}
        />
      </div>

      {/* Gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-t from-verra-black via-verra-black/40 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-r from-verra-black/60 via-transparent to-transparent" />

      {/* Vertical gold line accent */}
      <div className="absolute left-12 top-1/4 bottom-1/4 w-px bg-gradient-to-b from-transparent via-verra-gold/50 to-transparent hidden xl:block" />

      {/* Content */}
      <div ref={textRef} className="relative z-10 px-6 md:px-16 xl:px-24 max-w-[900px]">

        {/* Season badge */}
        <div
          data-reveal
          className="mb-8 inline-flex items-center gap-3"
          style={{ opacity: 0, transform: "translateY(30px)", transition: "all 0.9s cubic-bezier(0.16,1,0.3,1)" }}
        >
          <span className="w-8 h-px bg-verra-gold" />
          <span className="text-[10px] tracking-widest3 uppercase text-verra-gold font-medium">
            Winter 2026
          </span>
        </div>

        {/* Main heading */}
        <h1
          data-reveal
          className="font-serif text-[clamp(72px,10vw,160px)] font-light leading-[0.9] text-verra-ivory mb-4"
          style={{ opacity: 0, transform: "translateY(40px)", transition: "all 1s cubic-bezier(0.16,1,0.3,1)" }}
        >
          VÉRRA
        </h1>

        <p
          data-reveal
          className="font-serif text-[clamp(20px,2.5vw,32px)] font-light italic text-verra-gold mb-8"
          style={{ opacity: 0, transform: "translateY(30px)", transition: "all 0.9s cubic-bezier(0.16,1,0.3,1)" }}
        >
          Designed Beyond Time
        </p>

        <p
          data-reveal
          className="text-base md:text-lg text-verra-ash/90 max-w-xl leading-relaxed mb-12"
          style={{ opacity: 0, transform: "translateY(30px)", transition: "all 0.9s cubic-bezier(0.16,1,0.3,1)" }}
        >
          Crafting timeless garments for those who define their own legacy.
          Each piece is made once, made right, and made to last a lifetime.
        </p>

        <div
          data-reveal
          className="flex flex-wrap items-center gap-4"
          style={{ opacity: 0, transform: "translateY(20px)", transition: "all 0.9s cubic-bezier(0.16,1,0.3,1)" }}
        >
          <Link
            href="/collections"
            className="group inline-flex items-center gap-3 bg-verra-gold text-verra-black text-[11px] tracking-widest2 uppercase font-semibold px-8 py-4 hover:bg-verra-gold-light transition-all duration-400"
          >
            Explore Collection
            <span className="w-4 h-px bg-verra-black group-hover:w-6 transition-all duration-300" />
          </Link>
          <Link
            href="/atelier"
            className="inline-flex items-center gap-3 border border-verra-ivory/30 text-verra-ivory text-[11px] tracking-widest2 uppercase font-medium px-8 py-4 hover:border-verra-gold hover:text-verra-gold transition-all duration-400"
          >
            Enter Atelier
          </Link>
        </div>

      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 right-12 flex flex-col items-center gap-3 hidden md:flex">
        <span className="text-[9px] tracking-widest3 uppercase text-verra-ash/60 rotate-90 origin-center">Scroll</span>
        <div className="w-px h-16 bg-gradient-to-b from-verra-gold/0 via-verra-gold/40 to-verra-gold/0 animate-pulse" />
      </div>
    </section>
  );
}
