import type { Metadata } from "next";
import "./globals.css";
import { Navigation } from "@/components/Navigation";
import { CartProvider } from "@/components/CartContext";
import { CartDrawer } from "@/components/CartDrawer";

export const metadata: Metadata = {
  title:       "VÉRRA — Designed Beyond Time",
  description: "Crafting timeless garments for those who define their own legacy. Luxury fashion rooted in craftsmanship.",
  keywords:    "luxury fashion, designer clothing, cashmere, leather, tailored, VÉRRA",
  openGraph: {
    title:       "VÉRRA — Designed Beyond Time",
    description: "Crafting timeless garments for those who define their own legacy.",
    type:        "website",
    images: [{
      url:   "https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=1200&q=80",
      width: 1200, height: 630,
    }],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CartProvider>
          <Navigation />
          <main>{children}</main>
          <CartDrawer />
        </CartProvider>
      </body>
    </html>
  );
}
