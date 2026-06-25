import React from "react";
import { notFound }    from "next/navigation";
import { ProductCard } from "@/components/ProductCard";
import { Footer }      from "@/components/Footer";
import { products }    from "@/lib/products";

interface Props { params: Promise<{ category: string }> }

const titles: Record<string, string> = {
  men:          "Men's Collection",
  women:        "Women's Collection",
  new:          "New Arrivals",
  "new-arrivals": "New Arrivals",
  collection:   "Collections",
};

export default async function CategoryPage({ params }: Props) {
  const { category } = await params;
  const label   = titles[category];

  const filtered = category === "new" || category === "new-arrivals"
    ? products.filter((p) => p.isNew)
    : products.filter((p) => p.category === category);

  if (!label) notFound();

  return (
    <>
      <div className="pt-36 pb-16 px-6 md:px-16 xl:px-24 border-b border-verra-smoke/20">
        <div className="max-w-[1400px] mx-auto">
          <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-3">VÉRRA</p>
          <h1 className="font-serif text-[clamp(40px,6vw,80px)] font-light text-verra-ivory leading-tight">
            {label}
          </h1>
          <p className="text-sm text-verra-ash/60 mt-3">
            {filtered.length} {filtered.length === 1 ? "piece" : "pieces"}
          </p>
        </div>
      </div>

      <main className="py-20 px-6 md:px-16 xl:px-24 bg-verra-black">
        <div className="max-w-[1400px] mx-auto">
          {filtered.length === 0 ? (
            <div className="py-24 text-center">
              <p className="font-serif text-2xl text-verra-ash">No pieces found in this collection.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-16">
              {filtered.map((product, i) => (
                <ProductCard key={product.id} product={product} index={i} />
              ))}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </>
  );
}

export function generateStaticParams() {
  return ["men", "women", "new", "new-arrivals", "collection"].map((c) => ({ category: c }));
}
