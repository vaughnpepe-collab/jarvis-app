"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { Scissors, User, Calendar, Lock } from "lucide-react";

const services = [
  {
    icon:        Scissors,
    title:       "Custom Tailoring",
    description: "A garment built entirely to your measurements, in fabrics chosen with you. Takes 8–12 weeks.",
  },
  {
    icon:        User,
    title:       "Personal Styling",
    description: "A one-on-one session with a VÉRRA stylist. We build a wardrobe around you, not around a season.",
  },
  {
    icon:        Calendar,
    title:       "VIP Appointments",
    description: "Private showroom access. See the full collection before it goes public, with champagne on arrival.",
  },
  {
    icon:        Lock,
    title:       "Private Collections",
    description: "Exclusive pieces never seen online — created for clients who want something that cannot be found elsewhere.",
  },
];

export function AtelierSection() {
  return (
    <section className="relative overflow-hidden bg-verra-charcoal py-32 px-6 md:px-16 xl:px-24">
      <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 xl:gap-24 items-center">

        {/* Image */}
        <div className="relative order-2 lg:order-1">
          <div className="img-zoom-container aspect-[4/5] relative">
            <Image
              src="https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=900&q=85"
              alt="VÉRRA Atelier"
              fill
              className="object-cover"
            />
          </div>
          {/* Floating stat card */}
          <div className="absolute bottom-8 -right-4 md:right-8 bg-verra-black/90 backdrop-blur-sm border border-verra-smoke/30 px-6 py-5 min-w-[180px]">
            <p className="font-serif text-4xl text-verra-gold">47</p>
            <p className="text-[10px] tracking-widest uppercase text-verra-ash mt-1">
              Years of combined<br />tailoring mastery
            </p>
          </div>
        </div>

        {/* Content */}
        <div className="order-1 lg:order-2">
          <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-8">The Atelier</p>
          <h2 className="font-serif text-[clamp(36px,4vw,60px)] font-light text-verra-ivory leading-tight mb-6">
            An Experience<br />
            <span className="italic">As Rare As</span><br />
            the Garment
          </h2>
          <div className="luxury-divider mb-8" />
          <p className="text-base text-verra-ash leading-8 mb-12">
            The VÉRRA atelier is not a fitting room — it is a conversation about who
            you are and who you intend to become. Every service is private, unhurried,
            and focused entirely on you.
          </p>

          {/* Services grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-12">
            {services.map((s) => (
              <div key={s.title} className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center border border-verra-gold/30 mt-0.5">
                  <s.icon size={14} className="text-verra-gold" strokeWidth={1} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-verra-ivory mb-1">{s.title}</h3>
                  <p className="text-xs text-verra-ash/80 leading-relaxed">{s.description}</p>
                </div>
              </div>
            ))}
          </div>

          <Link
            href="/atelier"
            className="inline-flex items-center gap-4 bg-verra-gold text-verra-black text-[11px] tracking-widest2 uppercase font-semibold px-8 py-4 hover:bg-verra-gold-light transition-all duration-300"
          >
            Book a Private Appointment
          </Link>
        </div>

      </div>
    </section>
  );
}
