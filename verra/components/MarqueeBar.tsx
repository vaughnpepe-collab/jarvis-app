import React from "react";

const items = [
  "Complimentary Delivery on Orders Over £500",
  "Free Returns Within 30 Days",
  "Crafted in Europe — Italy · Scotland · Portugal",
  "Exclusive Access: New Arrivals Every Season",
  "Bespoke Tailoring Available — Visit the Atelier",
];

export function MarqueeBar() {
  return (
    <div className="bg-verra-charcoal border-y border-verra-smoke/20 py-3 overflow-hidden">
      <div className="marquee-track animate-marquee whitespace-nowrap">
        {[...items, ...items].map((item, i) => (
          <span key={i} className="inline-block text-[10px] tracking-widest uppercase text-verra-ash px-8">
            {item}
            <span className="mx-8 text-verra-gold">·</span>
          </span>
        ))}
      </div>
    </div>
  );
}
