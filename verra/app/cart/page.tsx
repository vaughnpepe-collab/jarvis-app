"use client";

import React, { useState } from "react";
import Image    from "next/image";
import Link     from "next/link";
import { Minus, Plus, X, ShoppingBag } from "lucide-react";
import { useCart }   from "@/components/CartContext";
import { formatPrice } from "@/lib/products";
import { Footer }    from "@/components/Footer";

export default function CartPage() {
  const { items, removeItem, updateQty, subtotal, itemCount } = useCart();
  const [promo,   setPromo]   = useState("");
  const [applied, setApplied] = useState("");

  const shipping = subtotal >= 500 ? 0 : 25;
  const total    = subtotal + shipping;

  if (itemCount === 0) {
    return (
      <>
        <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-6 text-center">
          <ShoppingBag size={48} strokeWidth={1} className="text-verra-smoke" />
          <h1 className="font-serif text-4xl text-verra-ivory font-light">Your bag is empty</h1>
          <p className="text-verra-ash/60 max-w-sm">
            You haven't added anything yet. Explore the collection and find your next piece.
          </p>
          <Link
            href="/collections"
            className="mt-4 bg-verra-gold text-verra-black text-[11px] tracking-widest2 uppercase font-semibold px-8 py-4 hover:bg-verra-gold-light transition-all duration-300"
          >
            Explore Collection
          </Link>
        </div>
        <Footer />
      </>
    );
  }

  return (
    <>
      <div className="pt-36 pb-24 px-6 md:px-16 xl:px-24">
        <div className="max-w-[1200px] mx-auto">

          <h1 className="font-serif text-[clamp(32px,4vw,56px)] font-light text-verra-ivory mb-2">Your Bag</h1>
          <p className="text-[11px] tracking-widest uppercase text-verra-ash/60 mb-14">
            {itemCount} {itemCount === 1 ? "piece" : "pieces"}
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-16">

            {/* Items */}
            <div className="lg:col-span-2 space-y-8">
              {items.map((item) => (
                <div key={`${item.id}-${item.size}`} className="flex gap-6 border-b border-verra-smoke/20 pb-8">
                  <Link href={`/products/${item.slug}`} className="relative w-28 h-36 flex-shrink-0 img-zoom-container">
                    <Image src={item.image} alt={item.name} fill className="object-cover" />
                  </Link>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between gap-4">
                      <Link href={`/products/${item.slug}`} className="font-serif text-xl text-verra-ivory hover:text-verra-gold transition-colors leading-tight">
                        {item.name}
                      </Link>
                      <button onClick={() => removeItem(item.id, item.size)} className="text-verra-ash/50 hover:text-red-400 transition-colors flex-shrink-0">
                        <X size={16} strokeWidth={1} />
                      </button>
                    </div>
                    <p className="text-[11px] tracking-wider text-verra-ash/50 uppercase mt-1">
                      {item.size} · {item.color}
                    </p>
                    <p className="text-base text-verra-ivory/80 mt-3">{formatPrice(item.price)}</p>
                    <div className="flex items-center gap-3 mt-4">
                      <button onClick={() => updateQty(item.id, item.size, item.quantity - 1)} className="w-8 h-8 flex items-center justify-center border border-verra-smoke/30 text-verra-ash hover:text-verra-ivory hover:border-verra-ivory transition-colors">
                        <Minus size={12} />
                      </button>
                      <span className="text-sm text-verra-ivory w-6 text-center">{item.quantity}</span>
                      <button onClick={() => updateQty(item.id, item.size, item.quantity + 1)} className="w-8 h-8 flex items-center justify-center border border-verra-smoke/30 text-verra-ash hover:text-verra-ivory hover:border-verra-ivory transition-colors">
                        <Plus size={12} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Summary */}
            <div className="space-y-6">
              <h2 className="font-serif text-2xl text-verra-ivory font-light">Order Summary</h2>

              <div className="space-y-3 text-sm text-verra-ash/70">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span className="text-verra-ivory">{formatPrice(subtotal)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Shipping</span>
                  <span className={shipping === 0 ? "text-verra-gold" : "text-verra-ivory"}>
                    {shipping === 0 ? "Complimentary" : formatPrice(shipping)}
                  </span>
                </div>
                {subtotal < 500 && (
                  <p className="text-[11px] text-verra-ash/50">
                    Spend {formatPrice(500 - subtotal)} more for free delivery
                  </p>
                )}
              </div>

              {/* Promo */}
              <div className="flex gap-0">
                <input
                  type="text"
                  placeholder="Promo code"
                  value={promo}
                  onChange={(e) => setPromo(e.target.value)}
                  className="flex-1 bg-transparent border border-verra-smoke/30 border-r-0 px-4 py-3 text-sm text-verra-ivory placeholder-verra-ash/30 outline-none focus:border-verra-gold/40 transition-colors"
                />
                <button
                  onClick={() => { if (promo) setApplied(promo); }}
                  className="bg-verra-smoke/30 text-verra-ash text-[10px] tracking-widest uppercase px-4 hover:bg-verra-smoke/50 transition-colors border border-verra-smoke/30"
                >
                  Apply
                </button>
              </div>
              {applied && <p className="text-[11px] text-verra-gold">Code "{applied}" applied</p>}

              <div className="border-t border-verra-smoke/20 pt-5 flex justify-between">
                <span className="text-[11px] tracking-widest uppercase text-verra-ash">Total</span>
                <span className="font-serif text-2xl text-verra-ivory">{formatPrice(total)}</span>
              </div>

              <button className="w-full bg-verra-gold text-verra-black text-[11px] tracking-widest2 uppercase font-semibold py-4 hover:bg-verra-gold-light transition-all duration-300">
                Proceed to Checkout
              </button>
              <Link href="/collections" className="block text-center text-[10px] tracking-widest uppercase text-verra-ash hover:text-verra-ivory transition-colors py-2">
                Continue Shopping
              </Link>

              {/* Trust */}
              <div className="pt-4 space-y-2 text-[10px] tracking-wider text-verra-ash/40">
                <p>✓ Secure encrypted checkout</p>
                <p>✓ Complimentary returns within 30 days</p>
                <p>✓ Certificate of authenticity included</p>
              </div>
            </div>

          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}
