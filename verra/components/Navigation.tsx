"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ShoppingBag, Search, Menu, X } from "lucide-react";
import { useCart } from "./CartContext";
import { cn } from "@/lib/utils";

const navLinks = [
  { label: "New Arrivals", href: "/collections/new" },
  { label: "Men",          href: "/collections/men" },
  { label: "Women",        href: "/collections/women" },
  { label: "Collections",  href: "/collections" },
  { label: "Atelier",      href: "/atelier" },
  { label: "Journal",      href: "/journal" },
  { label: "About",        href: "/about" },
];

export function Navigation() {
  const { itemCount, openCart } = useCart();
  const [scrolled,    setScrolled]    = useState(false);
  const [menuOpen,    setMenuOpen]    = useState(false);
  const [searchOpen,  setSearchOpen]  = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      {/* Top bar */}
      <div className="hidden md:flex items-center justify-center bg-verra-charcoal py-2 px-6 text-[10px] tracking-widest3 text-verra-ash uppercase">
        Complimentary shipping on orders over £500 &nbsp;·&nbsp; New Arrivals: The Winter Edit
      </div>

      {/* Main nav */}
      <nav
        className={cn(
          "fixed top-0 md:top-8 left-0 right-0 z-50 transition-all duration-500",
          scrolled
            ? "nav-blur bg-verra-black/80 border-b border-white/5 shadow-2xl md:top-0"
            : "bg-transparent"
        )}
      >
        <div className="max-w-[1600px] mx-auto px-6 md:px-12 h-16 md:h-20 flex items-center justify-between gap-8">

          {/* Logo */}
          <Link
            href="/"
            className="font-serif text-2xl md:text-3xl font-light tracking-widest2 text-verra-ivory flex-shrink-0 hover:text-verra-gold transition-colors duration-300"
          >
            VÉRRA
          </Link>

          {/* Desktop links */}
          <ul className="hidden lg:flex items-center gap-8">
            {navLinks.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className="text-[11px] tracking-widest font-medium text-verra-ash uppercase hover-underline hover:text-verra-ivory transition-colors duration-300"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>

          {/* Actions */}
          <div className="flex items-center gap-4">
            <button
              aria-label="Search"
              onClick={() => setSearchOpen(true)}
              className="text-verra-ash hover:text-verra-ivory transition-colors duration-300"
            >
              <Search size={18} strokeWidth={1.5} />
            </button>

            <button
              aria-label="Shopping bag"
              onClick={openCart}
              className="relative text-verra-ash hover:text-verra-ivory transition-colors duration-300"
            >
              <ShoppingBag size={18} strokeWidth={1.5} />
              {itemCount > 0 && (
                <span className="absolute -top-2 -right-2 w-4 h-4 rounded-full bg-verra-gold text-verra-black text-[9px] font-bold flex items-center justify-center">
                  {itemCount}
                </span>
              )}
            </button>

            <button
              aria-label="Menu"
              onClick={() => setMenuOpen(true)}
              className="lg:hidden text-verra-ash hover:text-verra-ivory transition-colors duration-300"
            >
              <Menu size={20} strokeWidth={1.5} />
            </button>
          </div>
        </div>
      </nav>

      {/* Search overlay */}
      {searchOpen && (
        <div className="fixed inset-0 z-[100] bg-verra-black/95 flex flex-col items-center justify-center px-6 animate-fade-in">
          <button
            onClick={() => setSearchOpen(false)}
            className="absolute top-8 right-8 text-verra-ash hover:text-verra-ivory transition-colors"
          >
            <X size={24} strokeWidth={1} />
          </button>
          <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-8">Search</p>
          <div className="w-full max-w-xl border-b border-verra-smoke pb-3 flex items-center gap-4">
            <Search size={18} strokeWidth={1} className="text-verra-ash flex-shrink-0" />
            <input
              autoFocus
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="What are you looking for?"
              className="flex-1 bg-transparent font-serif text-2xl text-verra-ivory placeholder-verra-smoke outline-none"
            />
          </div>
          <p className="mt-6 text-[11px] text-verra-ash tracking-wider">
            Try: wool coat, cashmere, leather jacket
          </p>
        </div>
      )}

      {/* Mobile menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-[100] bg-verra-black flex flex-col animate-fade-in">
          <div className="flex items-center justify-between px-6 h-16 border-b border-verra-charcoal">
            <Link href="/" className="font-serif text-2xl tracking-widest2 text-verra-ivory" onClick={() => setMenuOpen(false)}>
              VÉRRA
            </Link>
            <button onClick={() => setMenuOpen(false)} className="text-verra-ash hover:text-verra-ivory transition-colors">
              <X size={22} strokeWidth={1} />
            </button>
          </div>
          <ul className="flex-1 flex flex-col justify-center px-10 gap-8">
            {navLinks.map((l, i) => (
              <li key={l.href} style={{ animationDelay: `${i * 0.07}s` }} className="animate-fade-up">
                <Link
                  href={l.href}
                  onClick={() => setMenuOpen(false)}
                  className="font-serif text-4xl font-light text-verra-ivory hover:text-verra-gold transition-colors duration-300"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="px-10 pb-12 text-[11px] tracking-widest text-verra-ash uppercase">
            Crafted with intention. Designed beyond time.
          </div>
        </div>
      )}
    </>
  );
}
