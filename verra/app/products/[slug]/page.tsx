import React                    from "react";
import { notFound }             from "next/navigation";
import { getProductBySlug, products, formatPrice } from "@/lib/products";
import { ProductGallery }       from "@/components/ProductGallery";
import { AddToBagForm }         from "@/components/AddToBagForm";
import { ProductCard }          from "@/components/ProductCard";
import { Footer }               from "@/components/Footer";

interface Props { params: Promise<{ slug: string }> }

export default async function ProductPage({ params }: Props) {
  const { slug } = await params;
  const product  = getProductBySlug(slug);
  if (!product)  notFound();

  const related = products
    .filter((p) => p.id !== product.id && p.category === product.category)
    .slice(0, 3);

  return (
    <>
      {/* Breadcrumb */}
      <div className="pt-28 px-6 md:px-16 xl:px-24">
        <div className="max-w-[1400px] mx-auto">
          <nav className="flex items-center gap-2 text-[10px] tracking-widest uppercase text-verra-ash/50">
            <a href="/" className="hover:text-verra-gold transition-colors">Home</a>
            <span>/</span>
            <a href="/collections" className="hover:text-verra-gold transition-colors">Collections</a>
            <span>/</span>
            <span className="text-verra-ash">{product.name}</span>
          </nav>
        </div>
      </div>

      {/* Product section */}
      <section className="py-12 px-6 md:px-16 xl:px-24">
        <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 xl:gap-24">

          {/* Gallery */}
          <ProductGallery images={product.images} name={product.name} tag={product.tag} />

          {/* Details */}
          <div className="lg:pt-4 lg:sticky lg:top-24 lg:self-start">
            {product.isNew && (
              <span className="text-[9px] tracking-widest2 uppercase text-verra-gold font-medium mb-3 block">
                New Arrival
              </span>
            )}
            {product.isBestSeller && (
              <span className="text-[9px] tracking-widest2 uppercase text-verra-gold font-medium mb-3 block">
                Best Seller
              </span>
            )}

            <h1 className="font-serif text-[clamp(28px,3.5vw,48px)] font-light text-verra-ivory leading-tight mb-2">
              {product.name}
            </h1>
            <p className="text-sm text-verra-ash/70 italic mb-6">{product.subtitle}</p>

            <p className="font-serif text-3xl text-verra-ivory mb-8">
              {formatPrice(product.price)}
            </p>

            <p className="text-base text-verra-ash/80 leading-8 mb-10">
              {product.description}
            </p>

            <AddToBagForm product={product} />

            {/* Details accordion */}
            <div className="mt-10 border-t border-verra-smoke/20 space-y-0">
              {[
                { label: "Fabric & Materials", content: product.fabric },
                { label: "Origin",             content: product.origin },
                { label: "The Story",          content: product.story },
                { label: "Care Instructions",  content: product.care },
              ].map((d) => (
                <details key={d.label} className="group border-b border-verra-smoke/20 py-5 cursor-pointer">
                  <summary className="flex items-center justify-between text-[11px] tracking-widest uppercase text-verra-ash/80 list-none hover:text-verra-ivory transition-colors">
                    {d.label}
                    <span className="text-verra-gold text-lg leading-none group-open:rotate-45 transition-transform duration-300">+</span>
                  </summary>
                  <p className="mt-4 text-sm text-verra-ash/70 leading-relaxed">
                    {d.content}
                  </p>
                </details>
              ))}
            </div>

            {/* Trust signals */}
            <div className="mt-8 flex flex-wrap gap-6 text-[10px] tracking-widest uppercase text-verra-ash/50">
              <span>Complimentary Delivery</span>
              <span>·</span>
              <span>30-Day Returns</span>
              <span>·</span>
              <span>Authenticity Guaranteed</span>
            </div>
          </div>
        </div>
      </section>

      {/* Related */}
      {related.length > 0 && (
        <section className="py-24 px-6 md:px-16 xl:px-24 border-t border-verra-smoke/20">
          <div className="max-w-[1400px] mx-auto">
            <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-3">You May Also Like</p>
            <h2 className="font-serif text-3xl text-verra-ivory font-light mb-14">Related Pieces</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-16">
              {related.map((p, i) => (
                <ProductCard key={p.id} product={p} index={i} />
              ))}
            </div>
          </div>
        </section>
      )}

      <Footer />
    </>
  );
}

export function generateStaticParams() {
  return products.map((p) => ({ slug: p.slug }));
}
