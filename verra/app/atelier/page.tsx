"use client";

import React, { useState } from "react";
import Image    from "next/image";
import { Footer } from "@/components/Footer";
import { Calendar, User, Scissors, Lock } from "lucide-react";

const services = [
  {
    icon:     Scissors,
    title:    "Bespoke Tailoring",
    price:    "From £4,000",
    duration: "8–12 weeks",
    desc:     "A garment made entirely to your measurements. One consultation, two fittings, one masterpiece.",
    includes: ["Full pattern creation", "Two fittings", "Fabric consultation", "Lifetime alterations"],
  },
  {
    icon:     User,
    title:    "Wardrobe Consultation",
    price:    "£450",
    duration: "3 hours",
    desc:     "A private session to edit, refine, and invest in your wardrobe with intention.",
    includes: ["Pre-session questionnaire", "Wardrobe audit", "Style brief creation", "Shopping shortlist"],
  },
  {
    icon:     Calendar,
    title:    "Private Showroom Visit",
    price:    "Complimentary",
    duration: "By appointment",
    desc:     "See the full collection in private before it reaches the public. Champagne included.",
    includes: ["Full collection access", "Styling assistance", "Pre-order privileges", "Exclusive pieces"],
  },
  {
    icon:     Lock,
    title:    "Private Commission",
    price:    "From £8,000",
    duration: "12–20 weeks",
    desc:     "Something no one else will ever own. We create it together, from concept to cloth.",
    includes: ["Concept development", "Fabric sourcing", "Full bespoke construction", "Certificate of authenticity"],
  },
];

export default function AtelierPage() {
  const [selectedService, setSelectedService] = useState("");
  const [submitted, setSubmitted]             = useState(false);

  return (
    <>
      {/* Hero */}
      <div className="relative min-h-[60vh] flex items-end pb-20 overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: "url('https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1920&q=80')" }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-verra-black via-verra-black/50 to-transparent" />
        <div className="relative z-10 px-6 md:px-16 xl:px-24 max-w-3xl">
          <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-4">Private Services</p>
          <h1 className="font-serif text-[clamp(48px,7vw,96px)] font-light text-verra-ivory leading-[0.95]">
            The<br /><span className="italic">Atelier</span>
          </h1>
          <p className="text-base text-verra-ash/80 mt-6 max-w-md leading-8">
            An experience as rare as the garment. Everything at VÉRRA is available to be
            made exactly as you imagine it.
          </p>
        </div>
      </div>

      <main className="py-24 px-6 md:px-16 xl:px-24 bg-verra-black">
        <div className="max-w-[1200px] mx-auto">

          {/* Services */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-24">
            {services.map((s) => (
              <div
                key={s.title}
                className="border border-verra-smoke/20 p-8 hover:border-verra-gold/40 transition-colors duration-400 group"
              >
                <div className="flex items-start justify-between mb-6">
                  <div className="w-10 h-10 flex items-center justify-center border border-verra-gold/30 group-hover:border-verra-gold transition-colors duration-300">
                    <s.icon size={16} className="text-verra-gold" strokeWidth={1} />
                  </div>
                  <div className="text-right">
                    <p className="text-[11px] tracking-widest uppercase text-verra-gold font-medium">{s.price}</p>
                    <p className="text-[10px] tracking-wider text-verra-ash/50 mt-0.5">{s.duration}</p>
                  </div>
                </div>
                <h3 className="font-serif text-2xl text-verra-ivory font-light mb-3">{s.title}</h3>
                <p className="text-sm text-verra-ash/70 leading-7 mb-6">{s.desc}</p>
                <ul className="space-y-2">
                  {s.includes.map((item) => (
                    <li key={item} className="flex items-center gap-3 text-xs text-verra-ash/60">
                      <span className="w-3 h-px bg-verra-gold/50" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Booking form */}
          <div className="border-t border-verra-smoke/20 pt-20">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
              <div>
                <p className="text-[10px] tracking-widest3 uppercase text-verra-gold mb-5">Book Now</p>
                <h2 className="font-serif text-4xl text-verra-ivory font-light mb-6 leading-tight">
                  Request a<br /><span className="italic">Private Appointment</span>
                </h2>
                <p className="text-sm text-verra-ash/70 leading-7 mb-6">
                  Every appointment is handled personally by a VÉRRA atelier director.
                  We typically respond within 24 hours to arrange a time that suits you.
                </p>
                <div className="space-y-3 text-xs text-verra-ash/50">
                  <p>— London showroom available by appointment</p>
                  <p>— Milan and Paris visits available on request</p>
                  <p>— We travel for major commissions</p>
                </div>
              </div>

              {submitted ? (
                <div className="border border-verra-gold/30 p-10 text-center">
                  <p className="font-serif text-2xl text-verra-ivory mb-3">Thank you.</p>
                  <p className="text-sm text-verra-ash/70">
                    A VÉRRA atelier director will be in touch within 24 hours.
                  </p>
                </div>
              ) : (
                <form
                  onSubmit={(e) => { e.preventDefault(); setSubmitted(true); }}
                  className="space-y-5"
                >
                  {[
                    { label: "Full Name",     type: "text",  placeholder: "Your name" },
                    { label: "Email",         type: "email", placeholder: "your@email.com" },
                    { label: "Phone",         type: "tel",   placeholder: "+44 (0)..." },
                  ].map((f) => (
                    <div key={f.label}>
                      <label className="block text-[10px] tracking-widest uppercase text-verra-ash/60 mb-2">
                        {f.label}
                      </label>
                      <input
                        type={f.type}
                        placeholder={f.placeholder}
                        required
                        className="w-full bg-transparent border border-verra-smoke/30 px-5 py-4 text-sm text-verra-ivory placeholder-verra-ash/30 outline-none focus:border-verra-gold/50 transition-colors"
                      />
                    </div>
                  ))}
                  <div>
                    <label className="block text-[10px] tracking-widest uppercase text-verra-ash/60 mb-2">
                      Service
                    </label>
                    <select
                      value={selectedService}
                      onChange={(e) => setSelectedService(e.target.value)}
                      required
                      className="w-full bg-verra-charcoal border border-verra-smoke/30 px-5 py-4 text-sm text-verra-ivory outline-none focus:border-verra-gold/50 transition-colors appearance-none cursor-pointer"
                    >
                      <option value="">Select a service...</option>
                      {services.map((s) => (
                        <option key={s.title} value={s.title}>{s.title}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] tracking-widest uppercase text-verra-ash/60 mb-2">
                      Message (Optional)
                    </label>
                    <textarea
                      rows={4}
                      placeholder="Tell us more about what you're looking for..."
                      className="w-full bg-transparent border border-verra-smoke/30 px-5 py-4 text-sm text-verra-ivory placeholder-verra-ash/30 outline-none focus:border-verra-gold/50 transition-colors resize-none"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-verra-gold text-verra-black text-[11px] tracking-widest2 uppercase font-semibold py-4 hover:bg-verra-gold-light transition-all duration-300"
                  >
                    Request Appointment
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
