import React from "react";
import Image from "next/image";
import Link from "next/link";
import { journalPosts } from "@/lib/products";

export function JournalSection() {
  const featured = journalPosts[0];
  const rest     = journalPosts.slice(1, 3);

  return (
    <section className="py-32 px-6 md:px-16 xl:px-24 bg-verra-black">
      <div className="max-w-[1400px] mx-auto">

        {/* Header */}
        <div className="flex flex-wrap items-end justify-between gap-4 mb-16">
          <div>
            <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-3">
              The Journal
            </p>
            <h2 className="font-serif text-[clamp(32px,4vw,56px)] font-light text-verra-ivory leading-tight">
              Ideas Worth<br />
              <span className="italic">Wearing</span>
            </h2>
          </div>
          <Link
            href="/journal"
            className="text-[11px] tracking-widest uppercase text-verra-ash border-b border-verra-smoke pb-0.5 hover:text-verra-gold hover:border-verra-gold transition-colors duration-300"
          >
            View All Articles
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* Featured */}
          <Link href={`/journal/${featured.slug}`} className="group lg:col-span-2">
            <div className="img-zoom-container aspect-[16/10] relative mb-6">
              <Image
                src={featured.image}
                alt={featured.title}
                fill
                className="object-cover"
              />
              <div className="absolute top-4 left-4 bg-verra-gold/90 text-verra-black text-[9px] tracking-widest uppercase font-semibold px-3 py-1.5">
                {featured.category}
              </div>
            </div>
            <p className="text-[10px] tracking-widest uppercase text-verra-ash mb-2">
              {featured.date} · {featured.readTime} read · {featured.author}
            </p>
            <h3 className="font-serif text-2xl md:text-3xl text-verra-ivory group-hover:text-verra-gold transition-colors duration-300 leading-tight mb-3">
              {featured.title}
            </h3>
            <p className="text-sm text-verra-ash/80 leading-relaxed line-clamp-2">{featured.excerpt}</p>
          </Link>

          {/* Side articles */}
          <div className="flex flex-col gap-8">
            {rest.map((post) => (
              <Link key={post.id} href={`/journal/${post.slug}`} className="group flex gap-5">
                <div className="img-zoom-container w-24 h-28 flex-shrink-0 relative">
                  <Image src={post.image} alt={post.title} fill className="object-cover" />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-[9px] tracking-widest uppercase text-verra-gold">{post.category}</span>
                  <h4 className="font-serif text-base text-verra-ivory group-hover:text-verra-gold transition-colors duration-300 mt-1 leading-tight line-clamp-3">
                    {post.title}
                  </h4>
                  <p className="text-[10px] text-verra-ash/60 mt-2">{post.date}</p>
                </div>
              </Link>
            ))}
          </div>

        </div>
      </div>
    </section>
  );
}
