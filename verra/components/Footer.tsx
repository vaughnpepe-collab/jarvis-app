import React from "react";
import Link from "next/link";
import { Instagram, Twitter, Youtube } from "lucide-react";

const footerLinks = {
  "The House": [
    { label: "About VÉRRA",   href: "/about" },
    { label: "Atelier",       href: "/atelier" },
    { label: "Sustainability", href: "/about#sustainability" },
    { label: "Careers",       href: "/careers" },
    { label: "Press",         href: "/press" },
  ],
  Collections: [
    { label: "New Arrivals",  href: "/collections/new" },
    { label: "Women",         href: "/collections/women" },
    { label: "Men",           href: "/collections/men" },
    { label: "All Products",  href: "/collections" },
    { label: "The Journal",   href: "/journal" },
  ],
  "Client Care": [
    { label: "Sizing Guide",  href: "/sizing" },
    { label: "Shipping",      href: "/shipping" },
    { label: "Returns",       href: "/returns" },
    { label: "Contact Us",    href: "/contact" },
    { label: "FAQ",           href: "/faq" },
  ],
};

export function Footer() {
  return (
    <footer className="bg-verra-charcoal border-t border-verra-smoke/20">

      {/* Newsletter */}
      <div className="border-b border-verra-smoke/20 py-16 px-6 md:px-16 xl:px-24">
        <div className="max-w-[1400px] mx-auto flex flex-wrap items-center justify-between gap-10">
          <div>
            <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-3">The Inner Circle</p>
            <h3 className="font-serif text-2xl md:text-3xl text-verra-ivory font-light">
              First access. No exceptions.
            </h3>
            <p className="text-sm text-verra-ash/70 mt-2 max-w-md">
              Private sales, new arrivals before the world sees them, atelier invitations.
              For those who prefer to know first.
            </p>
          </div>
          <form
            className="flex w-full max-w-md gap-0"
            onSubmit={(e) => e.preventDefault()}
          >
            <input
              type="email"
              placeholder="Your email address"
              className="flex-1 bg-verra-black/50 border border-verra-smoke/30 border-r-0 px-5 py-4 text-sm text-verra-ivory placeholder-verra-ash/40 outline-none focus:border-verra-gold/50 transition-colors"
            />
            <button
              type="submit"
              className="bg-verra-gold text-verra-black text-[11px] tracking-widest2 uppercase font-semibold px-6 py-4 whitespace-nowrap hover:bg-verra-gold-light transition-colors duration-300"
            >
              Join
            </button>
          </form>
        </div>
      </div>

      {/* Links */}
      <div className="py-16 px-6 md:px-16 xl:px-24">
        <div className="max-w-[1400px] mx-auto grid grid-cols-2 md:grid-cols-4 gap-12">

          {/* Brand */}
          <div>
            <Link href="/" className="font-serif text-2xl tracking-widest2 text-verra-ivory hover:text-verra-gold transition-colors duration-300">
              VÉRRA
            </Link>
            <p className="text-xs text-verra-ash/60 mt-3 leading-relaxed max-w-[180px]">
              Designed Beyond Time.<br />
              Made in Europe.
            </p>
            <div className="flex gap-4 mt-6">
              <a href="#" aria-label="Instagram" className="text-verra-ash/60 hover:text-verra-gold transition-colors">
                <Instagram size={16} strokeWidth={1.5} />
              </a>
              <a href="#" aria-label="Twitter" className="text-verra-ash/60 hover:text-verra-gold transition-colors">
                <Twitter size={16} strokeWidth={1.5} />
              </a>
              <a href="#" aria-label="YouTube" className="text-verra-ash/60 hover:text-verra-gold transition-colors">
                <Youtube size={16} strokeWidth={1.5} />
              </a>
            </div>
          </div>

          {Object.entries(footerLinks).map(([section, links]) => (
            <div key={section}>
              <h4 className="text-[10px] tracking-widest2 uppercase text-verra-ash font-medium mb-5">
                {section}
              </h4>
              <ul className="space-y-3">
                {links.map((l) => (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      className="text-sm text-verra-ash/60 hover:text-verra-gold transition-colors duration-300"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}

        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-verra-smoke/20 py-6 px-6 md:px-16 xl:px-24">
        <div className="max-w-[1400px] mx-auto flex flex-wrap items-center justify-between gap-4 text-[10px] tracking-wider text-verra-ash/40">
          <p>© {new Date().getFullYear()} VÉRRA. All rights reserved.</p>
          <div className="flex gap-6">
            <Link href="/privacy"  className="hover:text-verra-gold transition-colors">Privacy Policy</Link>
            <Link href="/terms"    className="hover:text-verra-gold transition-colors">Terms of Service</Link>
            <Link href="/cookies"  className="hover:text-verra-gold transition-colors">Cookie Settings</Link>
          </div>
        </div>
      </div>

    </footer>
  );
}
