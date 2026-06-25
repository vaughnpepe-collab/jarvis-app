"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Heart, Eye } from "lucide-react";
import type { Product } from "@/lib/products";
import { formatPrice } from "@/lib/products";
import { useCart } from "./CartContext";

interface Props {
  product: Product;
  index?: number;
}

export function ProductCard({ product, index = 0 }: Props) {
  const { addItem } = useCart();
  const [wishlist,    setWishlist]    = useState(false);
  const [hovered,     setHovered]     = useState(false);
  const [quickAdded,  setQuickAdded]  = useState(false);

  const handleQuickAdd = (e: React.MouseEvent) => {
    e.preventDefault();
    addItem({
      id:    product.id,
      slug:  product.slug,
      name:  product.name,
      price: product.price,
      size:  product.sizes[1] ?? product.sizes[0],
      color: product.colors[0].name,
      image: product.images[0],
    });
    setQuickAdded(true);
    setTimeout(() => setQuickAdded(false), 2000);
  };

  return (
    <article
      className="group flex flex-col"
      style={{
        animationDelay: `${index * 0.1}s`,
        animation: "fadeUp 0.9s cubic-bezier(0.16,1,0.3,1) both",
      }}
    >
      <Link href={`/products/${product.slug}`} className="block">
        {/* Image */}
        <div
          className="relative overflow-hidden bg-verra-charcoal aspect-[3/4] mb-4"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <Image
            src={product.images[0]}
            alt={product.name}
            fill
            className={`object-cover transition-transform duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] ${
              hovered ? "scale-105" : "scale-100"
            }`}
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          />

          {/* Second image on hover */}
          {product.images[1] && (
            <Image
              src={product.images[1]}
              alt={product.name}
              fill
              className={`object-cover absolute inset-0 transition-opacity duration-500 ${
                hovered ? "opacity-100" : "opacity-0"
              }`}
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
            />
          )}

          {/* Tag */}
          {product.tag && (
            <div className="absolute top-4 left-4 bg-verra-black/80 backdrop-blur-sm text-[9px] tracking-widest2 uppercase text-verra-gold px-3 py-1.5 font-medium">
              {product.tag}
            </div>
          )}

          {/* Wishlist */}
          <button
            onClick={(e) => { e.preventDefault(); setWishlist(!wishlist); }}
            className={`absolute top-4 right-4 w-8 h-8 flex items-center justify-center transition-all duration-300 ${
              hovered || wishlist ? "opacity-100" : "opacity-0"
            }`}
            aria-label="Add to wishlist"
          >
            <Heart
              size={16}
              strokeWidth={1.5}
              className={wishlist ? "fill-verra-gold text-verra-gold" : "text-verra-ivory"}
            />
          </button>

          {/* Quick view + add overlays */}
          <div
            className={`absolute bottom-0 left-0 right-0 flex transition-all duration-400 ${
              hovered ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"
            }`}
          >
            <Link
              href={`/products/${product.slug}`}
              className="flex-1 bg-verra-black/80 backdrop-blur-sm flex items-center justify-center gap-2 py-3 text-[10px] tracking-widest uppercase text-verra-ash hover:text-verra-ivory transition-colors border-r border-verra-smoke/30"
            >
              <Eye size={12} />
              Quick View
            </Link>
            <button
              onClick={handleQuickAdd}
              className={`flex-1 backdrop-blur-sm flex items-center justify-center py-3 text-[10px] tracking-widest uppercase transition-all duration-300 ${
                quickAdded
                  ? "bg-verra-gold text-verra-black"
                  : "bg-verra-black/80 text-verra-ash hover:text-verra-ivory"
              }`}
            >
              {quickAdded ? "Added" : "Add to Bag"}
            </button>
          </div>
        </div>

        {/* Info */}
        <div className="space-y-1">
          <p className="text-[10px] tracking-widest uppercase text-verra-ash">
            {product.category}
          </p>
          <h3 className="font-serif text-lg text-verra-ivory group-hover:text-verra-gold transition-colors duration-300 leading-tight">
            {product.name}
          </h3>
          <p className="text-xs text-verra-ash/70 line-clamp-1">{product.subtitle}</p>
          <p className="text-base text-verra-ivory/90 mt-2 font-light">
            {formatPrice(product.price)}
          </p>
        </div>
      </Link>

      {/* Colour swatches */}
      <div className="flex gap-2 mt-3">
        {product.colors.map((c) => (
          <button
            key={c.name}
            title={c.name}
            className="w-3.5 h-3.5 rounded-full border border-verra-smoke/40 hover:border-verra-gold transition-colors"
            style={{ backgroundColor: c.hex }}
          />
        ))}
      </div>
    </article>
  );
}
