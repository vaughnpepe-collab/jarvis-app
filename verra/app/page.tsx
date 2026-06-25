import React from "react";
import Link from "next/link";
import { Hero }           from "@/components/Hero";
import { ProductCard }    from "@/components/ProductCard";
import { MarqueeBar }     from "@/components/MarqueeBar";
import { StorySection }   from "@/components/StorySection";
import { AtelierSection } from "@/components/AtelierSection";
import { JournalSection } from "@/components/JournalSection";
import { Footer }         from "@/components/Footer";
import { products }       from "@/lib/products";

export default function HomePage() {
  const featured = products.slice(0, 6);
  const newArrivals = products.filter((p) => p.isNew);

  return (
    <>
      <Hero />
      <MarqueeBar />

      {/* Featured Collection */}
      <section className="py-24 px-6 md:px-16 xl:px-24 bg-verra-black">
        <div className="max-w-[1400px] mx-auto">

          {/* Section header */}
          <div className="flex flex-wrap items-end justify-between gap-4 mb-16">
            <div>
              <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-3">
                The Collection
              </p>
              <h2 className="font-serif text-[clamp(32px,4vw,56px)] font-light text-verra-ivory leading-tight">
                Winter Edit<br />
                <span className="italic">2026</span>
              </h2>
            </div>
            <Link
              href="/collections"
              className="group flex items-center gap-3 text-[11px] tracking-widest uppercase text-verra-ash hover:text-verra-gold transition-colors duration-300"
            >
              View All
              <span className="w-6 h-px bg-current group-hover:w-10 transition-all duration-300" />
            </Link>
          </div>

          {/* Product grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-16">
            {featured.map((product, i) => (
              <ProductCard key={product.id} product={product} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* Full-width editorial banner */}
      <div className="relative h-[60vh] overflow-hidden flex items-center justify-center">
        <div
          className="absolute inset-0 bg-cover bg-center animate-slow-zoom"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1509631179647-0177331693ae?w=1920&q=80')",
          }}
        />
        <div className="absolute inset-0 bg-verra-black/60" />
        <div className="relative z-10 text-center px-6">
          <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-5">
            Now Available
          </p>
          <h2 className="font-serif text-[clamp(40px,7vw,100px)] font-light text-verra-ivory leading-[0.95] mb-8">
            New Arrivals
          </h2>
          <Link
            href="/collections/new"
            className="inline-flex items-center gap-3 border border-verra-ivory/40 text-verra-ivory text-[11px] tracking-widest2 uppercase px-10 py-4 hover:border-verra-gold hover:text-verra-gold transition-all duration-400"
          >
            Shop New Arrivals
          </Link>
        </div>
      </div>

      <StorySection />
      <AtelierSection />
      <JournalSection />

      {/* Social proof bar */}
      <section className="py-20 px-6 md:px-16 xl:px-24 bg-verra-charcoal border-y border-verra-smoke/20">
        <div className="max-w-[1400px] mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-12 text-center">
            {[
              { num: "2,400+", label: "Pieces crafted annually" },
              { num: "47",     label: "Years combined mastery" },
              { num: "6",      label: "European workshops" },
              { num: "100%",   label: "Natural fibres" },
            ].map((stat) => (
              <div key={stat.num}>
                <p className="font-serif text-[clamp(32px,4vw,56px)] text-verra-gold font-light">{stat.num}</p>
                <p className="text-[11px] tracking-widest uppercase text-verra-ash/70 mt-2">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
