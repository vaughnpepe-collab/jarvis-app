"use client";

import React, { useState } from "react";
import { Heart, ShoppingBag } from "lucide-react";
import type { Product } from "@/lib/products";
import { useCart } from "./CartContext";

interface Props { product: Product }

export function AddToBagForm({ product }: Props) {
  const { addItem }           = useCart();
  const [size,    setSize]    = useState<string>("");
  const [color,   setColor]   = useState(product.colors[0].name);
  const [wish,    setWish]    = useState(false);
  const [error,   setError]   = useState("");
  const [added,   setAdded]   = useState(false);

  const handleAdd = () => {
    if (!size) { setError("Please select a size"); return; }
    setError("");
    addItem({
      id:    product.id,
      slug:  product.slug,
      name:  product.name,
      price: product.price,
      size,
      color,
      image: product.images[0],
    });
    setAdded(true);
    setTimeout(() => setAdded(false), 3000);
  };

  return (
    <div className="space-y-6">

      {/* Colour selector */}
      <div>
        <p className="text-[10px] tracking-widest uppercase text-verra-ash/70 mb-3">
          Colour — <span className="text-verra-ivory">{color}</span>
        </p>
        <div className="flex gap-3">
          {product.colors.map((c) => (
            <button
              key={c.name}
              title={c.name}
              onClick={() => setColor(c.name)}
              className={`w-7 h-7 rounded-full border-2 transition-all duration-300 ${
                color === c.name ? "border-verra-gold scale-110" : "border-transparent hover:border-verra-ash/40"
              }`}
              style={{ backgroundColor: c.hex }}
            />
          ))}
        </div>
      </div>

      {/* Size selector */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] tracking-widest uppercase text-verra-ash/70">Size</p>
          <a href="/sizing" className="text-[10px] tracking-wider text-verra-gold underline">Size Guide</a>
        </div>
        <div className="flex gap-2 flex-wrap">
          {product.sizes.map((s) => (
            <button
              key={s}
              onClick={() => { setSize(s); setError(""); }}
              className={`min-w-[52px] h-11 border text-[12px] tracking-wider font-medium transition-all duration-300 ${
                size === s
                  ? "border-verra-gold bg-verra-gold text-verra-black"
                  : "border-verra-smoke/40 text-verra-ash hover:border-verra-ivory hover:text-verra-ivory"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleAdd}
          className={`flex-1 flex items-center justify-center gap-3 py-4 text-[11px] tracking-widest2 uppercase font-semibold transition-all duration-400 ${
            added
              ? "bg-verra-smoke text-verra-ivory"
              : "bg-verra-gold text-verra-black hover:bg-verra-gold-light"
          }`}
        >
          <ShoppingBag size={14} strokeWidth={1.5} />
          {added ? "Added to Bag" : "Add to Bag"}
        </button>
        <button
          onClick={() => setWish(!wish)}
          aria-label="Add to wishlist"
          className="w-14 h-[52px] border border-verra-smoke/40 flex items-center justify-center hover:border-verra-gold transition-colors duration-300"
        >
          <Heart
            size={16}
            strokeWidth={1.5}
            className={wish ? "fill-verra-gold text-verra-gold" : "text-verra-ash"}
          />
        </button>
      </div>

    </div>
  );
}
