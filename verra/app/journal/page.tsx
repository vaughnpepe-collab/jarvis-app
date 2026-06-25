import React from "react";
import Image  from "next/image";
import Link   from "next/link";
import { Footer }         from "@/components/Footer";
import { journalPosts }   from "@/lib/products";

const categories = ["All", "Style", "Craftsmanship", "Travel", "Culture", "Collections"];

export default function JournalPage() {
  const [featured, ...rest] = journalPosts;

  return (
    <>
      {/* Header */}
      <div className="pt-36 pb-16 px-6 md:px-16 xl:px-24 border-b border-verra-smoke/20">
        <div className="max-w-[1400px] mx-auto">
          <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-3">VÉRRA</p>
          <h1 className="font-serif text-[clamp(40px,6vw,80px)] font-light text-verra-ivory leading-tight mb-8">
            The Journal
          </h1>
          <div className="flex gap-3 flex-wrap">
            {categories.map((c) => (
              <button
                key={c}
                className={`text-[10px] tracking-widest uppercase px-4 py-2 border transition-all duration-300 ${
                  c === "All"
                    ? "border-verra-gold text-verra-gold"
                    : "border-verra-smoke/30 text-verra-ash hover:border-verra-gold hover:text-verra-gold"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
      </div>

      <main className="py-16 px-6 md:px-16 xl:px-24 bg-verra-black">
        <div className="max-w-[1400px] mx-auto space-y-20">

          {/* Featured article */}
          <Link href={`/journal/${featured.slug}`} className="group grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="img-zoom-container aspect-[16/10] relative">
              <Image src={featured.image} alt={featured.title} fill className="object-cover" />
              <div className="absolute top-5 left-5 bg-verra-gold/90 text-verra-black text-[9px] tracking-widest uppercase font-semibold px-3 py-1.5">
                {featured.category}
              </div>
            </div>
            <div>
              <p className="text-[10px] tracking-widest uppercase text-verra-ash/60 mb-4">
                {featured.date} · {featured.readTime} read · By {featured.author}
              </p>
              <h2 className="font-serif text-4xl md:text-5xl text-verra-ivory group-hover:text-verra-gold transition-colors duration-300 leading-tight mb-5">
                {featured.title}
              </h2>
              <p className="text-base text-verra-ash/70 leading-8">{featured.excerpt}</p>
              <div className="mt-8 flex items-center gap-3 text-[11px] tracking-widest uppercase text-verra-gold">
                Read Article
                <span className="w-6 h-px bg-verra-gold group-hover:w-10 transition-all duration-300" />
              </div>
            </div>
          </Link>

          {/* Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 border-t border-verra-smoke/20 pt-16">
            {rest.map((post) => (
              <Link key={post.id} href={`/journal/${post.slug}`} className="group">
                <div className="img-zoom-container aspect-[4/3] relative mb-5">
                  <Image src={post.image} alt={post.title} fill className="object-cover" />
                  <div className="absolute top-4 left-4 bg-verra-black/80 text-verra-gold text-[9px] tracking-widest uppercase font-medium px-2.5 py-1">
                    {post.category}
                  </div>
                </div>
                <p className="text-[10px] tracking-widest uppercase text-verra-ash/50 mb-2">
                  {post.date} · {post.readTime}
                </p>
                <h3 className="font-serif text-xl text-verra-ivory group-hover:text-verra-gold transition-colors duration-300 leading-tight mb-3">
                  {post.title}
                </h3>
                <p className="text-sm text-verra-ash/60 leading-relaxed line-clamp-3">{post.excerpt}</p>
              </Link>
            ))}
          </div>

        </div>
      </main>

      <Footer />
    </>
  );
}
