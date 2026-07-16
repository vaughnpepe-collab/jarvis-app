#!/usr/bin/env python3
"""
HW Web Design — Free Mockup Generator (premium engine).

Reads the leads CSV and builds a cinematic, personalised single-page website
mockup for each top callable lead (business name, town and phone baked in),
plus a gallery index. These are your closing tool: "I built you a sample —
have a look." They deploy with the repo, so each lead's mockup is live at
  https://hwwebdesign.co.uk/mockups/<slug>/
once pushed to main.

The presentation layer matches the standard of hwwebdesign.co.uk and the
/demos/ showcases: glass nav + mobile menu, staggered line-mask hero reveal,
atmosphere layers (glow + grain), services marquee, 3D-tilt cards with cursor
glow, count-up stats, magnetic CTAs, scroll reveals, reduced-motion fallbacks.
Every business still gets a deterministic variant (type, shape, hero, order)
so no two mockups feel template-stamped.

Usage:
    python mockup_gen.py                      # uses the default area CSV
    python mockup_gen.py leads/leads_x.csv    # any sweep CSV

Sample content (reviews, prices, stats) is illustrative and clearly labelled
as a design concept on every page.
"""
import csv
import hashlib
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
    "cafe": dict(arch="food", emoji="☕", visual="🥐",
        badge="Café & Coffee House", hl="Worth Stopping For",
        head="Coffee & Food <span>Worth Stopping For</span>",
        sub="Proper coffee, fresh food and a friendly welcome in the heart of {town} — eat in or takeaway.",
        cta="See Our Menu", stag="What We Serve", shead="Fresh All Day",
        ssub="From your morning flat white to a proper lunch — made fresh, every day.",
        services=[svc("☕", "Specialty Coffee", "Locally roasted beans, expertly made."),
                  svc("🥐", "Breakfast & Brunch", "Served fresh every morning."),
                  svc("🥪", "Lunches & Light Bites", "Sandwiches, salads and daily specials."),
                  svc("🍰", "Homemade Cakes", "Baked in-house — perfect with a cuppa."),
                  svc("🥡", "Takeaway & Collection", "Grab it to go — ready when you are."),
                  svc("🎉", "Private Hire & Catering", "Let us host or cater your next get-together.")]),
    "garage": dict(arch="trades", emoji="🔧", visual="🚗",
        badge="Garage & MOT Centre", hl="You Can Trust",
        head="Car Care <span>You Can Trust</span>",
        sub="MOTs, servicing and repairs in {town} — honest prices, straight answers and work done right the first time.",
        cta="Book Your MOT", stag="Our Services", shead="Everything Your Car Needs",
        ssub="From MOTs to major repairs — all makes and models, all under one roof.",
        services=[svc("📋", "MOT Testing", "Fast turnaround, fair retest policy.", "from £45"),
                  svc("🔧", "Servicing", "Interim and full services to schedule.", "from £99"),
                  svc("🛞", "Tyres & Tracking", "Supplied, fitted and balanced while you wait."),
                  svc("🔋", "Batteries & Electrics", "Diagnostics, batteries and auto-electrics."),
                  svc("🛑", "Brakes & Clutches", "Pads, discs and clutch replacement."),
                  svc("❄️", "Air-Con Service", "Regas and repair to keep you cool.")]),
    "estate agent": dict(arch="professional", emoji="🏡", visual="🔑",
        badge="Estate Agents", hl="Moving Made Simple",
        head="Selling & Letting, <span>Made Simple</span>",
        sub="Local property experts in {town} — honest valuations, beautiful marketing and a team that actually keeps you updated.",
        cta="Book a Free Valuation", stag="Our Services", shead="With You At Every Step",
        ssub="Whether you're selling, letting or searching, you'll always know where you stand.",
        services=[svc("🏷", "Free Valuations", "Accurate, no-obligation market appraisals."),
                  svc("🏠", "Residential Sales", "Standout marketing and negotiation."),
                  svc("🔑", "Lettings & Management", "Full management for stress-free landlords."),
                  svc("📸", "Premium Marketing", "Pro photography and floorplans as standard."),
                  svc("📈", "Investment Advice", "Buy-to-let guidance from local experts."),
                  svc("🤝", "Sales Progression", "A named contact from offer to completion.")]),
    "optician": dict(arch="clinic", emoji="👓", visual="👓",
        badge="Opticians", hl="See Clearly",
        head="Eye Care That Helps You <span>See Clearly</span>",
        sub="Friendly, thorough eye care in {town} — advanced eye exams, designer frames and honest advice for all the family.",
        cta="Book an Eye Test", stag="Our Services", shead="Complete Eye Care",
        ssub="From routine eye tests to contact lenses and everything in between.",
        services=[svc("👁", "Eye Examinations", "Thorough tests with the latest equipment.", "from £25"),
                  svc("🕶", "Designer Frames", "Hand-picked ranges for every budget."),
                  svc("🔍", "Contact Lenses", "Trials, fittings and easy repeat orders."),
                  svc("👶", "Children's Eye Care", "Gentle, NHS-covered kids' eye tests."),
                  svc("💻", "Screen-Strain Advice", "Lenses tuned for modern screen life."),
                  svc("🏠", "Home Visits", "Eye care for those who can't get to us.")]),
    "bakery": dict(arch="food", emoji="🥖", visual="🍞",
        badge="Bakery", hl="Baked Fresh Daily",
        head="Real Bread, <span>Baked Fresh Daily</span>",
        sub="Artisan bread, cakes and pastries baked every morning in {town} — made properly, from scratch.",
        cta="Order Ahead", stag="Fresh From The Oven", shead="Baked Every Morning",
        ssub="From sourdough to celebration cakes — everything made by hand, from scratch.",
        services=[svc("🍞", "Artisan Bread", "Sourdough, bloomers and classics daily."),
                  svc("🥐", "Pastries", "Croissants and pastries, baked at dawn."),
                  svc("🎂", "Celebration Cakes", "Made-to-order cakes for every occasion.", "from £35"),
                  svc("🥪", "Fresh Sandwiches", "Made on our own bread, every lunchtime."),
                  svc("☕", "Coffee To Go", "Proper coffee with your morning loaf."),
                  svc("🏪", "Wholesale", "Supplying local cafés and restaurants.")]),
}

REVIEWS = {  # (text, name) — first review localised to the lead's town
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

# ---------------------------------------------------------------- variants
# Each business gets a deterministic-but-unique combination so no two mockups
# feel template-stamped: typography, shape language, hero treatment, card
# style, section order and visual side all vary by a hash of the name.
V_HFONT = ["Georgia,'Times New Roman',serif",
           "'Segoe UI',system-ui,-apple-system,sans-serif",
           "'Trebuchet MS','Segoe UI',sans-serif",
           "'Palatino Linotype','Book Antiqua',Georgia,serif",
           "Verdana,Geneva,sans-serif"]
V_BFONT = ["'Segoe UI',system-ui,-apple-system,sans-serif",
           "Georgia,serif",
           "'Trebuchet MS',Verdana,sans-serif"]
V_RAD = ["4px", "12px", "18px", "26px"]
V_HALIGN = ["left", "center"]
V_HBG = ["grad", "mesh", "spot", "duo"]
V_CARD = ["elevated", "bordered", "tinted"]
V_ORDER = [("services", "about", "reviews"),
           ("about", "services", "reviews"),
           ("reviews", "services", "about"),
           ("services", "reviews", "about")]
V_VIS = ["right", "left"]


def _pick(seed, opts, salt):
    h = int(hashlib.md5((seed + salt).encode()).hexdigest(), 16)
    return opts[h % len(opts)]


def variant(name, town):
    s = name + "|" + town
    return {"hfont": _pick(s, V_HFONT, "hf"), "bfont": _pick(s, V_BFONT, "bf"),
            "rad": _pick(s, V_RAD, "rd"), "halign": _pick(s, V_HALIGN, "ha"),
            "hbg": _pick(s, V_HBG, "hb"), "card": _pick(s, V_CARD, "cd"),
            "order": _pick(s, V_ORDER, "or"), "vis": _pick(s, V_VIS, "vs")}


def build_variant_css(v, a):
    """Plain-CSS overrides (concatenated to avoid f-string brace escaping)."""
    hero = [x.strip() for x in a["hero"].split(",")]
    h0, h1, h2 = hero[0], hero[1], hero[2]
    p, pd, ac, bd, cr = a["primary"], a["dark"], a["accent"], a["border"], a["cream"]
    o = []
    o.append("body{font-family:" + v["bfont"] + "}")
    o.append("h1,h2,h3,h4,.logo,.eyebrow,.num,.price,.brand{font-family:" + v["hfont"] + "}")
    o.append(":root{--r:" + v["rad"] + "}")
    o.append(".mid{display:flex;flex-direction:column}")
    om = {"services": "#services", "about": "#about", "reviews": "#reviews"}
    for i, k in enumerate(v["order"]):
        o.append(om[k] + "{order:" + str(i) + "}")
    if v["halign"] == "center":
        o.append(".hero-grid{grid-template-columns:1fr}")
        o.append(".hero-copy{margin:0 auto;text-align:center;max-width:760px}")
        o.append(".hero .btns,.chips{justify-content:center}")
        o.append(".hero-visual{display:none}")
    if v["hbg"] == "mesh":
        o.append(".hero{background-color:" + h2 + ";background-image:radial-gradient("
                 "rgba(255,255,255,.06) 1px,transparent 1px),linear-gradient(135deg,"
                 + h0 + "," + h1 + "," + h2 + ");background-size:26px 26px,cover}")
    elif v["hbg"] == "spot":
        o.append(".hero{background:radial-gradient(circle at 78% 24%," + ac
                 + "44,transparent 52%),linear-gradient(165deg," + h0 + "," + h2 + ")}")
    elif v["hbg"] == "duo":
        o.append(".hero{background:linear-gradient(115deg," + p + " 0%," + pd
                 + " 55%,#07080e 100%)}")
    if v["card"] == "bordered":
        o.append(".card{box-shadow:none;border:1.5px solid " + bd + "}")
    elif v["card"] == "tinted":
        o.append(".card{background:" + cr + ";border-color:transparent}")
    else:
        o.append(".card{box-shadow:0 14px 34px rgba(2,6,23,.08);border-color:transparent}")
    if v["vis"] == "left":
        o.append(".why-wrap{direction:rtl}.why-wrap>*{direction:ltr}")
        o.append(".hero-grid{direction:rtl}.hero-grid>*{direction:ltr}")
    return "\n".join(o)


def tel(phone):
    digits = "".join(c for c in (phone or "") if c.isdigit() or c == "+")
    return digits or ""


def _count_num(s):
    """Leading integer of a stat like '12mo'/'4.9★' -> (prefixable int, suffix) or None."""
    digits = ""
    for ch in s:
        if ch.isdigit():
            digits += ch
        else:
            break
    if digits and "." not in s[:len(digits) + 1]:
        return digits, s[len(digits):]
    return None


def render(biz):
    name, niche, town = biz["name"], biz["niche"], biz["town"]
    n = NICHE.get(niche, NICHE["restaurant"])
    a = ARCH[n["arch"]]
    v = variant(name, town)
    vcss = build_variant_css(v, a)
    phone = biz.get("phone") or ""
    href = f"tel:{tel(phone)}" if phone else "#contact"
    fmt = lambda s: s.format(town=town)
    hero_cols = a["hero"].split(",")

    parts = name.split()
    logo = (" ".join(parts[:-1]) + f' <span>{parts[-1]}</span>') if len(parts) > 1 else f'<span>{name}</span>'

    # split headline at the accent <span> for the line-mask stagger
    head = fmt(n["head"])
    if "<span>" in head:
        pre, rest = head.split("<span>", 1)
        acc, post = rest.split("</span>", 1)
        lines = []
        if pre.strip():
            lines.append(f'<span class="hl"><span>{pre.strip()}</span></span>')
        lines.append(f'<span class="hl"><span><em>{acc}</em>{post}</span></span>')
        h1 = "".join(lines)
    else:
        h1 = f'<span class="hl"><span>{head}</span></span>'

    stats = ""
    for num, lab in a["stats"]:
        c = _count_num(num)
        if c:
            stats += (f'<div class="stat"><div class="num"><span data-count="{c[0]}">{c[0]}</span>'
                      f'{c[1]}</div><div class="lab">{lab}</div></div>')
        else:
            stats += f'<div class="stat"><div class="num">{num}</div><div class="lab">{lab}</div></div>'

    services = "".join(
        f'<div class="card" data-tilt><div class="ico"><span>{s["icon"]}</span></div>'
        f'<h3>{fmt(s["title"])}</h3><p>{fmt(s["desc"])}</p>'
        + (f'<div class="price">{s["price"]}</div>' if s["price"] else "")
        + "</div>" for s in n["services"])

    mq_items = "".join(f'<span>{fmt(s["title"])}</span><i>✦</i>' for s in n["services"])

    why = "".join(
        '<li class="why"><span class="chk"><svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg></span>'
        f'<div><h4>{h}</h4><p>{p}</p></div></li>' for h, p in a["why"])

    rev_towns = [town] + [t for t in NEARBY if t != town]
    reviews = "".join(
        f'<div class="rev"><div class="stars">★★★★★</div><p>"{txt}"</p>'
        f'<div class="auth"><div class="ava">{nm.split()[0][0]}{nm.split()[-1][0]}</div>'
        f'<div><div class="an">{nm}</div><div class="al">{rev_towns[i % len(rev_towns)]}</div></div></div></div>'
        for i, (txt, nm) in enumerate(REVIEWS[n["arch"]]))
    quote_txt, quote_nm = REVIEWS[n["arch"]][0]

    chips = "".join(f'<span class="chip"><svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>{c}</span>'
                    for c in [f"Trusted in {town}", "Friendly local team", "Fair, honest prices"])

    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{name} — {fmt(n['badge'])} in {town}. {fmt(n['sub'])}">
<meta name="robots" content="noindex">
<title>{name} | {fmt(n['badge'])} in {town}</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
:root{{--p:{a['primary']};--pd:{a['dark']};--a:{a['accent']};--a2:{a['accent2']};--tx:{a['text']};--g:{a['grey']};--bd:{a['border']};--cr:{a['cream']};--r:14px;
--ease:cubic-bezier(.16,1,.3,1)}}
body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:var(--tx);line-height:1.65;background:#fff;overflow-x:hidden;-webkit-font-smoothing:antialiased}}
a{{text-decoration:none;color:inherit}}
h1,h2,h3,h4{{text-wrap:balance}}
:focus-visible{{outline:3px solid var(--a2);outline-offset:3px;border-radius:6px}}
.grain{{position:fixed;inset:-60px;z-index:5;pointer-events:none;opacity:.28;mix-blend-mode:soft-light;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.4'/%3E%3C/svg%3E")}}
.progress{{position:fixed;top:0;left:0;height:2.5px;width:0;z-index:300;background:linear-gradient(90deg,var(--a),var(--a2));box-shadow:0 0 10px var(--a)}}

/* ---------- nav ---------- */
nav{{position:fixed;top:0;left:0;right:0;z-index:200;display:flex;align-items:center;justify-content:space-between;padding:0 5%;height:68px;transition:background .35s,box-shadow .35s,border-color .35s;border-bottom:1px solid transparent;background:rgba(10,12,18,.32);backdrop-filter:blur(14px) saturate(1.3);-webkit-backdrop-filter:blur(14px) saturate(1.3)}}
nav.solid{{background:rgba(10,12,18,.78);border-bottom-color:rgba(255,255,255,.08);box-shadow:0 8px 32px rgba(0,0,0,.25)}}
.logo{{color:#fff;font-size:1.22rem;font-weight:800;letter-spacing:-.01em}}
.logo span{{color:var(--a2)}}
.nlinks{{display:flex;gap:32px;list-style:none}}
.nlinks a{{position:relative;color:rgba(255,255,255,.82);font-size:.92rem;font-weight:600;transition:color .25s}}
.nlinks a::after{{content:'';position:absolute;left:0;bottom:-6px;height:2px;width:0;border-radius:2px;background:var(--a);transition:width .3s var(--ease)}}
.nlinks a:hover{{color:#fff}}
.nlinks a:hover::after{{width:100%}}
.nav-right{{display:flex;align-items:center;gap:10px}}
.ncta{{background:var(--a);color:#11151c;padding:11px 22px;border-radius:calc(var(--r) - 2px);font-weight:800;font-size:.86rem;white-space:nowrap;transition:transform .25s var(--ease),box-shadow .3s,filter .2s;box-shadow:0 10px 26px rgba(0,0,0,.28);will-change:transform}}
.ncta:hover{{transform:translateY(-2px);filter:brightness(1.08)}}
.ntgl{{display:none;flex-direction:column;justify-content:center;align-items:center;gap:5px;width:44px;height:44px;background:transparent;border:0;cursor:pointer}}
.ntgl span{{width:22px;height:2px;border-radius:2px;background:#fff;transition:transform .3s var(--ease),opacity .2s}}
.ntgl.open span:nth-child(1){{transform:translateY(7px) rotate(45deg)}}
.ntgl.open span:nth-child(2){{opacity:0}}
.ntgl.open span:nth-child(3){{transform:translateY(-7px) rotate(-45deg)}}
.mmenu{{position:fixed;top:68px;left:0;right:0;z-index:190;background:rgba(10,12,18,.96);backdrop-filter:blur(14px);display:flex;flex-direction:column;padding:8px 5% 20px;transform:translateY(-140%);transition:transform .38s var(--ease);border-bottom:1px solid rgba(255,255,255,.1)}}
.mmenu.open{{transform:translateY(0)}}
.mmenu a{{color:rgba(255,255,255,.92);font-size:1rem;font-weight:600;padding:14px 4px;border-bottom:1px solid rgba(255,255,255,.08)}}
.mmenu a.mcta{{background:var(--a);color:#11151c;text-align:center;border-radius:var(--r);margin-top:12px;padding:14px;border:0;font-weight:800}}

/* ---------- hero ---------- */
.hero{{position:relative;min-height:100svh;display:flex;align-items:center;padding:128px 5% 120px;background:linear-gradient(135deg,{hero_cols[0]} 0%,{hero_cols[1]} 50%,{hero_cols[2]} 100%);overflow:hidden;isolation:isolate}}
.hero::before{{content:'';position:absolute;z-index:-1;top:-22%;right:-14%;width:min(56vw,640px);aspect-ratio:1;border-radius:50%;background:radial-gradient(circle,{a['accent']}3d 0%,transparent 62%);filter:blur(50px);animation:mkBreathe 11s ease-in-out infinite;pointer-events:none}}
.hero::after{{content:'';position:absolute;z-index:-1;left:-14%;bottom:-26%;width:min(44vw,480px);aspect-ratio:1;border-radius:50%;background:radial-gradient(circle,{a['accent2']}2e 0%,transparent 60%);filter:blur(56px);animation:mkBreathe 13s ease-in-out infinite reverse;pointer-events:none}}
@keyframes mkBreathe{{0%,100%{{transform:scale(1) translate(0,0)}}50%{{transform:scale(1.14) translate(-24px,18px)}}}}
.hero-grid{{position:relative;width:100%;max-width:1180px;margin:0 auto;display:grid;grid-template-columns:1.08fr .92fr;gap:52px;align-items:center}}
.badge{{display:inline-flex;align-items:center;gap:9px;background:rgba(255,255,255,.07);border:1px solid {a['accent']}59;color:var(--a2);padding:8px 17px;border-radius:999px;font-size:.8rem;font-weight:700;letter-spacing:.04em;margin-bottom:26px;backdrop-filter:blur(6px);opacity:0;animation:mkUp .7s var(--ease) .08s forwards}}
.badge .dot{{width:7px;height:7px;border-radius:50%;background:var(--a2);box-shadow:0 0 10px var(--a2);animation:mkPulse 2.3s infinite}}
@keyframes mkPulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
.hero h1{{font-size:clamp(2.3rem, 1.2rem + 5vw, 4.2rem);font-weight:900;color:#fff;line-height:1.05;letter-spacing:-.025em;margin-bottom:22px}}
.hl{{display:block;overflow:hidden}}
.hl>span{{display:block;transform:translateY(112%);animation:mkLine 1s var(--ease) forwards}}
.hl:nth-child(1)>span{{animation-delay:.14s}}
.hl:nth-child(2)>span{{animation-delay:.3s}}
@keyframes mkLine{{to{{transform:translateY(0)}}}}
.hero h1 em{{font-style:normal;background:linear-gradient(92deg,var(--a),var(--a2));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}}
.hero .lead{{font-size:clamp(1.02rem, .96rem + .4vw, 1.2rem);color:rgba(255,255,255,.76);max-width:34em;margin-bottom:30px;opacity:0;animation:mkUp .8s var(--ease) .55s forwards}}
.btns{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:26px;opacity:0;animation:mkUp .8s var(--ease) .7s forwards}}
.bp{{position:relative;display:inline-flex;align-items:center;gap:9px;background:var(--a);color:#11151c;padding:16px 32px;border-radius:var(--r);font-weight:800;font-size:1rem;overflow:hidden;transition:transform .3s var(--ease),box-shadow .3s,filter .2s;box-shadow:0 14px 36px rgba(0,0,0,.32);will-change:transform}}
.bp:hover{{filter:brightness(1.07);box-shadow:0 20px 48px rgba(0,0,0,.4)}}
.bp::after{{content:'';position:absolute;inset:0;background:linear-gradient(115deg,transparent 42%,rgba(255,255,255,.5) 50%,transparent 58%);background-size:240% 100%;background-position:140% 0;animation:mkSheen 5.2s var(--ease) infinite;pointer-events:none}}
@keyframes mkSheen{{0%,58%{{background-position:140% 0}}86%,100%{{background-position:-60% 0}}}}
.bs{{display:inline-flex;align-items:center;background:rgba(255,255,255,.07);color:#fff;padding:16px 30px;border-radius:var(--r);font-weight:600;font-size:1rem;border:1px solid rgba(255,255,255,.22);backdrop-filter:blur(6px);transition:background .25s,border-color .25s,transform .25s var(--ease)}}
.bs:hover{{background:rgba(255,255,255,.14);border-color:rgba(255,255,255,.4);transform:translateY(-2px)}}
.chips{{display:flex;gap:10px 18px;flex-wrap:wrap;opacity:0;animation:mkUp .8s var(--ease) .85s forwards}}
.chip{{display:inline-flex;align-items:center;gap:7px;color:rgba(255,255,255,.72);font-size:.88rem;font-weight:600}}
.chip svg{{width:15px;height:15px;stroke:var(--a2);stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}}
/* hero visual — floating glass composition */
.hero-visual{{position:relative;display:grid;place-items:center;opacity:0;animation:mkUp 1s var(--ease) .5s forwards}}
.hv-main{{position:relative;width:min(360px,86%);aspect-ratio:.92;border-radius:calc(var(--r) + 10px);background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.16);backdrop-filter:blur(12px);box-shadow:0 40px 90px rgba(0,0,0,.42);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:34px;transform:perspective(900px) rotateX(var(--rx,0)) rotateY(var(--ry,0));transition:transform .5s var(--ease);will-change:transform;animation:mkFloat 7s ease-in-out infinite}}
@keyframes mkFloat{{0%,100%{{margin-top:0}}50%{{margin-top:-14px}}}}
.hv-ico{{width:96px;height:96px;border-radius:26px;display:grid;place-items:center;font-size:46px;background:linear-gradient(140deg,var(--a),var(--a2));box-shadow:0 18px 44px rgba(0,0,0,.35)}}
.hv-name{{color:#fff;font-weight:800;font-size:1.25rem;text-align:center;letter-spacing:-.01em}}
.hv-sub{{color:rgba(255,255,255,.62);font-size:.82rem;letter-spacing:.14em;text-transform:uppercase;text-align:center}}
.hv-line{{width:56%;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent)}}
.hv-chip{{position:absolute;display:flex;align-items:center;gap:9px;background:#fff;color:#101318;border-radius:14px;padding:11px 15px;font-size:.82rem;font-weight:750;box-shadow:0 18px 44px rgba(0,0,0,.35);white-space:nowrap}}
.hv-chip .st{{color:var(--a);letter-spacing:2px}}
.hv-c1{{top:6%;left:-6%;animation:mkBob 5.5s ease-in-out infinite}}
.hv-c2{{bottom:9%;right:-7%;animation:mkBob 5.5s ease-in-out infinite 1.1s}}
@keyframes mkBob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-11px)}}}}
@keyframes mkUp{{from{{opacity:0;transform:translateY(26px)}}to{{opacity:1;transform:none}}}}
.hero-fade{{position:absolute;left:0;right:0;bottom:-1px;height:110px;background:linear-gradient(transparent,#fff);z-index:1;pointer-events:none}}

/* ---------- marquee ---------- */
.mqw{{background:var(--pd);padding:20px 0;overflow:hidden;border-top:1px solid rgba(255,255,255,.07)}}
.mq{{display:flex;align-items:center;gap:38px;width:max-content;animation:mkMq 30s linear infinite}}
.mq:hover{{animation-play-state:paused}}
.mq span{{color:rgba(255,255,255,.82);font-size:.92rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;white-space:nowrap}}
.mq i{{color:var(--a);font-style:normal;font-size:.8rem}}
@keyframes mkMq{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}

/* ---------- stats ---------- */
.statwrap{{padding:0 5%;transform:translateY(-46px);margin-bottom:-46px;position:relative;z-index:2}}
.statbar{{max-width:1000px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:2px;border-radius:calc(var(--r) + 6px);overflow:hidden;box-shadow:0 26px 60px rgba(2,6,23,.18)}}
.stat{{background:linear-gradient(160deg,var(--p),var(--pd));text-align:center;color:#fff;padding:26px 16px}}
.stat .num{{font-size:1.7rem;font-weight:900;color:var(--a2);line-height:1.1}}
.stat .lab{{font-size:.82rem;color:rgba(255,255,255,.72);margin-top:4px;letter-spacing:.04em}}

/* ---------- sections ---------- */
section{{padding:clamp(72px,9vw,110px) 5%;scroll-margin-top:76px}}
.wrap{{max-width:1180px;margin:0 auto}}
.eyebrow{{display:inline-flex;align-items:center;gap:10px;font-size:.76rem;font-weight:800;letter-spacing:.22em;text-transform:uppercase;color:var(--a);margin-bottom:12px}}
.eyebrow::before{{content:'';width:24px;height:2px;border-radius:2px;background:linear-gradient(90deg,var(--a),var(--a2))}}
h2{{font-size:clamp(1.8rem, 1.2rem + 2.6vw, 2.8rem);font-weight:900;color:var(--p);line-height:1.12;letter-spacing:-.02em;margin-bottom:14px}}
.sub{{font-size:1.05rem;color:var(--g);max-width:38em;margin-bottom:48px}}
.cream{{background:var(--cr)}}

/* cards */
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:22px}}
.card{{--mx:50%;--my:50%;position:relative;background:#fff;border:1px solid var(--bd);border-radius:var(--r);padding:30px;overflow:hidden;transform:perspective(900px) rotateX(var(--rx,0)) rotateY(var(--ry,0));transition:transform .45s var(--ease),box-shadow .35s,border-color .3s;will-change:transform}}
.card::before{{content:'';position:absolute;inset:0;opacity:0;transition:opacity .45s;pointer-events:none;background:radial-gradient(380px circle at var(--mx) var(--my),{a['accent']}14,transparent 45%)}}
.card:hover{{box-shadow:0 24px 56px rgba(2,6,23,.13)}}
.card:hover::before{{opacity:1}}
.card>*{{position:relative;z-index:1}}
.ico{{width:56px;height:56px;border-radius:calc(var(--r) - 2px);display:grid;place-items:center;margin-bottom:16px;background:linear-gradient(140deg,{a['accent']}1f,{a['accent2']}30);border:1px solid {a['accent']}33}}
.ico span{{font-size:26px;transition:transform .35s var(--ease)}}
.card:hover .ico span{{transform:scale(1.18) rotate(-6deg)}}
.card h3{{font-size:1.16rem;font-weight:800;color:var(--tx);margin-bottom:8px}}
.card p{{font-size:.94rem;color:var(--g)}}
.price{{margin-top:14px;display:inline-block;background:var(--cr);color:var(--p);font-weight:800;font-size:.84rem;padding:6px 15px;border-radius:999px;border:1px solid var(--bd)}}

/* about / why */
.why-wrap{{display:grid;grid-template-columns:1.08fr .92fr;gap:56px;align-items:center}}
.whys{{list-style:none;display:flex;flex-direction:column;gap:20px;margin-top:8px}}
.why{{display:flex;gap:15px}}
.chk{{flex-shrink:0;width:34px;height:34px;border-radius:50%;background:linear-gradient(140deg,var(--a),var(--a2));display:grid;place-items:center;box-shadow:0 8px 20px {a['accent']}55}}
.chk svg{{width:16px;height:16px;stroke:#11151c;stroke-width:3.2;fill:none;stroke-linecap:round;stroke-linejoin:round}}
.why h4{{font-size:1.04rem;font-weight:800;color:var(--tx);margin-bottom:3px}}
.why p{{font-size:.92rem;color:var(--g)}}
.visual{{position:relative;border-radius:calc(var(--r) + 8px);min-height:400px;overflow:hidden;background:linear-gradient(150deg,var(--p),var(--pd));box-shadow:0 30px 70px rgba(2,6,23,.22);transform:scale(.95);transition:transform 1.1s var(--ease)}}
.visual.in{{transform:scale(1)}}
.visual::before{{content:'{n['visual']}';position:absolute;right:-24px;bottom:-30px;font-size:170px;opacity:.16;transform:rotate(-8deg)}}
.visual::after{{content:'';position:absolute;top:-30%;left:-20%;width:70%;height:90%;background:radial-gradient(circle,{a['accent']}38,transparent 62%);filter:blur(30px)}}
.vq{{position:absolute;left:22px;right:22px;bottom:22px;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.18);backdrop-filter:blur(12px);border-radius:var(--r);padding:20px 22px;color:#fff}}
.vq .st{{color:var(--a2);letter-spacing:2px;font-size:.9rem;margin-bottom:8px}}
.vq p{{font-size:.94rem;line-height:1.55;font-style:italic}}
.vq small{{display:block;margin-top:9px;color:rgba(255,255,255,.65);font-size:.76rem;letter-spacing:.14em;text-transform:uppercase}}
.vtag{{position:absolute;top:20px;left:20px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);backdrop-filter:blur(8px);color:#fff;border-radius:999px;padding:8px 17px;font-size:.74rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase}}

/* reviews */
.revs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:22px}}
.rev{{background:#fff;border:1px solid var(--bd);border-radius:var(--r);padding:28px;transition:transform .35s var(--ease),box-shadow .3s}}
.rev:hover{{transform:translateY(-6px);box-shadow:0 20px 48px rgba(2,6,23,.1)}}
.stars{{color:var(--a);font-size:1.05rem;letter-spacing:2px;margin-bottom:12px}}
.rev p{{font-size:.95rem;color:#374151;font-style:italic;margin-bottom:18px}}
.auth{{display:flex;align-items:center;gap:12px}}
.ava{{width:42px;height:42px;border-radius:50%;background:linear-gradient(140deg,var(--p),var(--a));color:#fff;display:grid;place-items:center;font-weight:800;font-size:.82rem}}
.an{{font-weight:750;font-size:.9rem;color:var(--tx)}}
.al{{font-size:.76rem;color:var(--g)}}

/* CTA band */
.band{{position:relative;text-align:center;color:#fff;overflow:hidden;background:linear-gradient(120deg,var(--pd),var(--p) 45%,var(--pd));background-size:200% 200%;animation:mkGrad 11s ease infinite}}
@keyframes mkGrad{{0%,100%{{background-position:0 50%}}50%{{background-position:100% 50%}}}}
.band::before{{content:'';position:absolute;inset:0;background:radial-gradient(circle at 18% 20%,{a['accent']}30,transparent 44%),radial-gradient(circle at 84% 82%,{a['accent2']}22,transparent 44%)}}
.band .wrap{{position:relative}}
.band h2{{color:#fff}}
.band p{{font-size:1.08rem;color:rgba(255,255,255,.86);max-width:36em;margin:0 auto 30px}}
.bw{{display:inline-flex;align-items:center;gap:9px;background:#fff;color:var(--p);padding:16px 34px;border-radius:var(--r);font-weight:800;font-size:1.02rem;transition:transform .3s var(--ease),box-shadow .3s;box-shadow:0 16px 40px rgba(0,0,0,.28);will-change:transform}}
.bw:hover{{box-shadow:0 22px 54px rgba(0,0,0,.36)}}

/* contact */
.contact-wrap{{display:grid;grid-template-columns:1fr 1.05fr;gap:56px}}
.cinfo{{display:flex;flex-direction:column;gap:14px;margin-top:8px}}
.crow{{display:flex;gap:15px;align-items:center;background:#fff;border:1px solid var(--bd);border-radius:var(--r);padding:16px 19px;transition:transform .25s var(--ease),box-shadow .25s}}
.crow:hover{{transform:translateX(5px);box-shadow:0 12px 30px rgba(2,6,23,.08)}}
.ci{{flex-shrink:0;width:44px;height:44px;border-radius:calc(var(--r) - 3px);display:grid;place-items:center;background:linear-gradient(140deg,{a['accent']}1f,{a['accent2']}30);border:1px solid {a['accent']}33;color:var(--p)}}
.ci svg{{width:19px;height:19px;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round;stroke-linejoin:round}}
.cl{{font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:var(--g);font-weight:700}}
.cv{{font-size:1.02rem;font-weight:800;color:var(--tx)}}
form{{display:flex;flex-direction:column;gap:14px;background:#fff;border:1px solid var(--bd);border-radius:calc(var(--r) + 4px);padding:32px;box-shadow:0 20px 50px rgba(2,6,23,.07)}}
input,textarea{{padding:13px 16px;border:1.5px solid var(--bd);border-radius:calc(var(--r) - 4px);font-size:.96rem;font-family:inherit;background:#fff;transition:border-color .2s,box-shadow .2s}}
input:focus,textarea:focus{{outline:none;border-color:var(--a);box-shadow:0 0 0 4px {a['accent']}22}}
.fsub{{background:var(--p);color:#fff;border:none;padding:15px;border-radius:calc(var(--r) - 4px);font-weight:800;font-size:1rem;cursor:pointer;transition:transform .25s var(--ease),background .2s,box-shadow .3s;box-shadow:0 12px 30px rgba(2,6,23,.18)}}
.fsub:hover{{background:var(--pd);transform:translateY(-2px)}}

/* footer + flag */
footer{{background:var(--pd);color:rgba(255,255,255,.6);padding:44px 5% 78px;text-align:center}}
footer .fn{{color:#fff;font-size:1.25rem;font-weight:800;margin-bottom:8px}}
footer .fn span{{color:var(--a2)}}
.concept{{margin-top:22px;font-size:.8rem;color:rgba(255,255,255,.45);max-width:40em;margin-left:auto;margin-right:auto;line-height:1.6}}
.flag{{position:fixed;right:16px;bottom:16px;z-index:220;background:#0f172a;color:#fff;font-size:.78rem;font-weight:600;padding:9px 15px;border-radius:999px;box-shadow:0 8px 26px rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.12)}}
.flag span{{color:#7dd3fc}}
.flag b{{color:var(--a2)}}

/* reveals */
.reveal{{opacity:0;transform:translateY(30px);transition:opacity .9s var(--ease),transform .9s var(--ease)}}
.reveal.in{{opacity:1;transform:none}}
.grid .card,.revs .rev,.statbar .stat{{opacity:0;transform:translateY(26px);transition:opacity .7s var(--ease),transform .7s var(--ease)}}
.grid.in .card,.revs.in .rev,.statbar.in .stat{{opacity:1;transform:none}}
.grid.in .card:nth-child(2),.revs.in .rev:nth-child(2),.statbar.in .stat:nth-child(2){{transition-delay:.08s}}
.grid.in .card:nth-child(3),.revs.in .rev:nth-child(3),.statbar.in .stat:nth-child(3){{transition-delay:.16s}}
.grid.in .card:nth-child(4),.statbar.in .stat:nth-child(4){{transition-delay:.24s}}
.grid.in .card:nth-child(5){{transition-delay:.32s}}
.grid.in .card:nth-child(6){{transition-delay:.4s}}

@media(max-width:880px){{
  .nlinks{{display:none}}
  .ntgl{{display:flex}}
  .ncta{{padding:9px 15px;font-size:.74rem}}
  .hero-grid{{grid-template-columns:1fr}}
  .hero-visual{{display:none}}
  .why-wrap,.contact-wrap{{grid-template-columns:1fr;gap:40px}}
  .visual{{min-height:320px}}
}}
@media(max-width:600px){{
  .hero{{padding:112px 5% 90px}}
  .btns{{flex-direction:column;align-items:stretch}}
  .btns a{{justify-content:center;text-align:center}}
  .statwrap{{transform:translateY(-30px);margin-bottom:-30px}}
}}
@media(prefers-reduced-motion:reduce){{
  *{{animation:none!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
  .hl>span{{transform:none!important}}
  .badge,.hero .lead,.btns,.chips,.hero-visual{{opacity:1!important}}
  .reveal,.grid .card,.revs .rev,.statbar .stat{{opacity:1!important;transform:none!important}}
  .visual{{transform:none!important}}
}}
</style>
<style>{vcss}</style>
</head>
<body>
<div class="grain" aria-hidden="true"></div>
<div class="progress" id="mkProg" aria-hidden="true"></div>

<nav id="nav">
  <div class="logo">{logo}</div>
  <ul class="nlinks">
    <li><a href="#services">{n['stag']}</a></li>
    <li><a href="#about">About</a></li>
    <li><a href="#reviews">Reviews</a></li>
    <li><a href="#contact">Contact</a></li>
  </ul>
  <div class="nav-right">
    <a href="{href}" class="ncta">{('📞 ' + phone) if phone else n['cta']}</a>
    <button class="ntgl" id="ntgl" aria-label="Open menu" aria-expanded="false" aria-controls="mmenu"><span></span><span></span><span></span></button>
  </div>
</nav>
<div class="mmenu" id="mmenu">
  <a href="#services">{n['stag']}</a>
  <a href="#about">About</a>
  <a href="#reviews">Reviews</a>
  <a href="#contact">Contact</a>
  <a href="{href}" class="mcta">{n['cta']}</a>
</div>

<header class="hero" id="top">
  <div class="hero-grid">
    <div class="hero-copy">
      <span class="badge"><span class="dot"></span>{fmt(n['badge'])} · {town}</span>
      <h1>{h1}</h1>
      <p class="lead">{fmt(n['sub'])}</p>
      <div class="btns">
        <a href="{href}" class="bp">{n['cta']} →</a>
        <a href="#services" class="bs">See More</a>
      </div>
      <div class="chips">{chips}</div>
    </div>
    <div class="hero-visual" aria-hidden="true">
      <div class="hv-main" data-tilt>
        <div class="hv-ico">{n['emoji']}</div>
        <div class="hv-name">{name}</div>
        <div class="hv-line"></div>
        <div class="hv-sub">{fmt(n['badge'])}</div>
      </div>
      <div class="hv-chip hv-c1"><span class="st">★★★★★</span> Loved by locals</div>
      <div class="hv-chip hv-c2">📍 {town} &amp; nearby</div>
    </div>
  </div>
  <div class="hero-fade" aria-hidden="true"></div>
</header>

<div class="mqw" aria-hidden="true"><div class="mq">{mq_items}{mq_items}</div></div>

<div class="statwrap"><div class="statbar">{stats}</div></div>

<div class="mid">
<section id="services">
  <div class="wrap">
    <div class="reveal">
      <div class="eyebrow">{n['stag']}</div>
      <h2>{fmt(n['shead'])}</h2>
      <p class="sub">{fmt(n['ssub'])}</p>
    </div>
    <div class="grid">{services}</div>
  </div>
</section>

<section id="about" class="cream">
  <div class="wrap why-wrap">
    <div class="reveal">
      <div class="eyebrow">Why {name}</div>
      <h2>Why Locals Choose Us</h2>
      <p class="sub">We're proud to serve {town} and the surrounding area — and we work hard to keep it that way.</p>
      <ul class="whys">{why}</ul>
    </div>
    <div class="visual">
      <span class="vtag">{town}</span>
      <div class="vq"><div class="st">★★★★★</div><p>"{quote_txt}"</p><small>{quote_nm} · {town}</small></div>
    </div>
  </div>
</section>

<section id="reviews">
  <div class="wrap">
    <div class="reveal">
      <div class="eyebrow">Reviews</div>
      <h2>What People Say</h2>
      <p class="sub">Real words from happy customers across {town} and beyond.</p>
    </div>
    <div class="revs">{reviews}</div>
  </div>
</section>
</div>

<section class="band">
  <div class="wrap reveal">
    <div class="eyebrow" style="color:var(--a2)">Ready when you are</div>
    <h2>{n['cta']} Today</h2>
    <p>Friendly, local and easy to reach — {name} is here for {town}. Get in touch and we'll take care of the rest.</p>
    <a href="{href}" class="bw">{('📞 ' + phone) if phone else n['cta']}</a>
  </div>
</section>

<section id="contact" class="cream">
  <div class="wrap contact-wrap">
    <div class="reveal">
      <div class="eyebrow">Get In Touch</div>
      <h2>{n['cta']}</h2>
      <p class="sub">We'd love to hear from you. Call us or drop a message and we'll get straight back to you.</p>
      <div class="cinfo">
        <div class="crow"><span class="ci"><svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/></svg></span><div><div class="cl">Phone</div><div class="cv">{phone or 'Add your number'}</div></div></div>
        <div class="crow"><span class="ci"><svg viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg></span><div><div class="cl">Area</div><div class="cv">{town} &amp; surrounding areas</div></div></div>
        <div class="crow"><span class="ci"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></span><div><div class="cl">Hours</div><div class="cv">Open 6 days a week</div></div></div>
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
(function(){{
  "use strict";
  var reduce=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine=window.matchMedia("(pointer: fine)").matches;
  var nav=document.getElementById('nav'),prog=document.getElementById('mkProg'),ticking=false;
  function onScroll(){{
    if(ticking)return;ticking=true;
    requestAnimationFrame(function(){{
      var y=window.scrollY||0;
      nav.classList.toggle('solid',y>40);
      if(prog){{var h=document.documentElement.scrollHeight-window.innerHeight;
        prog.style.width=(h>0?(y/h*100):0)+'%';}}
      ticking=false;
    }});
  }}
  addEventListener('scroll',onScroll,{{passive:true}});onScroll();

  var tgl=document.getElementById('ntgl'),mm=document.getElementById('mmenu');
  if(tgl&&mm){{
    tgl.addEventListener('click',function(){{
      var open=mm.classList.toggle('open');tgl.classList.toggle('open',open);
      tgl.setAttribute('aria-expanded',open);
    }});
    mm.querySelectorAll('a').forEach(function(a){{a.addEventListener('click',function(){{
      mm.classList.remove('open');tgl.classList.remove('open');tgl.setAttribute('aria-expanded','false');
    }});}});
  }}

  var io=new IntersectionObserver(function(es){{
    es.forEach(function(e){{
      if(!e.isIntersecting)return;
      e.target.classList.add('in');
      e.target.querySelectorAll('[data-count]').forEach(count);
      io.unobserve(e.target);
    }});
  }},{{threshold:.1,rootMargin:'0px 0px -6% 0px'}});
  document.querySelectorAll('.reveal,.grid,.revs,.statbar,.visual').forEach(function(el){{io.observe(el);}});

  function count(el){{
    if(el.dataset.done)return;el.dataset.done=1;
    var t=parseInt(el.dataset.count,10);
    if(reduce||!t){{el.textContent=el.dataset.count;return;}}
    var t0=null;
    function step(ts){{
      if(!t0)t0=ts;
      var p=Math.min((ts-t0)/1100,1);
      el.textContent=Math.round(t*(1-Math.pow(1-p,3)));
      if(p<1)requestAnimationFrame(step);else el.textContent=el.dataset.count;
    }}
    requestAnimationFrame(step);
  }}

  if(fine&&!reduce){{
    document.querySelectorAll('.bp,.bw,.ncta').forEach(function(b){{
      b.addEventListener('mousemove',function(e){{
        var r=b.getBoundingClientRect();
        b.style.transform='translate('+((e.clientX-r.left-r.width/2)*.22)+'px,'+((e.clientY-r.top-r.height/2)*.34)+'px)';
      }});
      b.addEventListener('mouseleave',function(){{b.style.transform='';}});
    }});
    document.querySelectorAll('[data-tilt]').forEach(function(c){{
      c.addEventListener('mousemove',function(e){{
        var r=c.getBoundingClientRect(),
            px=(e.clientX-r.left)/r.width, py=(e.clientY-r.top)/r.height;
        c.style.setProperty('--ry',((px-.5)*7)+'deg');
        c.style.setProperty('--rx',((.5-py)*5)+'deg');
        c.style.setProperty('--mx',(px*100)+'%');
        c.style.setProperty('--my',(py*100)+'%');
      }});
      c.addEventListener('mouseleave',function(){{
        c.style.setProperty('--rx','0deg');c.style.setProperty('--ry','0deg');
      }});
    }});
  }}
}})();
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
        f'<div class="gt" style="background:linear-gradient(140deg,{ARCH[NICHE.get(b["niche"], NICHE["restaurant"])["arch"]]["primary"]},{ARCH[NICHE.get(b["niche"], NICHE["restaurant"])["arch"]]["dark"]})">'
        f'<span>{NICHE.get(b["niche"], {}).get("emoji", "🌐")}</span></div>'
        f'<div class="gb"><div class="gn">{b["name"]}</div>'
        f'<div class="gm">{b["niche"]} · {b["town"]}</div></div></a>'
        for b in items)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex">
<title>HW Web Design — Live Mockups</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0b1220;color:#eef2fc}}
header{{position:relative;background:radial-gradient(60% 90% at 80% -20%,rgba(124,58,237,.3),transparent 60%),radial-gradient(50% 80% at 10% 0%,rgba(37,99,235,.35),transparent 55%),#0b1220;padding:72px 6% 56px;overflow:hidden}}
header h1{{font-size:clamp(28px,4vw,44px);font-weight:900;letter-spacing:-1px}}
header h1 span{{background:linear-gradient(92deg,#60a5fa,#a78bfa);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}}
header p{{color:rgba(238,242,252,.7);margin-top:10px;font-size:17px;max-width:640px}}
.wrap{{max-width:1140px;margin:0 auto;padding:46px 6% 90px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:18px}}
.g{{background:#101a35;border:1px solid rgba(125,160,255,.14);border-radius:16px;overflow:hidden;text-decoration:none;color:inherit;transition:transform .3s cubic-bezier(.16,1,.3,1),box-shadow .3s,border-color .3s}}
.g:hover{{transform:translateY(-6px);box-shadow:0 22px 50px rgba(2,6,20,.55);border-color:rgba(125,160,255,.35)}}
.gt{{height:120px;display:flex;align-items:center;justify-content:center}}
.gt span{{font-size:46px;filter:drop-shadow(0 6px 16px rgba(0,0,0,.4))}}
.gb{{padding:16px 18px}}.gn{{font-weight:800;font-size:15.5px}}.gm{{color:rgba(238,242,252,.55);font-size:12.5px;text-transform:capitalize;margin-top:3px}}
</style></head><body>
<header><h1>Live Website <span>Mockups</span></h1>
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
