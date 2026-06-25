import React    from "react";
import Image    from "next/image";
import Link     from "next/link";
import { Footer } from "@/components/Footer";

export default function AboutPage() {
  return (
    <>
      {/* Hero */}
      <div className="relative min-h-[60vh] flex items-end pb-20 overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: "url('https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=1920&q=80')" }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-verra-black via-verra-black/50 to-transparent" />
        <div className="relative z-10 px-6 md:px-16 xl:px-24 max-w-3xl">
          <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-4">The House</p>
          <h1 className="font-serif text-[clamp(48px,7vw,96px)] font-light text-verra-ivory leading-[0.95]">
            About<br /><span className="italic">VÉRRA</span>
          </h1>
        </div>
      </div>

      <main className="py-24 px-6 md:px-16 xl:px-24 bg-verra-black">
        <div className="max-w-[1000px] mx-auto space-y-24">

          {/* Mission */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-start">
            <div>
              <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-5">Mission</p>
              <h2 className="font-serif text-4xl md:text-5xl font-light text-verra-ivory leading-tight mb-6">
                We don't follow.<br />
                <span className="italic">We define.</span>
              </h2>
            </div>
            <div className="space-y-5 text-verra-ash/80 leading-8">
              <p>
                VÉRRA was founded on a single conviction: that the fashion industry's
                obsession with speed and volume is incompatible with quality, integrity,
                and the kind of beauty that endures.
              </p>
              <p>
                We make fewer things. Better things. Things that take months to perfect
                and years to appreciate. Our clients don't buy a new wardrobe each season —
                they build one, piece by piece, over a lifetime.
              </p>
            </div>
          </div>

          {/* Founder story */}
          <div className="border-t border-verra-smoke/20 pt-16 grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
            <div className="relative aspect-[3/4] img-zoom-container">
              <Image
                src="https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=900&q=85"
                alt="VÉRRA Founder"
                fill
                className="object-cover"
              />
            </div>
            <div className="space-y-6">
              <p className="text-[10px] tracking-widest3 uppercase text-verra-gold">The Founder</p>
              <h3 className="font-serif text-3xl font-light text-verra-ivory italic">
                "I wanted to make one thing perfectly. Then another. Then another. That's still the idea."
              </h3>
              <div className="luxury-divider" />
              <p className="text-verra-ash/80 leading-8">
                Elena Voronova trained under two of Europe's last true couturiers before spending
                a decade managing fabric sourcing for houses you'd recognise but won't find mentioned
                here. VÉRRA is what she built when she grew tired of making compromises.
              </p>
              <p className="text-verra-ash/80 leading-8">
                The brand launched with three pieces in 2019. All three sold out the same afternoon.
                Nothing has changed — except the number of artisans we work with and the depth
                of our conviction.
              </p>
            </div>
          </div>

          {/* Values */}
          <div className="border-t border-verra-smoke/20 pt-16" id="sustainability">
            <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-10">Our Values</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
              {[
                {
                  title: "Craftsmanship First",
                  body:  "We work exclusively with ateliers that have been operating for at least two generations. Technique takes decades to perfect — we don't shortcut it.",
                },
                {
                  title: "Honest Materials",
                  body:  "Every fibre we use is natural and traceable: wool from farms we've visited, leather from tanneries we audit annually, silk from mills we know by name.",
                },
                {
                  title: "Sustainability by Design",
                  body:  "The most sustainable garment is the one you wear for twenty years. We make clothes that earn that commitment: serviceable, repairable, and beautiful enough to warrant it.",
                },
                {
                  title: "Radical Transparency",
                  body:  "Our supply chain has no hidden steps. If you want to know where your jacket was tanned, stitched, or finished — ask. We'll tell you, and show you.",
                },
              ].map((v) => (
                <div key={v.title} className="flex gap-5">
                  <div className="w-px bg-verra-gold/40 flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="font-serif text-xl text-verra-ivory mb-3">{v.title}</h4>
                    <p className="text-sm text-verra-ash/70 leading-7">{v.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </main>

      <Footer />
    </>
  );
}
