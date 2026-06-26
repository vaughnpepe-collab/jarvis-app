#!/usr/bin/env python3
"""
HW Web Design — Free Mockup Generator.

Reads the leads CSV and builds a polished, personalised single-page website
mockup for each top callable lead (business name, town and phone baked in),
plus a gallery index. These are your closing tool: "I built you a sample —
have a look." They deploy with the repo, so each lead's mockup is live at
  https://hwwebdesign.co.uk/mockups/<slug>/
once this branch is merged to main.

Usage:
    python mockup_gen.py                      # uses the default area CSV
    python mockup_gen.py leads/leads_x.csv    # any sweep CSV

Sample content (reviews, prices, stats) is illustrative and clearly labelled
as a design concept on every page.
"""
import csv
import os
import sys

from area_sweep import lead_slug, WARM_LIMIT, BASE_URL

# ---------------------------------------------------------------- palettes
ARCH = {
    "food": dict(primary="#7c1c1c", dark="#5c1414", accent="#c9972a",
                 accent2="#f0c060", hero="#1c0902,#3d1a08,#2d1005",
                 text="#3d2b1f", grey="#7a6a5a", border="#e8ddd0", cream="#fdf8f0",
                 stats=[("4.9★", "Google rating"), ("Fresh", "Made daily"),
                        ("7 Days", "Open all week")],
                 why=[("Fresh, Local Ingredients", "Prepared fresh every day — nothing frozen, nothing rushed."),
                      ("Dine In or Takeaway", "Enjoy the full experience with us, or take it home — your choice."),
                      ("A Warm Welcome", "Friendly, family-run service that keeps locals coming back."),
                      ("Great Value", "Generous portions and fair prices, every single visit.")]),
    "beauty": dict(primary="#9d2b5b", dark="#7a1f47", accent="#c79a4b",
                   accent2="#ecd2a0", hero="#2a0e1f,#4a1942,#3a1530",
                   text="#3a2230", grey="#8a7280", border="#ecdde5", cream="#fdf6f9",
                   stats=[("4.9★", "Google rating"), ("Walk-ins", "Welcome"),
                          ("Expert", "Trained stylists")],
                   why=[("Skilled, Friendly Team", "Experienced stylists and therapists who genuinely listen."),
                        ("Relaxing Space", "A calm, welcoming salon where you can switch off and unwind."),
                        ("Quality Products", "Only trusted, professional-grade products on every treatment."),
                        ("Easy Booking", "Book online in seconds, or just pop in — whatever suits you.")]),
    "clinic": dict(primary="#0e7490", dark="#0b5566", accent="#14b8a6",
                   accent2="#5eead4", hero="#062a33,#0e4d5c,#0a3a44",
                   text="#143641", grey="#5f7a82", border="#d6e7ea", cream="#f0fbfc",
                   stats=[("4.9★", "Patient rating"), ("New", "Patients welcome"),
                          ("Same-week", "Appointments")],
                   why=[("Gentle, Modern Care", "Up-to-date treatments delivered with a calm, caring touch."),
                        ("All The Family", "Welcoming patients of every age — from little ones to grandparents."),
                        ("Clear Pricing", "Know exactly what to expect, with no surprises on the bill."),
                        ("Easy To Reach", "Convenient local appointments that fit around your life.")]),
    "trades": dict(primary="#1e3a5f", dark="#142b47", accent="#f97316",
                   accent2="#fdba74", hero="#0f1f33,#1e3a5f,#16293f",
                   text="#1f2937", grey="#64748b", border="#dbe3ec", cream="#f4f7fb",
                   stats=[("Free", "Quotes"), ("Fully", "Insured"),
                          ("Fast", "Response"), ("12mo", "Guarantee")],
                   why=[("Fixed Prices, No Surprises", "We quote upfront and stick to it — you'll never get a shock invoice."),
                        ("Fully Insured & Certified", "Properly qualified, fully insured work you can rely on."),
                        ("Fast Local Response", "We answer the phone and turn up when we say we will."),
                        ("Workmanship Guarantee", "If something's not right, we come back and fix it.")]),
    "fitness": dict(primary="#111827", dark="#030712", accent="#84cc16",
                    accent2="#bef264", hero="#0a0f1c,#111827,#0d1322",
                    text="#111827", grey="#6b7280", border="#e5e7eb", cream="#f7f8f9",
                    stats=[("Open", "Early & late"), ("Classes", "Every day"),
                           ("No", "Judgement")],
                    why=[("Kit For Every Goal", "Free weights, machines and a functional zone — whatever your training."),
                         ("Friendly Community", "A welcoming, no-ego gym where everyone fits in."),
                         ("Expert Coaching", "Qualified trainers on hand to keep you safe and progressing."),
                         ("Flexible Memberships", "No tie-ins, no nonsense — join on terms that suit you.")]),
    "professional": dict(primary="#1e293b", dark="#0f172a", accent="#2563eb",
                         accent2="#93c5fd", hero="#0b1220,#1e293b,#172033",
                         text="#0f172a", grey="#64748b", border="#e2e8f0", cream="#f8fafc",
                         stats=[("Fixed", "Fees"), ("Free", "First chat"),
                                ("Local", "& independent")],
                         why=[("Plain-English Advice", "No jargon — just clear guidance you can actually act on."),
                              ("Fixed, Fair Fees", "Know your costs upfront, with no surprise bills."),
                              ("Proactive Support", "We chase the deadlines so you don't have to."),
                              ("Local & Personal", "A real person who knows your business, not a call centre.")]),
}

# ---------------------------------------------------------------- niches
def svc(icon, title, desc, price=None):
    return dict(icon=icon, title=title, desc=desc, price=price)


NICHE = {
    "restaurant": dict(arch="food", emoji="🍽", visual="🍲",
        badge="Restaurant & Takeaway", hl="Freshly Made",
        head="Delicious Food, <span>Freshly Made</span>",
        sub="Dine in, takeaway, or delivered to your door — fresh ingredients, generous portions and a warm welcome in {town}.",
        cta="Book a Table", stag="What We Offer", shead="Something For Everyone",
        ssub="Whether you're eating in, grabbing a takeaway or feeding a crowd, we've got you covered.",
        services=[svc("🍽", "Dine In", "Relaxed, friendly dining in the heart of {town}."),
                  svc("🥡", "Takeaway & Collection", "Order ahead and collect — ready when you are."),
                  svc("🛵", "Local Delivery", "Hot, fresh food delivered across {town}."),
                  svc("🎉", "Events & Catering", "Let us cater your party, function or special occasion."),
                  svc("✨", "Fresh Daily Specials", "New seasonal dishes on the board every week."),
                  svc("🍷", "Fully Licensed", "A great selection of drinks to go with your meal.")]),
    "salon": dict(arch="beauty", emoji="💇", visual="💅",
        badge="Hair & Beauty", hl="Feel Great",
        head="Look Good, <span>Feel Great</span>",
        sub="Expert cuts, colour, nails and beauty treatments in the heart of {town}. Book ahead or walk in — you'll leave feeling your best.",
        cta="Book an Appointment", stag="Our Services", shead="Treatments & Pricing",
        ssub="A full range of hair and beauty treatments, all at honest, up-front prices.",
        services=[svc("✂️", "Cut & Blow-Dry", "A fresh, flattering style tailored to you.", "from £28"),
                  svc("🎨", "Colour & Highlights", "Balayage, highlights and full colour by experts.", "from £55"),
                  svc("💅", "Manicure & Pedicure", "Gel, acrylic and classic nails that last.", "from £25"),
                  svc("🌿", "Facials & Skincare", "Relaxing, results-driven facial treatments.", "from £40"),
                  svc("🌸", "Waxing & Threading", "Quick, gentle and precise — every time.", "from £12"),
                  svc("👰", "Bridal & Occasion", "Look unforgettable for your big day.", "from £75")]),
    "dentist": dict(arch="clinic", emoji="🦷", visual="🦷",
        badge="Dental Practice", hl="Confident",
        head="A Healthy, <span>Confident</span> Smile",
        sub="Gentle, modern dental care for all the family in {town}. From routine check-ups to cosmetic treatments — new patients always welcome.",
        cta="Book a Check-Up", stag="Treatments", shead="Complete Dental Care",
        ssub="Everything you need to keep your smile healthy, comfortable and looking its best.",
        services=[svc("🪥", "Check-Ups & Hygiene", "Routine exams and professional cleaning.", "from £45"),
                  svc("✨", "Cosmetic Dentistry", "Veneers and bonding for a smile you'll love."),
                  svc("😁", "Teeth Whitening", "Safe, professional whitening that really works.", "from £199"),
                  svc("😬", "Invisalign & Braces", "Discreet, modern teeth straightening."),
                  svc("🚑", "Emergency Appointments", "In pain? We'll see you the same day.", "Same day"),
                  svc("🦷", "Implants & Crowns", "Natural-looking, long-lasting restorations.")]),
    "vet": dict(arch="clinic", emoji="🐾", visual="🐾",
        badge="Veterinary Surgery", hl="Like Family",
        head="Caring For Your Pets <span>Like Family</span>",
        sub="Compassionate veterinary care in {town} — from routine vaccinations to surgery and emergencies. Your pet's health is our priority.",
        cta="Book an Appointment", stag="Our Services", shead="Complete Pet Care",
        ssub="Friendly, expert care for every stage of your pet's life.",
        services=[svc("💉", "Vaccinations & Check-Ups", "Keep your pet healthy and protected."),
                  svc("🏥", "Neutering & Surgery", "Safe procedures in modern facilities."),
                  svc("🦷", "Dental Care", "Cleaning and treatment for healthy teeth."),
                  svc("🚑", "Emergency Care", "Urgent help when your pet needs it most.", "Urgent"),
                  svc("🔍", "Microchipping", "Quick, permanent peace of mind.", "from £15"),
                  svc("❤️", "Pet Health Plans", "Spread the cost of routine care.")]),
    "plumber": dict(arch="trades", emoji="🔧", visual="🔧",
        badge="Plumbing & Heating", hl="Done Right",
        head="Reliable Plumbing, <span>Done Right</span>",
        sub="Local, Gas Safe plumbing and heating across {town}. Leaks, boilers, bathrooms and emergency call-outs — fair prices, no surprises.",
        cta="Get a Free Quote", stag="What We Do", shead="Plumbing & Heating Services",
        ssub="From a dripping tap to a full bathroom, no job is too big or too small.",
        services=[svc("💧", "Leaks & Repairs", "Fast fixes for leaks, taps and pipework."),
                  svc("🔥", "Boiler Service & Repair", "Keep your heating safe and efficient."),
                  svc("🛁", "Bathroom Installation", "Full design and fit, start to finish."),
                  svc("♨️", "Central Heating", "Radiators, pumps and full heating systems."),
                  svc("🚨", "Emergency Call-Outs", "Burst pipe? We're on our way.", "24/7"),
                  svc("🌀", "Power Flushing", "Clear sludge and restore your heating.")]),
    "electrician": dict(arch="trades", emoji="⚡", visual="⚡",
        badge="Electrical Services", hl="Certified",
        head="Safe, Certified <span>Electrics</span>",
        sub="Certified electrical work across {town}. Rewires, fuse boards, sockets, lighting and EV chargers — fully tested, fairly priced.",
        cta="Get a Free Quote", stag="What We Do", shead="Electrical Services",
        ssub="Qualified, certified electrical work for homes and businesses.",
        services=[svc("🔌", "Rewiring", "Full or partial rewires, done safely."),
                  svc("⚡", "Fuse Boards", "Consumer unit upgrades and replacements."),
                  svc("💡", "Sockets & Lighting", "Extra sockets, indoor and outdoor lighting."),
                  svc("🔋", "EV Charger Install", "Home charge points, professionally fitted."),
                  svc("🔍", "Fault Finding", "We track down and fix the problem fast."),
                  svc("📋", "Certificates", "EICR and electrical safety certificates.")]),
    "roofer": dict(arch="trades", emoji="🏠", visual="🏠",
        badge="Roofing Specialists", hl="That Last",
        head="Roofs <span>That Last</span>",
        sub="Trusted roofing across {town} — repairs, new roofs, flat roofs and guttering. Free inspections and honest, no-pressure quotes.",
        cta="Get a Free Quote", stag="What We Do", shead="Roofing Services",
        ssub="Repairs, replacements and everything in between — built to last.",
        services=[svc("🔨", "Roof Repairs", "Leaks, slipped tiles and storm damage."),
                  svc("🏠", "New Roofs", "Full re-roofing with quality materials."),
                  svc("📐", "Flat Roofing", "Durable, watertight flat roof systems."),
                  svc("🌧️", "Guttering & Fascias", "Keep water where it belongs."),
                  svc("🧱", "Chimney Work", "Repointing, repairs and removals."),
                  svc("🚨", "Emergency Repairs", "Fast response to urgent leaks.", "24/7")]),
    "gym": dict(arch="fitness", emoji="💪", visual="🏋",
        badge="Gym & Fitness", hl="Every Day",
        head="Stronger, <span>Every Day</span>",
        sub="A friendly, fully-equipped gym in {town}. Classes, personal training and flexible memberships — for every level, with no judgement.",
        cta="Start a Free Trial", stag="What's Inside", shead="Everything You Need",
        ssub="Top kit, great classes and real coaching — all under one roof.",
        services=[svc("🏋", "Free Weights & Machines", "A full strength and cardio floor."),
                  svc("🤸", "Group Classes", "Spin, HIIT, yoga and more, every day."),
                  svc("💪", "Personal Training", "1-on-1 coaching towards your goals."),
                  svc("🔥", "Functional Zone", "Rigs, sleds and space to move."),
                  svc("🚿", "Sauna & Showers", "Recover and refresh after training."),
                  svc("📅", "Flexible Memberships", "No contracts, no tie-ins.", "from £25/mo")]),
    "accountant": dict(arch="professional", emoji="📊", visual="📊",
        badge="Accountancy", hl="Simple",
        head="Accounting Made <span>Simple</span>",
        sub="Straightforward accountancy for small businesses and the self-employed in {town}. Tax, bookkeeping and payroll — clear advice, fixed fees.",
        cta="Book a Free Consultation", stag="Our Services", shead="How We Help",
        ssub="Everything you need to stay compliant and in control of your numbers.",
        services=[svc("🧾", "Self-Assessment", "Stress-free personal tax returns."),
                  svc("📊", "Annual Accounts", "Accurate accounts, filed on time."),
                  svc("📚", "Bookkeeping", "Keep your records tidy and up to date."),
                  svc("💷", "Payroll", "Pay your team accurately, every time."),
                  svc("📋", "VAT Returns", "Hassle-free, MTD-compliant VAT."),
                  svc("💡", "Business Advice", "Practical guidance to help you grow.")]),
}

REVIEWS = {  # (text, name, town-offset) — first review localised to the lead's town
    "food": [("Best meal we've had locally in ages — fresh, tasty and great value. We'll be back!", "James W."),
             ("Ordered a takeaway on Friday, arrived hot and the portions were huge. Lovely staff too.", "Aisha R."),
             ("They catered our office party and it was flawless from start to finish. Highly recommend.", "Tom C.")],
    "beauty": [("Absolutely love my new colour — they really listened to what I wanted. Felt so relaxed.", "Sophie H."),
               ("Best nails I've had in years and the salon is gorgeous. Booking again already!", "Megan T."),
               ("Did my hair and makeup for my wedding — I felt incredible. Thank you so much.", "Hannah L.")],
    "clinic": [("Nervous patient here — they put me completely at ease. Gentle, kind and professional.", "David M."),
               ("Got an emergency appointment the same day. Sorted quickly and explained everything clearly.", "Priya S."),
               ("The whole family goes here now. Friendly team and never a long wait. Brilliant.", "Karen B.")],
    "trades": [("Turned up on time, fair price, tidy work. Exactly what you want from a local trade.", "Mark K."),
               ("Called in a panic and they came straight out. Sorted it fast and didn't overcharge. Lifesavers.", "Lisa P."),
               ("Quoted upfront and stuck to it. Honest, reliable and a quality job. Highly recommend.", "Steve R.")],
    "fitness": [("Friendliest gym I've ever joined — zero ego and the trainers genuinely care. Love it.", "Ryan F."),
                ("Classes are brilliant and there's never a wait for kit. Best decision I've made all year.", "Chloe D."),
                ("Down two stone with their PT support. Welcoming place that actually keeps you going.", "Daniel O.")],
    "professional": [("Took all the stress out of my tax return and saved me money. Clear, no jargon, brilliant.", "Rachel N."),
                     ("Switched to them last year — proactive, responsive and genuinely helpful. Wish I'd done it sooner.", "Paul G."),
                     ("Fixed fees, real advice and they actually pick up the phone. Exactly what a small business needs.", "Emma V.")],
}
NEARBY = ["High Wycombe", "Marlow", "Beaconsfield", "Amersham"]


def tel(phone):
    digits = "".join(c for c in (phone or "") if c.isdigit() or c == "+")
    return digits or ""


def render(biz):
    name, niche, town = biz["name"], biz["niche"], biz["town"]
    n = NICHE.get(niche, NICHE["restaurant"])
    a = ARCH[n["arch"]]
    phone = biz.get("phone") or ""
    href = f"tel:{tel(phone)}" if phone else "#contact"
    fmt = lambda s: s.format(town=town)

    # logo: highlight last word
    parts = name.split()
    logo = (" ".join(parts[:-1]) + f' <span>{parts[-1]}</span>') if len(parts) > 1 else f'<span>{name}</span>'

    stats = "".join(f'<div class="stat"><div class="num">{n_}</div><div class="lab">{l}</div></div>'
                    for n_, l in a["stats"])
    services = "".join(
        f'<div class="card"><div class="ico">{s["icon"]}</div>'
        f'<h3>{fmt(s["title"])}</h3><p>{fmt(s["desc"])}</p>'
        + (f'<div class="price">{s["price"]}</div>' if s["price"] else "")
        + "</div>" for s in n["services"])
    why = "".join(f'<li class="why"><div class="chk">✓</div><div><h4>{h}</h4><p>{p}</p></div></li>'
                  for h, p in a["why"])
    rev_towns = [town] + [t for t in NEARBY if t != town]
    reviews = "".join(
        f'<div class="rev"><div class="stars">★★★★★</div><p>"{txt}"</p>'
        f'<div class="auth"><div class="ava">{nm.split()[0][0]}{nm.split()[-1][0]}</div>'
        f'<div><div class="an">{nm}</div><div class="al">{rev_towns[i % len(rev_towns)]}</div></div></div></div>'
        for i, (txt, nm) in enumerate(REVIEWS[n["arch"]]))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{name} — {fmt(n['badge'])} in {town}. {fmt(n['sub'])}">
<title>{name} | {fmt(n['badge'])} in {town}</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:{a['text']};line-height:1.6;background:#fff}}
:root{{--p:{a['primary']};--pd:{a['dark']};--a:{a['accent']};--a2:{a['accent2']};--g:{a['grey']};--bd:{a['border']};--cr:{a['cream']}}}
a{{text-decoration:none}}
nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(15,15,20,.55);backdrop-filter:blur(10px);display:flex;align-items:center;justify-content:space-between;padding:0 5%;height:66px;transition:background .3s}}
nav.solid{{background:var(--pd)}}
.logo{{color:#fff;font-size:21px;font-weight:800;letter-spacing:-.3px}}
.logo span{{color:var(--a)}}
.nlinks{{display:flex;gap:30px;list-style:none}}
.nlinks a{{color:rgba(255,255,255,.82);font-size:15px;font-weight:500;transition:color .2s}}
.nlinks a:hover{{color:var(--a)}}
.ncta{{background:var(--a);color:#11151c;padding:10px 22px;border-radius:8px;font-weight:700;font-size:14px;transition:transform .15s,filter .2s}}
.ncta:hover{{transform:translateY(-1px);filter:brightness(1.07)}}
.hero{{min-height:100vh;display:flex;align-items:center;padding:120px 5% 70px;background:linear-gradient(135deg,{a['hero'].split(',')[0]} 0%,{a['hero'].split(',')[1]} 50%,{a['hero'].split(',')[2]} 100%);position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;top:-180px;right:-160px;width:560px;height:560px;background:radial-gradient(circle,{a['accent']}22 0%,transparent 65%);pointer-events:none}}
.hwrap{{position:relative;max-width:660px}}
.badge{{display:inline-flex;align-items:center;gap:8px;background:{a['accent']}1f;border:1px solid {a['accent']}55;color:var(--a2);padding:7px 16px;border-radius:30px;font-size:13px;font-weight:600;margin-bottom:26px}}
.hero h1{{font-size:clamp(36px,6vw,66px);font-weight:900;color:#fff;line-height:1.08;letter-spacing:-1.5px;margin-bottom:22px}}
.hero h1 span{{color:var(--a)}}
.hero p{{font-size:19px;color:rgba(255,255,255,.74);max-width:540px;margin-bottom:36px}}
.btns{{display:flex;gap:14px;flex-wrap:wrap}}
.bp{{background:var(--a);color:#11151c;padding:15px 32px;border-radius:10px;font-weight:800;font-size:16px;transition:transform .15s,filter .2s}}
.bp:hover{{transform:translateY(-2px);filter:brightness(1.07)}}
.bs{{background:rgba(255,255,255,.1);color:#fff;padding:15px 30px;border-radius:10px;font-weight:600;font-size:16px;border:1px solid rgba(255,255,255,.25)}}
.bs:hover{{background:rgba(255,255,255,.18)}}
.statbar{{background:var(--p);display:flex;justify-content:center;gap:clamp(28px,7vw,80px);flex-wrap:wrap;padding:26px 5%}}
.stat{{text-align:center;color:#fff}}
.stat .num{{font-size:26px;font-weight:900;color:var(--a2)}}
.stat .lab{{font-size:13px;color:rgba(255,255,255,.7);letter-spacing:.5px}}
section{{padding:86px 5%}}
.tag{{font-size:12px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:var(--a);margin-bottom:12px}}
h2{{font-size:clamp(28px,4vw,44px);font-weight:900;color:var(--p);line-height:1.15;letter-spacing:-.5px;margin-bottom:14px}}
.sub{{font-size:18px;color:var(--g);max-width:580px;margin-bottom:50px}}
.cream{{background:var(--cr)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:22px}}
.card{{background:#fff;border:1px solid var(--bd);border-radius:14px;padding:28px;transition:transform .2s,box-shadow .2s;position:relative}}
.card:hover{{transform:translateY(-5px);box-shadow:0 16px 38px rgba(0,0,0,.09)}}
.ico{{font-size:36px;margin-bottom:14px}}
.card h3{{font-size:19px;font-weight:800;color:var(--text);margin-bottom:8px}}
.card p{{font-size:15px;color:var(--g)}}
.price{{margin-top:14px;display:inline-block;background:var(--cr);color:var(--p);font-weight:800;font-size:14px;padding:5px 14px;border-radius:20px}}
.why-wrap{{display:grid;grid-template-columns:1.1fr .9fr;gap:60px;align-items:center}}
.whys{{list-style:none;display:flex;flex-direction:column;gap:22px;margin-top:8px}}
.why{{display:flex;gap:16px}}
.chk{{flex-shrink:0;width:30px;height:30px;border-radius:50%;background:var(--a);color:#11151c;display:flex;align-items:center;justify-content:center;font-weight:900}}
.why h4{{font-size:17px;font-weight:800;color:var(--text);margin-bottom:3px}}
.why p{{font-size:15px;color:var(--g)}}
.visual{{background:linear-gradient(135deg,var(--p),var(--pd));border-radius:20px;min-height:380px;display:flex;align-items:center;justify-content:center;font-size:130px}}
.revs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:22px}}
.rev{{background:#fff;border:1px solid var(--bd);border-radius:14px;padding:28px}}
.stars{{color:var(--a);font-size:18px;margin-bottom:12px}}
.rev p{{font-size:15px;color:#374151;font-style:italic;margin-bottom:18px}}
.auth{{display:flex;align-items:center;gap:12px}}
.ava{{width:42px;height:42px;border-radius:50%;background:var(--p);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px}}
.an{{font-weight:700;font-size:14px;color:var(--text)}}
.al{{font-size:12px;color:var(--g)}}
.contact-wrap{{display:grid;grid-template-columns:1fr 1fr;gap:60px}}
.cinfo{{display:flex;flex-direction:column;gap:18px;margin-top:10px}}
.crow{{display:flex;gap:16px;align-items:flex-start;background:var(--cr);border:1px solid var(--bd);border-radius:12px;padding:18px 20px}}
.crow .ci{{font-size:22px}}
.cl{{font-size:12px;letter-spacing:1px;text-transform:uppercase;color:var(--g);margin-bottom:3px}}
.cv{{font-size:17px;font-weight:800;color:var(--text)}}
form{{display:flex;flex-direction:column;gap:14px;background:var(--cr);border:1px solid var(--bd);border-radius:16px;padding:30px}}
input,textarea{{padding:13px 16px;border:1px solid var(--bd);border-radius:9px;font-size:15px;font-family:inherit;background:#fff}}
input:focus,textarea:focus{{outline:2px solid var(--a)}}
.fsub{{background:var(--p);color:#fff;border:none;padding:15px;border-radius:9px;font-weight:800;font-size:16px;cursor:pointer}}
.fsub:hover{{background:var(--pd)}}
footer{{background:var(--pd);color:rgba(255,255,255,.6);padding:40px 5% 70px;text-align:center}}
footer .fn{{color:#fff;font-size:20px;font-weight:800;margin-bottom:8px}}
footer .fn span{{color:var(--a)}}
.concept{{margin-top:22px;font-size:12.5px;color:rgba(255,255,255,.45);max-width:620px;margin-left:auto;margin-right:auto;line-height:1.6}}
.flag{{position:fixed;right:16px;bottom:16px;z-index:200;background:#0f172a;color:#fff;font-size:12.5px;font-weight:600;padding:9px 15px;border-radius:30px;box-shadow:0 8px 26px rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.12)}}
.flag span{{color:#7dd3fc}}
.flag b{{color:var(--a)}}
/* animation + polish */
@keyframes mkUp{{from{{opacity:0;transform:translateY(26px)}}to{{opacity:1;transform:none}}}}
@keyframes mkGlow{{0%,100%{{transform:translate(0,0) scale(1)}}50%{{transform:translate(-45px,35px) scale(1.18)}}}}
@keyframes mkShine{{0%,55%{{left:-130%}}80%,100%{{left:140%}}}}
.hero .badge{{animation:mkUp .6s .05s both cubic-bezier(.2,.7,.2,1)}}
.hero h1{{animation:mkUp .7s .16s both cubic-bezier(.2,.7,.2,1)}}
.hero p{{animation:mkUp .7s .3s both cubic-bezier(.2,.7,.2,1)}}
.hero .btns{{animation:mkUp .7s .42s both cubic-bezier(.2,.7,.2,1)}}
.hero::after{{content:'';position:absolute;left:-120px;bottom:-170px;width:430px;height:430px;border-radius:50%;background:radial-gradient(circle,var(--a) 0%,transparent 60%);opacity:.16;pointer-events:none;animation:mkGlow 17s ease-in-out infinite}}
.bp{{position:relative;overflow:hidden}}
.bp::after{{content:'';position:absolute;top:0;left:-130%;width:55%;height:100%;background:linear-gradient(120deg,transparent,rgba(255,255,255,.55),transparent);transform:skewX(-20deg);animation:mkShine 4.8s ease-in-out infinite}}
.reveal{{opacity:0;transform:translateY(28px);transition:opacity .7s cubic-bezier(.2,.7,.2,1),transform .7s cubic-bezier(.2,.7,.2,1)}}
.reveal.in{{opacity:1;transform:none}}
.grid .card,.revs .rev{{opacity:0;transform:translateY(26px);transition:opacity .6s cubic-bezier(.2,.7,.2,1),transform .6s cubic-bezier(.2,.7,.2,1)}}
.grid.in .card,.revs.in .rev{{opacity:1;transform:none}}
.grid.in .card:nth-child(2),.revs.in .rev:nth-child(2){{transition-delay:.08s}}
.grid.in .card:nth-child(3),.revs.in .rev:nth-child(3){{transition-delay:.16s}}
.grid.in .card:nth-child(4){{transition-delay:.24s}}
.grid.in .card:nth-child(5){{transition-delay:.32s}}
.grid.in .card:nth-child(6){{transition-delay:.4s}}
.statbar .stat{{opacity:0;transform:translateY(16px);transition:opacity .6s,transform .6s}}
.statbar.in .stat{{opacity:1;transform:none}}
.statbar.in .stat:nth-child(2){{transition-delay:.1s}}
.statbar.in .stat:nth-child(3){{transition-delay:.2s}}
.statbar.in .stat:nth-child(4){{transition-delay:.3s}}
.card .ico{{transition:transform .3s}}
.card:hover .ico{{transform:scale(1.15) rotate(-5deg)}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}.reveal,.grid .card,.revs .rev,.statbar .stat,.hero .badge,.hero h1,.hero p,.hero .btns{{opacity:1!important;transform:none!important}}}}
@media(max-width:820px){{.nlinks{{display:none}}.why-wrap,.contact-wrap{{grid-template-columns:1fr}}.visual{{min-height:220px;font-size:90px}}}}
</style>
</head>
<body>
<nav id="nav">
  <div class="logo">{logo}</div>
  <ul class="nlinks">
    <li><a href="#services">{n['stag']}</a></li>
    <li><a href="#about">About</a></li>
    <li><a href="#reviews">Reviews</a></li>
    <li><a href="#contact">Contact</a></li>
  </ul>
  <a href="{href}" class="ncta">{('📞 ' + phone) if phone else n['cta']}</a>
</nav>

<section class="hero">
  <div class="hwrap">
    <div class="badge">{n['emoji']} {fmt(n['badge'])} · {town}</div>
    <h1>{fmt(n['head'])}</h1>
    <p>{fmt(n['sub'])}</p>
    <div class="btns">
      <a href="{href}" class="bp">{n['cta']} →</a>
      <a href="#services" class="bs">See More</a>
    </div>
  </div>
</section>

<div class="statbar">{stats}</div>

<section id="services">
  <div class="reveal">
    <div class="tag">{n['stag']}</div>
    <h2>{fmt(n['shead'])}</h2>
    <p class="sub">{fmt(n['ssub'])}</p>
  </div>
  <div class="grid">{services}</div>
</section>

<section id="about" class="cream">
  <div class="why-wrap">
    <div class="reveal">
      <div class="tag">Why {name}</div>
      <h2>Why Locals Choose Us</h2>
      <p class="sub">We're proud to serve {town} and the surrounding area — and we work hard to keep it that way.</p>
      <ul class="whys">{why}</ul>
    </div>
    <div class="visual reveal">{n['visual']}</div>
  </div>
</section>

<section id="reviews">
  <div class="reveal">
    <div class="tag">Reviews</div>
    <h2>What People Say</h2>
    <p class="sub">Real words from happy customers across {town} and beyond.</p>
  </div>
  <div class="revs">{reviews}</div>
</section>

<section id="contact" class="cream">
  <div class="contact-wrap">
    <div class="reveal">
      <div class="tag">Get In Touch</div>
      <h2>{n['cta']}</h2>
      <p class="sub">We'd love to hear from you. Call us or drop a message and we'll get straight back to you.</p>
      <div class="cinfo">
        <div class="crow"><div class="ci">📞</div><div><div class="cl">Phone</div><div class="cv">{phone or 'Add your number'}</div></div></div>
        <div class="crow"><div class="ci">📍</div><div><div class="cl">Area</div><div class="cv">{town} & surrounding areas</div></div></div>
        <div class="crow"><div class="ci">🕒</div><div><div class="cl">Hours</div><div class="cv">Open 6 days a week</div></div></div>
      </div>
    </div>
    <form class="reveal" onsubmit="return false">
      <input type="text" placeholder="Your name" aria-label="Your name">
      <input type="tel" placeholder="Phone number" aria-label="Phone number">
      <input type="email" placeholder="Email address" aria-label="Email address">
      <textarea rows="4" placeholder="How can we help?" aria-label="Message"></textarea>
      <button class="fsub" type="submit">Send Message →</button>
    </form>
  </div>
</section>

<footer>
  <div class="fn">{logo}</div>
  <div>{fmt(n['badge'])} · {town}{(' · ' + phone) if phone else ''}</div>
  <p class="concept">This is a free design concept created by <b>HW Web Design</b> to show {name}
    what a modern website could look like. Sample text, prices and reviews are for illustration only.
    Like it? Let's make it real — hwwebdesign.co.uk</p>
</footer>

<a class="flag" href="{BASE_URL}" target="_blank" rel="noopener">✦ Concept by <b>HW Web Design</b> — <span>let's build yours</span></a>
<script>
addEventListener('scroll',function(){{document.getElementById('nav').classList.toggle('solid',scrollY>30)}},{{passive:true}});
var mio=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{e.target.classList.add('in');mio.unobserve(e.target)}}}})}},{{threshold:.14}});
document.querySelectorAll('.reveal,.grid,.revs,.statbar').forEach(function(el){{mio.observe(el)}});
</script>
</body>
</html>
"""


def select(csv_path):
    rows = []
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            r["score"] = int(r.get("score") or 0)
            r["phone"] = (r.get("phone") or "").strip()
            r["nosite"] = "no website at all" in r.get("flaws", "")
            r["verified"] = r.get("verified_flaw") == "yes"
            rows.append(r)
    hot = [r for r in rows if r["nosite"] and r["phone"]]
    warm = [r for r in rows if r["verified"] and not r["nosite"] and r["phone"]]
    hot.sort(key=lambda r: (r["town"], r["name"]))
    warm.sort(key=lambda r: -r["score"])
    return hot + warm[:WARM_LIMIT]


def gallery(items):
    cards = "".join(
        f'<a class="g" href="./{lead_slug(b["name"], b["town"])}/" target="_blank">'
        f'<div class="gt">{NICHE.get(b["niche"], {}).get("emoji", "🌐")}</div>'
        f'<div class="gb"><div class="gn">{b["name"]}</div>'
        f'<div class="gm">{b["niche"]} · {b["town"]}</div></div></a>'
        for b in items)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HW Web Design — Live Mockups</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f8fafc;color:#0f172a}}
header{{background:linear-gradient(135deg,#1e293b,#2563eb);color:#fff;padding:60px 6% 50px}}
header h1{{font-size:clamp(28px,4vw,42px);font-weight:900;letter-spacing:-1px}}
header p{{color:rgba(255,255,255,.8);margin-top:10px;font-size:17px;max-width:640px}}
.wrap{{max-width:1100px;margin:0 auto;padding:50px 6% 80px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px}}
.g{{background:#fff;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;text-decoration:none;color:inherit;transition:transform .2s,box-shadow .2s}}
.g:hover{{transform:translateY(-5px);box-shadow:0 16px 38px rgba(0,0,0,.1)}}
.gt{{height:130px;background:linear-gradient(135deg,#1e293b,#334155);display:flex;align-items:center;justify-content:center;font-size:60px}}
.gb{{padding:18px}}.gn{{font-weight:800;font-size:16px}}.gm{{color:#64748b;font-size:13px;text-transform:capitalize;margin-top:3px}}
</style></head><body>
<header><h1>Live Website Mockups</h1>
<p>Free design concepts built by HW Web Design for local businesses. Click any card to view the full mockup.</p></header>
<div class="wrap"><div class="grid">{cards}</div></div></body></html>"""


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "leads/leads_high_wycombe_area.csv"
    items = select(csv_path)
    os.makedirs("mockups", exist_ok=True)
    for b in items:
        slug = lead_slug(b["name"], b["town"])
        d = os.path.join("mockups", slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w") as f:
            f.write(render(b))
    with open("mockups/index.html", "w") as f:
        f.write(gallery(items))
    print(f"Generated {len(items)} mockups -> mockups/  (gallery: mockups/index.html)")
    for b in items[:5]:
        print(f"  · {BASE_URL}/mockups/{lead_slug(b['name'], b['town'])}/  ({b['name']})")


if __name__ == "__main__":
    main()
