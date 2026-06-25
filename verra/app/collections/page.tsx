import React from "react";
import Link from "next/link";
import { ProductCard } from "@/components/ProductCard";
import { Footer }      from "@/components/Footer";
import { products }    from "@/lib/products";

export default function CollectionsPage() {
  return (
    <>
      {/* Page header */}
      <div className="pt-36 pb-16 px-6 md:px-16 xl:px-24 border-b border-verra-smoke/20">
        <div className="max-w-[1400px] mx-auto flex flex-wrap items-end justify-between gap-8">
          <div>
            <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-3">VÉRRA</p>
            <h1 className="font-serif text-[clamp(40px,6vw,80px)] font-light text-verra-ivory leading-tight">
              All Collections
            </h1>
          </div>
          <div className="flex gap-3 flex-wrap">
            {["All", "Women", "Men", "New Arrivals"].map((f) => (
              <Link
                key={f}
                href={f === "All" ? "/collections" : `/collections/${f.toLowerCase().replace(" ", "-")}`}
                className={`text-[10px] tracking-widest uppercase px-4 py-2 border transition-all duration-300 ${
                  f === "All"
                    ? "border-verra-gold text-verra-gold"
                    : "border-verra-smoke/30 text-verra-ash hover:border-verra-gold hover:text-verra-gold"
                }`}
              >
                {f}
              </Link>
            ))}
          </div>
        </div>
      </div>

      <main className="py-20 px-6 md:px-16 xl:px-24 bg-verra-black">
        <div className="max-w-[1400px] mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-16">
            {products.map((product, i) => (
              <ProductCard key={product.id} product={product} index={i} />
            ))}
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
