"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { X, Plus, Minus, ShoppingBag } from "lucide-react";
import { useCart } from "./CartContext";
import { formatPrice } from "@/lib/products";

export function CartDrawer() {
  const { items, isOpen, closeCart, removeItem, updateQty, subtotal, itemCount } = useCart();

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm"
          onClick={closeCart}
        />
      )}

      {/* Drawer */}
      <aside
        className={`fixed top-0 right-0 bottom-0 z-[201] w-full max-w-md bg-verra-charcoal flex flex-col transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-6 border-b border-verra-smoke/30">
          <div>
            <h2 className="font-serif text-xl text-verra-ivory">Your Bag</h2>
            <p className="text-[11px] tracking-widest text-verra-ash uppercase mt-0.5">
              {itemCount} {itemCount === 1 ? "piece" : "pieces"}
            </p>
          </div>
          <button onClick={closeCart} className="text-verra-ash hover:text-verra-ivory transition-colors">
            <X size={20} strokeWidth={1} />
          </button>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <ShoppingBag size={40} strokeWidth={1} className="text-verra-smoke" />
              <p className="font-serif text-lg text-verra-ash text-center">
                Your bag is empty
              </p>
              <p className="text-[11px] tracking-wider text-verra-smoke uppercase text-center">
                Discover the collection
              </p>
              <Link
                href="/collections"
                onClick={closeCart}
                className="mt-4 text-[11px] tracking-widest uppercase text-verra-gold border border-verra-gold px-6 py-3 hover:bg-verra-gold hover:text-verra-black transition-all duration-300"
              >
                Shop Now
              </Link>
            </div>
          ) : (
            items.map((item) => (
              <div key={`${item.id}-${item.size}`} className="flex gap-5">
                <div className="relative w-20 h-24 flex-shrink-0 bg-verra-smoke/20 overflow-hidden">
                  <Image src={item.image} alt={item.name} fill className="object-cover" />
                </div>
                <div className="flex-1 min-w-0">
                  <Link
                    href={`/products/${item.slug}`}
                    onClick={closeCart}
                    className="font-serif text-base text-verra-ivory hover:text-verra-gold transition-colors line-clamp-2"
                  >
                    {item.name}
                  </Link>
                  <p className="text-[11px] text-verra-ash mt-1 uppercase tracking-wider">
                    {item.size} · {item.color}
                  </p>
                  <p className="text-sm text-verra-ivory mt-2 font-medium">
                    {formatPrice(item.price)}
                  </p>
                  <div className="flex items-center gap-3 mt-3">
                    <button
                      onClick={() => updateQty(item.id, item.size, item.quantity - 1)}
                      className="w-6 h-6 flex items-center justify-center border border-verra-smoke/40 text-verra-ash hover:text-verra-ivory hover:border-verra-ivory transition-colors"
                    >
                      <Minus size={10} />
                    </button>
                    <span className="text-sm text-verra-ivory w-4 text-center">{item.quantity}</span>
                    <button
                      onClick={() => updateQty(item.id, item.size, item.quantity + 1)}
                      className="w-6 h-6 flex items-center justify-center border border-verra-smoke/40 text-verra-ash hover:text-verra-ivory hover:border-verra-ivory transition-colors"
                    >
                      <Plus size={10} />
                    </button>
                    <button
                      onClick={() => removeItem(item.id, item.size)}
                      className="ml-auto text-[10px] tracking-wider uppercase text-verra-ash hover:text-red-400 transition-colors"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="px-8 py-6 border-t border-verra-smoke/30 space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-[11px] tracking-widest uppercase text-verra-ash">Subtotal</span>
              <span className="font-serif text-xl text-verra-ivory">{formatPrice(subtotal)}</span>
            </div>
            <p className="text-[10px] text-verra-ash/60 tracking-wider">
              Taxes and shipping calculated at checkout
            </p>
            <Link
              href="/cart"
              onClick={closeCart}
              className="block w-full bg-verra-gold text-verra-black text-center text-[12px] tracking-widest2 uppercase font-semibold py-4 hover:bg-verra-gold-light transition-all duration-300"
            >
              Proceed to Checkout
            </Link>
            <button
              onClick={closeCart}
              className="block w-full text-center text-[11px] tracking-widest uppercase text-verra-ash hover:text-verra-ivory transition-colors py-2"
            >
              Continue Shopping
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
