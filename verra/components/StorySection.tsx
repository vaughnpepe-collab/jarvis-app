"use client";

import React, { useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";

export function StorySection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.querySelectorAll(".reveal").forEach((r, i) => {
              setTimeout(() => r.classList.add("visible"), i * 150);
            });
          }
        });
      },
      { threshold: 0.2 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="py-32 px-6 md:px-16 xl:px-24 overflow-hidden">
      <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 xl:gap-24 items-center">

        {/* Text side */}
        <div>
          <p className="reveal text-[10px] tracking-widest3 uppercase text-verra-gold mb-8">
            The Philosophy
          </p>
          <h2 className="reveal font-serif text-[clamp(40px,5vw,72px)] font-light text-verra-ivory leading-[1.1] mb-8">
            The Art of<br />
            <span className="italic">Precision</span>
          </h2>

          <div className="luxury-divider mb-8 reveal" />

          <p className="reveal text-base text-verra-ash leading-8 mb-6">
            Every VÉRRA piece is the culmination of an obsessive search — for the right fabric,
            the right maker, the right moment. We do not manufacture. We commission.
          </p>
          <p className="reveal text-base text-verra-ash leading-8 mb-6">
            Our ateliers span Florence, Milan, the Scottish Borders, and Porto. Each workshop
            was chosen not for proximity or price, but for a shared belief: that the invisible
            details are the only ones that matter.
          </p>
          <p className="reveal text-base text-verra-ash leading-8 mb-12">
            Hand-stitched canvases. Full-grain leathers that age with the wearer. Cashmere
            spun to our own specification. These are not selling points — they are the minimum
            standard we have set for ourselves.
          </p>

          <Link
            href="/about"
            className="reveal inline-flex items-center gap-3 text-[11px] tracking-widest2 uppercase text-verra-ivory border-b border-verra-gold pb-1 hover:text-verra-gold transition-colors duration-300"
          >
            Our Story
            <span className="w-6 h-px bg-current" />
          </Link>
        </div>

        {/* Image side */}
        <div className="grid grid-cols-2 gap-4">
          <div className="img-zoom-container aspect-[3/4] col-span-2 sm:col-span-1 row-span-2 relative">
            <Image
              src="https://images.unsplash.com/photo-1558171813-c28e4e92ee8d?w=900&q=85"
              alt="VÉRRA Craftsmanship"
              fill
              className="object-cover"
            />
          </div>
          <div className="img-zoom-container aspect-square relative hidden sm:block">
            <Image
              src="https://images.unsplash.com/photo-1540553016722-983e48a2cd10?w=600&q=85"
              alt="VÉRRA Detail"
              fill
              className="object-cover"
            />
          </div>
          <div className="img-zoom-container aspect-square relative hidden sm:block">
            <Image
              src="https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=600&q=85"
              alt="VÉRRA Studio"
              fill
              className="object-cover"
            />
          </div>
        </div>

      </div>
    </section>
  );
}
