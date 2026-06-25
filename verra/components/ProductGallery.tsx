"use client";

import React, { useState } from "react";
import Image from "next/image";
import { ZoomIn } from "lucide-react";

interface Props {
  images: string[];
  name:   string;
  tag?:   string;
}

export function ProductGallery({ images, name, tag }: Props) {
  const [active, setActive]   = useState(0);
  const [zoomed, setZoomed]   = useState(false);

  return (
    <div className="flex flex-col gap-4">
      {/* Main image */}
      <div
        className="relative aspect-[3/4] bg-verra-charcoal overflow-hidden group cursor-zoom-in"
        onClick={() => setZoomed(true)}
      >
        <Image
          src={images[active]}
          alt={name}
          fill
          className="object-cover transition-transform duration-700 group-hover:scale-[1.03]"
          priority
          sizes="(max-width: 1024px) 100vw, 50vw"
        />
        {tag && (
          <div className="absolute top-5 left-5 bg-verra-black/80 text-verra-gold text-[9px] tracking-widest2 uppercase px-3 py-1.5 font-medium">
            {tag}
          </div>
        )}
        <button className="absolute bottom-5 right-5 bg-verra-black/60 backdrop-blur-sm p-3 text-verra-ash/70 hover:text-verra-ivory transition-colors opacity-0 group-hover:opacity-100 duration-300">
          <ZoomIn size={16} strokeWidth={1.5} />
        </button>
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="flex gap-3">
          {images.map((img, i) => (
            <button
              key={i}
              onClick={() => setActive(i)}
              className={`relative w-20 h-24 flex-shrink-0 overflow-hidden transition-all duration-300 ${
                active === i
                  ? "ring-1 ring-verra-gold"
                  : "ring-1 ring-transparent opacity-60 hover:opacity-100"
              }`}
            >
              <Image src={img} alt={`${name} view ${i + 1}`} fill className="object-cover" />
            </button>
          ))}
        </div>
      )}

      {/* Zoom overlay */}
      {zoomed && (
        <div
          className="fixed inset-0 z-[300] bg-verra-black/95 flex items-center justify-center p-8"
          onClick={() => setZoomed(false)}
        >
          <div className="relative w-full max-w-3xl aspect-[3/4]">
            <Image
              src={images[active]}
              alt={name}
              fill
              className="object-contain"
            />
          </div>
          <button className="absolute top-6 right-6 text-verra-ash hover:text-verra-ivory text-2xl">×</button>
        </div>
      )}
    </div>
  );
}
