#!/usr/bin/env python3
"""
HW Web Design — Free Mockup Generator (multi-architecture engine).

Reads the leads CSV and builds a personalised single-page website mockup for
each top callable lead (business name, town and phone baked in), plus a gallery
index. These are the closing tool: "I built you a sample — have a look." They
deploy with the repo, so each lead's mockup is live at
  https://hwwebdesign.co.uk/mockups/<slug>/
once pushed to main.

Unlike a single template with colour swaps, every mockup is rendered through one
of FOUR genuinely different site architectures, chosen deterministically from the
business name + niche so no two feel template-stamped:

  · STAGE     cinematic centred hero, dark→light, service-card grid
  · ATELIER   cream editorial, serif display, split hero, zig-zag rows, pull-quote
  · MOMENTUM  full-dark kinetic, condensed caps, poster hero, bold service list
  · BLOOM     warm soft boutique, rounded floating nav, card-cluster hero, tiles

Each has its own theme, type, hero, section rhythm, navigation and motion.

Usage:
    python mockup_gen.py                      # uses the default area CSV
    python mockup_gen.py leads/leads_x.csv    # any sweep CSV

Sample content (reviews, prices, stats) is illustrative and clearly labelled as
a design concept on every page.
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
    "barber": dict(primary="#232326", dark="#141416", accent="#b8863b",
                   accent2="#e3c07f", hero="#0d0d10,#232326,#161618",
                   text="#26262b", grey="#6b6b73", border="#e6e4e0", cream="#f7f6f3",
                   stats=[("Walk-ins", "Welcome"), ("Sharp", "Every time"),
                          ("6 Days", "Open")],
                   why=[("Skilled Barbers", "Precision cuts, fades and beard work by experienced hands."),
                        ("Walk-In or Book", "Pop in when it suits, or reserve your chair online."),
                        ("Relaxed Atmosphere", "Good chat, good music and a proper finish every time."),
                        ("Sharp, Every Time", "From classic cuts to modern styles — done right.")]),
    "club": dict(primary="#15603a", dark="#0f4429", accent="#c9972a",
                 accent2="#f0c060", hero="#08301d,#12563a,#0d4029",
                 text="#1f2b24", grey="#5f7a6a", border="#dbe8e0", cream="#f2f9f5",
                 stats=[("All", "Abilities welcome"), ("New", "Members welcome"),
                        ("Juniors", "& seniors")],
                 why=[("Everyone's Welcome", "From beginners to seasoned members — there's a place for you."),
                      ("Great Facilities", "Well-kept grounds, equipment and a friendly clubhouse."),
                      ("Coaching & Socials", "Improve your game and enjoy the social side too."),
                      ("Community Spirit", "More than a club — a proper local community.")]),
    "studio": dict(primary="#7c3a9d", dark="#5c2a76", accent="#e0894a",
                   accent2="#f4b78a", hero="#2a1233,#4a2258,#3a1a48",
                   text="#3a2a40", grey="#7a6a80", border="#ecdff2", cream="#faf5fc",
                   stats=[("All", "Levels welcome"), ("Small", "Class sizes"),
                          ("Weekly", "Timetable")],
                   why=[("Every Level Welcome", "Total beginners to advanced — classes for everyone."),
                        ("Small, Friendly Classes", "Personal attention in a calm, supportive space."),
                        ("Expert Instructors", "Qualified, encouraging teachers who genuinely care."),
                        ("Flexible Passes", "Drop in or join — memberships to suit you.")]),
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
    "detailing": dict(arch="trades", emoji="✨", visual="🚘",
        badge="Detailing & Valeting", hl="Every Time",
        head="Showroom Shine, <span>Every Time</span>",
        sub="Professional car detailing and valeting in {town} — paint correction, ceramic coatings and protection that keeps your car looking its best.",
        cta="Get a Free Quote", stag="Our Services", shead="Detailing & Protection",
        ssub="From a deep clean to full paint protection — proper products, proper process, proper results.",
        services=[svc("🧼", "Full Valet", "Inside and out, back to its best.", "from £45"),
                  svc("✨", "Machine Polish & Correction", "Swirls and scratches carefully removed."),
                  svc("🛡", "Ceramic Coating", "Long-term gloss and protection.", "from £199"),
                  svc("🎞", "Paint Protection Film", "Invisible armour for high-impact areas."),
                  svc("🪑", "Interior Deep Clean", "Seats, carpets and trim, properly refreshed."),
                  svc("🛞", "Wheels & Callipers", "Deep-cleaned, sealed and dressed.")]),
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
    "barber": dict(arch="barber", emoji="💈", visual="💈",
        badge="Barbershop", hl="Every Time",
        head="Sharp Cuts, <span>Every Time</span>",
        sub="Skin fades, classic cuts, beard trims and hot-towel shaves in {town}. Walk in or book your chair — you'll leave looking sharp.",
        cta="Book a Chair", stag="Our Services", shead="Cuts & Grooming",
        ssub="From a quick tidy-up to the full works — done properly, every time.",
        services=[svc("✂️", "Skin Fades & Cuts", "Precision fades and classic cuts.", "from £16"),
                  svc("🧔", "Beard Trim & Shape", "Sharp lines and a clean finish.", "from £10"),
                  svc("🪒", "Hot Towel Shave", "A traditional, relaxing wet shave.", "from £20"),
                  svc("👦", "Kids' Cuts", "Patient, friendly cuts for the little ones.", "from £12"),
                  svc("💈", "Cut & Beard Combo", "The full works, head to chin.", "from £24"),
                  svc("🧴", "Styling & Products", "Advice and quality grooming products.")]),
    "club": dict(arch="club", emoji="🏅", visual="🏆",
        badge="Members' Club", hl="Local Club",
        head="Your Local <span>Club</span>",
        sub="A friendly, welcoming club in {town} — membership, coaching and events for all ages and abilities. Come and be part of it.",
        cta="Become a Member", stag="What We Offer", shead="Join the Club",
        ssub="Whether you're brand new or a seasoned member, there's a place for you here.",
        services=[svc("🎫", "Membership", "Flexible membership for all ages."),
                  svc("🎓", "Coaching & Lessons", "Improve with friendly, expert coaching."),
                  svc("📅", "Fixtures & Events", "A full calendar of fixtures and socials."),
                  svc("🏛", "Facilities & Hire", "Great facilities, available to hire."),
                  svc("🧒", "Juniors & Beginners", "A warm welcome for newcomers and kids."),
                  svc("🍻", "Clubhouse & Socials", "The social heart of the club.")]),
    "studio": dict(arch="studio", emoji="🧘", visual="🧘",
        badge="Studio", hl="Belong",
        head="Move, Breathe, <span>Belong</span>",
        sub="Welcoming classes for every level in {town} — find your flow, build strength and feel great. Your first class is the hardest step.",
        cta="Book a Class", stag="Our Classes", shead="Classes For Everyone",
        ssub="Beginners to advanced — small, friendly classes with room to grow.",
        services=[svc("🌱", "Beginners' Classes", "The perfect place to start."),
                  svc("🗓", "Weekly Timetable", "Classes morning, noon and evening."),
                  svc("👥", "Small Group Classes", "Personal attention, friendly faces."),
                  svc("🧘", "Private Sessions", "One-to-one, tailored to you."),
                  svc("✨", "All Levels Welcome", "Move at your own pace, always."),
                  svc("🎟", "Memberships & Passes", "Drop in or join — your choice.", "from £10")]),
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
    "barber": [("Best fade I've had in ages — in and out, sharp finish, sound bloke.", "Jordan M."),
               ("Been coming here for years. Always a proper cut and good banter.", "Chris P."),
               ("Took my lad for his first proper haircut, they were brilliant with him.", "Dean R.")],
    "club": [("Joined last season and everyone made me feel welcome straight away.", "Helen W."),
             ("Brilliant facilities and a real community feel. My kids love it.", "Mark T."),
             ("Great coaching and a lovely clubhouse. Best decision we made.", "Sarah L.")],
    "studio": [("Nervous first-timer and they put me completely at ease. Hooked now!", "Amy R."),
               ("Small classes mean real attention. I've improved so much already.", "Bec H."),
               ("The instructors are amazing and the whole vibe is so welcoming.", "Priya K.")],
}
NEARBY = ["High Wycombe", "Marlow", "Beaconsfield", "Amersham"]

# Hand-built one-off mockups that must NEVER be overwritten by the generator.
BESPOKE_SLUGS = {"detail-kings-high-wycombe"}

# ---------------------------------------------------------------- architecture pick
# Each niche maps to a shortlist of suitable architectures; the business name
# hash chooses within it, so pages vary even within one niche.
CANDIDATES = {
    "restaurant": ["stage", "bloom"], "cafe": ["bloom", "stage"], "bakery": ["bloom", "atelier"],
    "salon": ["atelier", "bloom"], "dentist": ["atelier", "stage"], "vet": ["stage", "atelier"],
    "plumber": ["momentum", "stage"], "electrician": ["momentum", "stage"], "roofer": ["momentum", "stage"],
    "gym": ["momentum", "stage"], "accountant": ["atelier", "stage"], "garage": ["momentum", "stage"],
    "estate agent": ["atelier", "stage"], "optician": ["atelier", "stage"], "detailing": ["momentum", "stage"],
    "barber": ["momentum", "stage"], "club": ["stage", "atelier"], "studio": ["bloom", "stage"],
}

# Businesses the source data mis-categorised: correct the niche by slug so the
# page shows the right trade (a rowing club must not show gym services, etc.).
NICHE_OVERRIDE = {
    "marlow-rowing-club-marlow": "club",
    "upper-thames-rowing-club-henley-on-thames": "club",
    "farnham-royal-cricket-club-slough": "club",
    "phyllis-court-croquet-club-henley-on-thames": "club",
    "henley-yoga-studio-henley-on-thames": "studio",
    "pole-attack-aylesbury": "studio",
    "barber-crew-henley-on-thames": "barber",
    "the-barbershop-group-princes-risborough": "barber",
    "ozzy-s-traditional-barbers-amersham": "barber",
    "the-art-of-turkish-barbering-marlow": "barber",
    "hairdressing-for-men-amersham": "barber",
}


def pick_arch(name, town, niche):
    cands = CANDIDATES.get(niche, ["stage", "bloom"])
    h = int(hashlib.md5((name + "|" + town + "|arch").encode()).hexdigest(), 16)
    return cands[h % len(cands)]


# ---------------------------------------------------------------- helpers
def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def tel(phone):
    return "".join(c for c in (phone or "") if c.isdigit() or c == "+")


def _count_num(s):
    digits = ""
    for ch in s:
        if ch.isdigit():
            digits += ch
        else:
            break
    if digits and "." not in s[:len(digits) + 1]:
        return digits, s[len(digits):]
    return None


def _vars(a):
    h = [x.strip() for x in a["hero"].split(",")]
    return (":root{"
            "--p:" + a["primary"] + ";--pd:" + a["dark"] + ";--a:" + a["accent"] +
            ";--a2:" + a["accent2"] + ";--tx:" + a["text"] + ";--g:" + a["grey"] +
            ";--bd:" + a["border"] + ";--cr:" + a["cream"] +
            ";--h0:" + h[0] + ";--h1:" + h[1] + ";--h2:" + h[2] +
            ";--ease:cubic-bezier(.16,1,.3,1)}")


def _logo(name):
    parts = esc(name).split()
    if len(parts) > 1:
        return " ".join(parts[:-1]) + ' <span>' + parts[-1] + "</span>"
    return "<span>" + esc(name) + "</span>"


def _headline(head, town):
    """Split head at its <span> accent into line-mask spans."""
    head = head.format(town=town)
    if "<span>" in head:
        pre, rest = head.split("<span>", 1)
        acc, post = rest.split("</span>", 1)
        out = ""
        if pre.strip():
            out += '<span class="hl"><span>' + esc(pre.strip()) + " </span></span>"
        out += '<span class="hl"><span><em>' + esc(acc) + "</em>" + esc(post) + "</span></span>"
        return out
    return '<span class="hl"><span>' + esc(head) + "</span></span>"


def _stats_html(a):
    out = ""
    for num, lab in a["stats"]:
        c = _count_num(num)
        inner = ('<span data-count="' + c[0] + '">' + c[0] + "</span>" + c[1]) if c else esc(num)
        out += '<div class="stat"><div class="num">' + inner + '</div><div class="lab">' + esc(lab) + "</div></div>"
    return out


def _reviews_list(n, town):
    rev_towns = [town] + [t for t in NEARBY if t != town]
    items = []
    for i, (txt, nm) in enumerate(REVIEWS[n["arch"]]):
        initials = nm.split()[0][0] + nm.split()[-1][0]
        items.append(dict(txt=txt, nm=nm, initials=initials, place=rev_towns[i % len(rev_towns)]))
    return items


# ---------------------------------------------------------------- shared JS
CORE_JS = """
<script>
(function(){
  "use strict";
  var reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine=matchMedia("(pointer: fine)").matches;
  var nav=document.getElementById('nav'),prog=document.getElementById('prog'),t=false;
  function onScroll(){
    if(t)return;t=true;
    requestAnimationFrame(function(){
      var y=scrollY||0;
      if(nav)nav.classList.toggle('solid',y>40);
      if(prog){var h=document.documentElement.scrollHeight-innerHeight;prog.style.width=(h>0?(y/h*100):0)+'%';}
      t=false;
    });
  }
  addEventListener('scroll',onScroll,{passive:true});onScroll();

  var tg=document.getElementById('tgl'),mm=document.getElementById('mm');
  if(tg&&mm){
    tg.addEventListener('click',function(){
      var o=mm.classList.toggle('open');tg.classList.toggle('open',o);tg.setAttribute('aria-expanded',o);
    });
    mm.querySelectorAll('a').forEach(function(a){a.addEventListener('click',function(){
      mm.classList.remove('open');tg.classList.remove('open');tg.setAttribute('aria-expanded','false');
    });});
  }

  function count(el){
    if(el.dataset.done)return;el.dataset.done=1;
    var target=parseInt(el.dataset.count,10);
    if(reduce||!target){el.textContent=el.dataset.count;return;}
    var s=null;
    function step(ts){
      if(!s)s=ts;var p=Math.min((ts-s)/1200,1);
      el.textContent=Math.round(target*(1-Math.pow(1-p,3)));
      if(p<1)requestAnimationFrame(step);else el.textContent=el.dataset.count;
    }
    requestAnimationFrame(step);
  }
  var io=new IntersectionObserver(function(es){
    es.forEach(function(e){
      if(!e.isIntersecting)return;
      e.target.classList.add('in');
      e.target.querySelectorAll('[data-count]').forEach(count);
      io.unobserve(e.target);
    });
  },{threshold:.12,rootMargin:'0px 0px -6% 0px'});
  document.querySelectorAll('.reveal,.clip,.blur,.stagger,.statbar,.panel,.count-wrap').forEach(function(el){io.observe(el);});

  // rotating pull-quote (atelier)
  var rot=document.querySelector('.qrot');
  if(rot&&!reduce){
    var qs=rot.querySelectorAll('.q'),i=0;
    if(qs.length>1)setInterval(function(){qs[i].classList.remove('on');i=(i+1)%qs.length;qs[i].classList.add('on');},4200);
  }

  if(fine&&!reduce){
    document.querySelectorAll('.bp,.bw,.ncta,[data-mag]').forEach(function(b){
      b.addEventListener('mousemove',function(e){
        var r=b.getBoundingClientRect();
        b.style.transform='translate('+((e.clientX-r.left-r.width/2)*.2)+'px,'+((e.clientY-r.top-r.height/2)*.3)+'px)';
      });
      b.addEventListener('mouseleave',function(){b.style.transform='';});
    });
    document.querySelectorAll('[data-tilt]').forEach(function(c){
      c.addEventListener('mousemove',function(e){
        var r=c.getBoundingClientRect(),px=(e.clientX-r.left)/r.width,py=(e.clientY-r.top)/r.height;
        c.style.setProperty('--ry',((px-.5)*7)+'deg');c.style.setProperty('--rx',((.5-py)*5)+'deg');
        c.style.setProperty('--mx',(px*100)+'%');c.style.setProperty('--my',(py*100)+'%');
      });
      c.addEventListener('mouseleave',function(){c.style.setProperty('--rx','0deg');c.style.setProperty('--ry','0deg');});
    });
  }
})();
</script>
"""

# ---------------------------------------------------------------- shared CSS core
CORE_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{color:var(--tx);line-height:1.65;background:#fff;overflow-x:hidden;-webkit-font-smoothing:antialiased}
a{text-decoration:none;color:inherit}
img{max-width:100%;display:block}
h1,h2,h3,h4{text-wrap:balance;letter-spacing:-.02em}
:focus-visible{outline:3px solid var(--a2);outline-offset:3px;border-radius:6px}
.grain{position:fixed;inset:-60px;z-index:6;pointer-events:none;opacity:.24;mix-blend-mode:soft-light;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.4'/%3E%3C/svg%3E")}
.prog{position:fixed;top:0;left:0;height:2.5px;width:0;z-index:300;background:linear-gradient(90deg,var(--a),var(--a2));box-shadow:0 0 10px var(--a)}
/* nav skeleton */
nav{position:fixed;top:0;left:0;right:0;z-index:200;display:flex;align-items:center;justify-content:space-between;padding:0 5%;height:70px;transition:background .35s,box-shadow .35s,border-color .35s,transform .35s}
.logo{font-size:1.2rem;font-weight:800;color:#fff}
.logo span{color:var(--a2)}
.nlinks{display:flex;gap:30px;list-style:none}
.nlinks a{position:relative;font-size:.9rem;font-weight:600;color:rgba(255,255,255,.82);transition:color .25s}
.nlinks a::after{content:'';position:absolute;left:0;bottom:-6px;height:2px;width:0;background:var(--a);transition:width .3s var(--ease)}
.nlinks a:hover{color:#fff}.nlinks a:hover::after{width:100%}
.nav-right{display:flex;align-items:center;gap:10px}
.ncta{background:var(--a);color:#11151c;padding:11px 22px;border-radius:10px;font-weight:800;font-size:.85rem;white-space:nowrap;box-shadow:0 10px 26px rgba(0,0,0,.26);transition:transform .25s var(--ease),filter .2s;will-change:transform}
.ncta:hover{filter:brightness(1.08)}
.tgl{display:none;flex-direction:column;justify-content:center;align-items:center;gap:5px;width:44px;height:44px;background:transparent;border:0;cursor:pointer}
.tgl span{width:22px;height:2px;border-radius:2px;background:#fff;transition:transform .3s var(--ease),opacity .2s}
.tgl.open span:nth-child(1){transform:translateY(7px) rotate(45deg)}
.tgl.open span:nth-child(2){opacity:0}
.tgl.open span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
.mm{position:fixed;top:70px;left:0;right:0;z-index:190;background:rgba(12,14,20,.97);backdrop-filter:blur(14px);display:flex;flex-direction:column;padding:8px 5% 20px;transform:translateY(-140%);transition:transform .38s var(--ease);border-bottom:1px solid rgba(255,255,255,.1)}
.mm.open{transform:translateY(0)}
.mm a{color:rgba(255,255,255,.92);font-size:1rem;font-weight:600;padding:14px 4px;border-bottom:1px solid rgba(255,255,255,.08)}
.mm a.mcta{background:var(--a);color:#11151c;text-align:center;border-radius:12px;margin-top:12px;border:0;font-weight:800}
/* buttons */
.bp{position:relative;display:inline-flex;align-items:center;gap:9px;background:var(--a);color:#11151c;padding:16px 32px;border-radius:12px;font-weight:800;font-size:1rem;overflow:hidden;box-shadow:0 14px 36px rgba(0,0,0,.28);transition:transform .3s var(--ease),filter .2s;will-change:transform}
.bp:hover{filter:brightness(1.07)}
.bp::after{content:'';position:absolute;inset:0;background:linear-gradient(115deg,transparent 42%,rgba(255,255,255,.5) 50%,transparent 58%);background-size:240% 100%;background-position:140% 0;animation:sheen 5.4s var(--ease) infinite;pointer-events:none}
@keyframes sheen{0%,58%{background-position:140% 0}86%,100%{background-position:-60% 0}}
.bs{display:inline-flex;align-items:center;gap:8px;padding:16px 30px;border-radius:12px;font-weight:700;font-size:1rem;transition:transform .25s var(--ease),background .25s,border-color .25s}
.bw{display:inline-flex;align-items:center;gap:9px;background:#fff;color:var(--p);padding:16px 34px;border-radius:12px;font-weight:800;font-size:1.02rem;box-shadow:0 16px 40px rgba(0,0,0,.26);transition:transform .3s var(--ease),box-shadow .3s;will-change:transform}
/* sections */
section{padding:clamp(70px,9vw,112px) 5%;scroll-margin-top:78px;position:relative}
.wrap{max-width:1180px;margin:0 auto}
.eyebrow{display:inline-flex;align-items:center;gap:10px;font-size:.75rem;font-weight:800;letter-spacing:.22em;text-transform:uppercase;color:var(--a);margin-bottom:14px}
.eyebrow::before{content:'';width:24px;height:2px;background:linear-gradient(90deg,var(--a),var(--a2))}
h2{font-size:clamp(1.8rem, 1.2rem + 2.6vw, 2.9rem);font-weight:900;color:var(--p);line-height:1.12;margin-bottom:14px}
.sub{font-size:1.05rem;color:var(--g);max-width:40em;margin-bottom:48px}
/* reveals */
.reveal{opacity:0;transform:translateY(30px);transition:opacity .9s var(--ease),transform .9s var(--ease)}
.reveal.in{opacity:1;transform:none}
.clip{opacity:0;clip-path:inset(0 0 100% 0);transition:opacity 1s var(--ease),clip-path 1.1s var(--ease)}
.clip.in{opacity:1;clip-path:inset(0 0 0 0)}
.blur{opacity:0;filter:blur(14px);transform:translateY(22px) scale(.98);transition:opacity 1s ease,filter 1s ease,transform 1s var(--ease)}
.blur.in{opacity:1;filter:none;transform:none}
.stagger>*{opacity:0;transform:translateY(26px);transition:opacity .7s var(--ease),transform .7s var(--ease)}
.stagger.in>*{opacity:1;transform:none}
.stagger.in>*:nth-child(2){transition-delay:.07s}.stagger.in>*:nth-child(3){transition-delay:.14s}
.stagger.in>*:nth-child(4){transition-delay:.21s}.stagger.in>*:nth-child(5){transition-delay:.28s}
.stagger.in>*:nth-child(6){transition-delay:.35s}
/* footer + flag */
footer{background:var(--pd);color:rgba(255,255,255,.6);padding:46px 5% 78px;text-align:center}
footer .fn{color:#fff;font-size:1.25rem;font-weight:800;margin-bottom:8px}
footer .fn span{color:var(--a2)}
.concept{margin:22px auto 0;font-size:.8rem;color:rgba(255,255,255,.45);max-width:42em;line-height:1.6}
.flag{position:fixed;right:16px;bottom:16px;z-index:220;background:#0f172a;color:#fff;font-size:.78rem;font-weight:600;padding:9px 15px;border-radius:999px;box-shadow:0 8px 26px rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.12)}
.flag b{color:var(--a2)}
.hl{display:block;overflow:hidden}
.hl>span{display:block;transform:translateY(115%);animation:line 1s var(--ease) forwards}
.hl:nth-child(1)>span{animation-delay:.12s}.hl:nth-child(2)>span{animation-delay:.28s}
@keyframes line{to{transform:translateY(0)}}
h1 em{font-style:normal;background:linear-gradient(92deg,var(--a),var(--a2));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
@keyframes breathe{0%,100%{transform:scale(1) translate(0,0)}50%{transform:scale(1.14) translate(-22px,16px)}}
@keyframes up{from{opacity:0;transform:translateY(26px)}to{opacity:1;transform:none}}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-11px)}}
@media(max-width:880px){
  .nlinks{display:none}.tgl{display:flex}.ncta{padding:9px 15px;font-size:.74rem;white-space:nowrap}
  .logo{font-size:1.05rem;max-width:44vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
}
@media(prefers-reduced-motion:reduce){
  *{animation:none!important;transition-duration:.01ms!important;scroll-behavior:auto!important}
  .hl>span{transform:none!important}
  .reveal,.clip,.blur,.stagger>*{opacity:1!important;transform:none!important;clip-path:none!important;filter:none!important}
}
"""

# Base bits every page needs (badge/chip layout), themed by each architecture.
BASE_BITS = (
    ".badge{display:inline-flex;align-items:center;gap:9px;padding:8px 17px;border-radius:999px;"
    "font-size:.8rem;font-weight:700;letter-spacing:.04em;margin-bottom:24px}"
    ".badge .dot{width:7px;height:7px;border-radius:50%}"
    ".chip{display:inline-flex;align-items:center;gap:6px}"
    ".fsub{border:none;cursor:pointer;justify-content:center}"
)

# ================================================================ STAGE
CSS_STAGE = """
.t-stage{font-family:'Segoe UI',system-ui,-apple-system,sans-serif}
.s-hero{min-height:100svh;display:flex;align-items:center;justify-content:center;text-align:center;padding:120px 6% 130px;position:relative;overflow:hidden;isolation:isolate;background:linear-gradient(135deg,var(--h0),var(--h1) 52%,var(--h2))}
.s-hero::before{content:'';position:absolute;z-index:-1;inset:0;background:radial-gradient(circle at 50% 0,color-mix(in srgb,var(--a) 26%,transparent),transparent 55%)}
.orb{position:absolute;z-index:-1;border-radius:50%;filter:blur(60px);pointer-events:none;animation:breathe 12s ease-in-out infinite}
.o1{top:-16%;right:-8%;width:min(50vw,560px);aspect-ratio:1;background:radial-gradient(circle,color-mix(in srgb,var(--a) 40%,transparent),transparent 62%)}
.o2{bottom:-22%;left:-10%;width:min(40vw,440px);aspect-ratio:1;background:radial-gradient(circle,color-mix(in srgb,var(--a2) 34%,transparent),transparent 60%);animation-direction:reverse}
.grid-ov{position:absolute;inset:0;z-index:-1;background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:60px 60px;-webkit-mask-image:radial-gradient(circle at 50% 40%,#000,transparent 75%);mask-image:radial-gradient(circle at 50% 40%,#000,transparent 75%)}
.s-hero-in{max-width:900px;position:relative}
.badge{background:rgba(255,255,255,.07);border:1px solid color-mix(in srgb,var(--a) 45%,transparent);color:var(--a2);opacity:0;animation:up .7s var(--ease) .1s forwards}
.badge .dot{background:var(--a2);box-shadow:0 0 10px var(--a2)}
.s-hero h1{font-size:clamp(2.4rem, 1.2rem + 5.2vw, 4.4rem);font-weight:900;color:#fff;line-height:1.05;margin-bottom:22px}
.lead{font-size:clamp(1.02rem,.96rem + .4vw,1.2rem);color:rgba(255,255,255,.78);max-width:38em;margin:0 auto 30px;opacity:0;animation:up .8s var(--ease) .55s forwards}
.btns{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:26px;opacity:0;animation:up .8s var(--ease) .7s forwards}
.s-hero .bs{background:rgba(255,255,255,.08);color:#fff;border:1px solid rgba(255,255,255,.22)}
.s-hero .bs:hover{background:rgba(255,255,255,.15);transform:translateY(-2px)}
.chips{display:flex;gap:10px 20px;flex-wrap:wrap;justify-content:center;opacity:0;animation:up .8s var(--ease) .85s forwards}
.chip{color:rgba(255,255,255,.72);font-size:.88rem;font-weight:600}
.s-fade{position:absolute;left:0;right:0;bottom:-1px;height:120px;background:linear-gradient(transparent,#fff);z-index:1;pointer-events:none}
.mqw{background:var(--pd);padding:18px 0;overflow:hidden}
.mq{display:flex;align-items:center;gap:38px;width:max-content;animation:mq 30s linear infinite}
.mq:hover{animation-play-state:paused}
.mq span{color:rgba(255,255,255,.82);font-size:.9rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;white-space:nowrap}
.mq i{color:var(--a);font-style:normal}
@keyframes mq{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.statwrap{padding:0 5%;transform:translateY(-46px);margin-bottom:-46px;position:relative;z-index:2}
.statbar{max-width:1000px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:2px;border-radius:18px;overflow:hidden;box-shadow:0 26px 60px rgba(2,6,23,.18)}
.stat{background:linear-gradient(160deg,var(--p),var(--pd));text-align:center;color:#fff;padding:26px 16px}
.stat .num{font-size:1.7rem;font-weight:900;color:var(--a2)}
.stat .lab{font-size:.82rem;color:rgba(255,255,255,.72);margin-top:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:22px}
.card{--mx:50%;--my:50%;position:relative;background:#fff;border:1px solid var(--bd);border-radius:16px;padding:30px;overflow:hidden;transform:perspective(900px) rotateX(var(--rx,0)) rotateY(var(--ry,0));transition:transform .45s var(--ease),box-shadow .35s;will-change:transform}
.card::before{content:'';position:absolute;inset:0;opacity:0;transition:opacity .45s;pointer-events:none;background:radial-gradient(380px circle at var(--mx) var(--my),color-mix(in srgb,var(--a) 12%,transparent),transparent 45%)}
.card:hover{box-shadow:0 24px 56px rgba(2,6,23,.13)}.card:hover::before{opacity:1}
.card>*{position:relative;z-index:1}
.ico{width:56px;height:56px;border-radius:14px;display:grid;place-items:center;font-size:26px;margin-bottom:16px;background:linear-gradient(140deg,color-mix(in srgb,var(--a) 16%,#fff),color-mix(in srgb,var(--a2) 22%,#fff));border:1px solid color-mix(in srgb,var(--a) 30%,transparent)}
.card h3{font-size:1.14rem;font-weight:800;color:var(--tx);margin-bottom:8px}
.card p{font-size:.94rem;color:var(--g)}
.price{margin-top:14px;display:inline-block;background:var(--cr);color:var(--p);font-weight:800;font-size:.84rem;padding:6px 15px;border-radius:999px;border:1px solid var(--bd)}
.cream{background:var(--cr)}
.awrap{display:grid;grid-template-columns:1.05fr .95fr;gap:56px;align-items:center}
.whys{list-style:none;display:flex;flex-direction:column;gap:18px;margin-top:8px}
.why{display:flex;gap:14px}
.chk{flex-shrink:0;width:32px;height:32px;border-radius:50%;background:linear-gradient(140deg,var(--a),var(--a2));display:grid;place-items:center;color:#11151c;font-weight:900;font-size:.9rem}
.why h4{font-size:1.02rem;font-weight:800;color:var(--tx);margin-bottom:2px}
.why p{font-size:.92rem;color:var(--g)}
.svisual{position:relative;border-radius:22px;min-height:400px;overflow:hidden;background:linear-gradient(150deg,var(--p),var(--pd));box-shadow:0 30px 70px rgba(2,6,23,.22)}
.svisual::before{content:attr(data-emoji);position:absolute;right:-24px;bottom:-30px;font-size:170px;opacity:.16;transform:rotate(-8deg)}
.svq{position:absolute;left:22px;right:22px;bottom:22px;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.18);backdrop-filter:blur(12px);border-radius:14px;padding:20px;color:#fff}
.svq .st{color:var(--a2);letter-spacing:2px;margin-bottom:8px}
.svq p{font-size:.94rem;font-style:italic}
.svq small{display:block;margin-top:9px;color:rgba(255,255,255,.65);font-size:.74rem;letter-spacing:.12em;text-transform:uppercase}
.revs{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:22px}
.rev{background:#fff;border:1px solid var(--bd);border-radius:16px;padding:28px;transition:transform .35s var(--ease),box-shadow .3s}
.rev:hover{transform:translateY(-6px);box-shadow:0 20px 48px rgba(2,6,23,.1)}
.stars{color:var(--a);letter-spacing:2px;margin-bottom:12px}
.rev p{font-size:.95rem;color:#374151;font-style:italic;margin-bottom:18px}
.auth{display:flex;align-items:center;gap:12px}
.ava{width:42px;height:42px;border-radius:50%;background:linear-gradient(140deg,var(--p),var(--a));color:#fff;display:grid;place-items:center;font-weight:800;font-size:.82rem}
.an{font-weight:750;font-size:.9rem;color:var(--tx)}.al{font-size:.76rem;color:var(--g)}
.band{text-align:center;color:#fff;overflow:hidden;background:linear-gradient(120deg,var(--pd),var(--p) 45%,var(--pd));background-size:200% 200%;animation:grad 11s ease infinite}
@keyframes grad{0%,100%{background-position:0 50%}50%{background-position:100% 50%}}
.band h2{color:#fff}.band .eyebrow{color:var(--a2)}
.band p{font-size:1.08rem;color:rgba(255,255,255,.86);max-width:36em;margin:0 auto 30px}
.contact .cwrap{display:grid;grid-template-columns:1fr 1.05fr;gap:56px}
.cinfo{display:flex;flex-direction:column;gap:14px;margin-top:8px}
.crow{display:flex;gap:15px;align-items:center;background:#fff;border:1px solid var(--bd);border-radius:14px;padding:15px 18px;transition:transform .25s var(--ease),box-shadow .25s}
.crow:hover{transform:translateX(5px);box-shadow:0 12px 30px rgba(2,6,23,.08)}
.ci{flex-shrink:0;width:44px;height:44px;border-radius:12px;display:grid;place-items:center;font-size:20px;background:color-mix(in srgb,var(--a) 12%,#fff);border:1px solid color-mix(in srgb,var(--a) 26%,transparent)}
.cl{font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:var(--g);font-weight:700}
.cv{font-size:1.02rem;font-weight:800;color:var(--tx)}
form{display:flex;flex-direction:column;gap:14px;background:#fff;border:1px solid var(--bd);border-radius:20px;padding:32px;box-shadow:0 20px 50px rgba(2,6,23,.07)}
input,textarea{padding:13px 16px;border:1.5px solid var(--bd);border-radius:10px;font-size:.96rem;font-family:inherit;background:#fff;transition:border-color .2s,box-shadow .2s}
input:focus,textarea:focus{outline:none;border-color:var(--a);box-shadow:0 0 0 4px color-mix(in srgb,var(--a) 18%,transparent)}
@media(max-width:880px){.awrap,.contact .cwrap{grid-template-columns:1fr;gap:40px}.svisual{min-height:320px}}
@media(max-width:600px){.s-hero{padding:110px 6% 100px}.btns{flex-direction:column;align-items:stretch}.btns a{justify-content:center}}
"""

# ================================================================ ATELIER
CSS_ATELIER = """
.t-atelier{font-family:'Segoe UI',system-ui,sans-serif;background:var(--cr)}
.t-atelier h1,.t-atelier h2,.t-atelier h3,.t-atelier .a-num,.t-atelier .logo{font-family:'Palatino Linotype','Book Antiqua',Georgia,serif;letter-spacing:-.01em}
.t-atelier .logo{color:var(--p)}
.t-atelier .nlinks a{color:var(--tx)}
.t-atelier .tgl span{background:var(--p)}
.t-atelier nav.solid{background:color-mix(in srgb,var(--cr) 90%,transparent);backdrop-filter:blur(12px);box-shadow:0 8px 30px rgba(2,6,23,.06);border-bottom:1px solid var(--bd)}
.a-hero{padding:150px 6% 90px;border-bottom:1px solid var(--bd)}
.a-grid{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:1.15fr .85fr;gap:60px;align-items:center}
.a-eye{font-size:.78rem;letter-spacing:.24em;text-transform:uppercase;color:var(--a);font-weight:700;display:block;margin-bottom:22px}
.a-hero h1{font-size:clamp(2.6rem,1.4rem + 5vw,4.6rem);font-weight:700;color:var(--p);line-height:1.04;margin-bottom:24px}
.a-hero .lead{font-size:1.16rem;color:var(--g);max-width:32em;margin-bottom:30px;line-height:1.7}
.a-act{display:flex;align-items:center;gap:24px;flex-wrap:wrap}
.a-tel{font-weight:700;color:var(--p);border-bottom:2px solid var(--a);padding-bottom:2px}
.a-panel{position:relative}
.a-frame{position:relative;border-radius:8px;aspect-ratio:.82;background:linear-gradient(150deg,var(--p),var(--pd));overflow:hidden;box-shadow:0 40px 90px rgba(2,6,23,.2)}
.a-frame::after{content:'';position:absolute;top:-20%;left:-20%;width:70%;height:80%;background:radial-gradient(circle,color-mix(in srgb,var(--a) 40%,transparent),transparent 62%);filter:blur(26px)}
.a-wm{position:absolute;inset:0;display:grid;place-items:center;font-size:150px;filter:drop-shadow(0 20px 40px rgba(0,0,0,.4))}
.a-qc{position:absolute;left:-34px;bottom:38px;background:#fff;border:1px solid var(--bd);border-radius:12px;padding:18px 20px;max-width:260px;box-shadow:0 26px 60px rgba(2,6,23,.16)}
.a-qc .st{color:var(--a);letter-spacing:2px;font-size:.85rem;margin-bottom:8px}
.a-qc p{font-size:.9rem;font-style:italic;color:var(--tx);margin-bottom:8px}
.a-qc small{color:var(--g);font-size:.74rem;letter-spacing:.1em;text-transform:uppercase}
.a-rows{display:flex;flex-direction:column;margin-top:20px}
.a-row{display:grid;grid-template-columns:auto 1fr auto;gap:28px;align-items:center;padding:30px 0;border-top:1px solid var(--bd)}
.a-row:last-child{border-bottom:1px solid var(--bd)}
.a-num{font-size:1.6rem;font-weight:700;color:color-mix(in srgb,var(--a) 70%,var(--g))}
.a-rc h3{font-size:1.4rem;font-weight:700;color:var(--p);margin-bottom:4px}
.a-rc p{color:var(--g);font-size:.98rem;max-width:44em}
.a-price{font-weight:700;color:var(--p);white-space:nowrap;background:#fff;border:1px solid var(--bd);padding:7px 15px;border-radius:999px;font-size:.82rem}
.a-about{background:var(--p);color:#fff;text-align:center}
.a-about h2{color:#fff;font-size:clamp(1.9rem,1.2rem + 3vw,3rem);max-width:16em;margin:0 auto 10px}
.a-about .eyebrow{color:var(--a2);justify-content:center}
.a-stats{display:flex;justify-content:center;gap:56px;flex-wrap:wrap;margin-top:40px}
.a-st .num{font-size:2.4rem;font-weight:700;color:var(--a2);font-family:'Palatino Linotype',Georgia,serif}
.a-st .lab{font-size:.82rem;color:rgba(255,255,255,.7);letter-spacing:.06em;margin-top:4px}
.a-rev{text-align:center}
.qrot{position:relative;max-width:760px;margin:10px auto 0;min-height:220px}
.q{position:absolute;inset:0;opacity:0;transition:opacity .8s ease;display:flex;flex-direction:column;justify-content:center;align-items:center}
.q.on{opacity:1;position:relative}
.q p{font-size:clamp(1.3rem,1rem + 1.6vw,2rem);font-style:italic;color:var(--p);line-height:1.4;font-family:'Palatino Linotype',Georgia,serif;margin-bottom:18px}
.q .st{color:var(--a);letter-spacing:3px;margin-bottom:16px}
.q small{color:var(--g);letter-spacing:.1em;text-transform:uppercase;font-size:.78rem}
.a-band{background:var(--p);color:#fff;text-align:center}
.a-band h2{color:#fff}.a-band .eyebrow{color:var(--a2);justify-content:center}
.a-band p{color:rgba(255,255,255,.82);max-width:34em;margin:0 auto 28px}
.a-band .bw{background:var(--a);color:#11151c}
.contact .cwrap{display:grid;grid-template-columns:1fr 1.05fr;gap:56px}
.cinfo{display:flex;flex-direction:column;gap:12px;margin-top:8px}
.crow{display:flex;gap:14px;align-items:center;padding:12px 2px;border-bottom:1px solid var(--bd)}
.ci{font-size:20px}
.cl{font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:var(--g);font-weight:700}
.cv{font-size:1.02rem;font-weight:700;color:var(--p)}
.t-atelier form{display:flex;flex-direction:column;gap:18px;background:transparent;border:none;padding:0}
.t-atelier input,.t-atelier textarea{padding:12px 2px;border:none;border-bottom:1.5px solid var(--bd);border-radius:0;background:transparent;font-size:1rem;font-family:inherit}
.t-atelier input:focus,.t-atelier textarea:focus{outline:none;border-bottom-color:var(--a);box-shadow:none}
.t-atelier .fsub{background:var(--p);color:#fff;border-radius:8px;margin-top:8px;padding:15px}
@media(max-width:880px){.a-grid,.contact .cwrap{grid-template-columns:1fr;gap:44px}.a-qc{left:0}.a-row{grid-template-columns:auto 1fr;gap:14px}.a-price{grid-column:2}}
"""

# ================================================================ MOMENTUM
CSS_MOMENTUM = """
.t-momentum{font-family:'Segoe UI',system-ui,sans-serif;background:#0a0d14;color:#fff}
.t-momentum h1,.t-momentum h2,.t-momentum h3,.t-momentum .m-num,.t-momentum .num{font-family:'Arial Narrow','Helvetica Neue',Arial,sans-serif;text-transform:uppercase;letter-spacing:0}
.t-momentum section{background:#0a0d14}
.t-momentum h2{color:#fff}.t-momentum .sub{color:rgba(255,255,255,.6)}
.t-momentum nav.solid{background:rgba(10,13,20,.85);border-bottom:1px solid rgba(255,255,255,.08)}
.m-hero{min-height:100svh;display:flex;flex-direction:column;justify-content:center;padding:120px 6% 0;position:relative;overflow:hidden;background:radial-gradient(70% 60% at 75% 15%,color-mix(in srgb,var(--a) 24%,transparent),transparent 60%),#0a0d14}
.m-hero::before{content:'';position:absolute;inset:0;background-image:repeating-linear-gradient(115deg,transparent 0 38px,rgba(255,255,255,.025) 38px 39px);pointer-events:none}
.m-in{max-width:1180px;margin:0 auto;width:100%;position:relative;padding-bottom:56px}
.m-eye{display:inline-block;font-size:.78rem;letter-spacing:.28em;text-transform:uppercase;color:var(--a);font-weight:800;margin-bottom:22px}
.m-hero h1{font-size:clamp(3rem,1.4rem + 9vw,7rem);font-weight:800;line-height:.92;color:#fff;margin-bottom:22px}
.m-hero .lead{font-size:clamp(1.05rem,1rem + .4vw,1.25rem);color:rgba(255,255,255,.66);max-width:34em;margin-bottom:30px}
.m-hero .btns{display:flex;gap:14px;flex-wrap:wrap}
.m-tel{display:inline-flex;align-items:center;padding:16px 26px;border:1px solid rgba(255,255,255,.2);border-radius:12px;color:#fff;font-weight:700;will-change:transform}
.m-strip{border-top:1px solid rgba(255,255,255,.1);border-bottom:1px solid rgba(255,255,255,.1);padding:18px 0;overflow:hidden;background:rgba(255,255,255,.02)}
.m-strip .mq{display:flex;gap:34px;width:max-content;animation:mq 26s linear infinite}
.m-strip .mq span{color:#fff;font-weight:800;text-transform:uppercase;letter-spacing:.1em;font-size:1rem;white-space:nowrap}
.m-strip .mq i{color:var(--a);font-style:normal}
@keyframes mq{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.m-stats .statbar{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:rgba(255,255,255,.08);border-radius:16px;overflow:hidden}
.m-stats .stat{background:#0d111a;text-align:center;padding:30px 16px}
.m-stats .num{font-size:2.4rem;font-weight:800;color:var(--a)}
.m-stats .lab{font-size:.82rem;color:rgba(255,255,255,.55);margin-top:4px;text-transform:uppercase;letter-spacing:.08em}
.m-list{display:flex;flex-direction:column;margin-top:16px}
.m-row{position:relative;display:grid;grid-template-columns:auto 1fr auto;gap:26px;align-items:center;padding:28px 24px;border-top:1px solid rgba(255,255,255,.1);overflow:hidden;transition:background .3s}
.m-row:last-child{border-bottom:1px solid rgba(255,255,255,.1)}
.m-row::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--a);transform:scaleY(0);transform-origin:bottom;transition:transform .35s var(--ease)}
.m-row:hover{background:rgba(255,255,255,.03)}.m-row:hover::before{transform:scaleY(1)}
.m-num{font-size:1.5rem;font-weight:800;color:rgba(255,255,255,.3)}
.m-rc h3{font-size:1.5rem;font-weight:800;color:#fff;margin-bottom:2px}
.m-rc p{color:rgba(255,255,255,.55);font-size:.96rem}
.m-arrow{font-size:1.4rem;color:var(--a);opacity:0;transform:translateX(-8px);transition:opacity .3s,transform .3s var(--ease)}
.m-row:hover .m-arrow{opacity:1;transform:none}
.m-awrap{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:center}
.m-about h2{font-size:clamp(2rem,1.2rem + 3.4vw,3.4rem);line-height:1}
.m-whys{list-style:none;display:flex;flex-direction:column;gap:16px;margin-top:20px}
.m-whys li{display:flex;gap:12px;color:rgba(255,255,255,.72)}
.m-whys .chk{flex-shrink:0;width:26px;height:26px;border-radius:6px;background:var(--a);color:#0a0d14;display:grid;place-items:center;font-weight:900;font-size:.8rem}
.m-whys h4{color:#fff;font-size:1rem;font-weight:800;margin-bottom:1px;text-transform:none}
.m-big{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.m-bc{border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:26px;background:rgba(255,255,255,.02)}
.m-bc .num{font-size:2.6rem;font-weight:800;color:var(--a);line-height:1}
.m-bc .lab{color:rgba(255,255,255,.55);font-size:.85rem;margin-top:6px;text-transform:uppercase;letter-spacing:.06em}
.m-scroll{display:flex;gap:20px;overflow-x:auto;padding-bottom:14px;scroll-snap-type:x mandatory}
.m-scroll .rev{scroll-snap-align:start;flex:0 0 320px;background:#0d111a;border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:26px}
.m-scroll .stars{color:var(--a);letter-spacing:2px;margin-bottom:12px}
.m-scroll .rev p{color:rgba(255,255,255,.78);font-style:italic;margin-bottom:16px}
.m-scroll .auth{display:flex;align-items:center;gap:12px}
.m-scroll .ava{width:42px;height:42px;border-radius:50%;background:linear-gradient(140deg,var(--a),var(--a2));color:#0a0d14;display:grid;place-items:center;font-weight:800;font-size:.82rem}
.m-scroll .an{color:#fff;font-weight:750;font-size:.9rem}.m-scroll .al{color:rgba(255,255,255,.5);font-size:.76rem}
.t-momentum .m-band{text-align:center;background:var(--a);color:#0a0d14}
.m-band h2{color:#0a0d14;font-size:clamp(2.2rem,1.4rem + 4vw,4rem)}
.m-band .eyebrow{color:#0a0d14;justify-content:center}.m-band .eyebrow::before{background:#0a0d14}
.m-band p{color:rgba(10,13,20,.8);max-width:32em;margin:0 auto 26px;font-weight:600}
.m-band .bw{background:#0a0d14;color:#fff}
.t-momentum .contact{background:#0a0d14}
.t-momentum .cwrap{display:grid;grid-template-columns:1fr 1.05fr;gap:56px}
.t-momentum .cinfo{display:flex;flex-direction:column;gap:12px;margin-top:8px}
.t-momentum .crow{display:flex;gap:14px;align-items:center;background:#0d111a;border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:15px 18px}
.t-momentum .ci{font-size:20px}
.t-momentum .cl{color:rgba(255,255,255,.5);font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;font-weight:700}
.t-momentum .cv{color:#fff;font-weight:800}
.t-momentum form{display:flex;flex-direction:column;gap:14px;background:#0d111a;border:1px solid rgba(255,255,255,.1);border-radius:18px;padding:30px}
.t-momentum input,.t-momentum textarea{background:#0a0d14;border:1px solid rgba(255,255,255,.14);color:#fff;border-radius:10px;padding:13px 16px;font-family:inherit;font-size:.96rem}
.t-momentum input::placeholder,.t-momentum textarea::placeholder{color:rgba(255,255,255,.4)}
.t-momentum input:focus,.t-momentum textarea:focus{outline:none;border-color:var(--a)}
.t-momentum footer{background:#070a10}
.m-bc{min-width:0}
@media(max-width:880px){.m-awrap,.t-momentum .cwrap{grid-template-columns:1fr;gap:40px}.m-row{grid-template-columns:auto 1fr;gap:16px}.m-arrow{display:none}}
@media(max-width:560px){.m-big{grid-template-columns:1fr}}
"""

# ================================================================ BLOOM
CSS_BLOOM = """
.t-bloom{font-family:'Segoe UI',system-ui,sans-serif;background:var(--cr)}
.t-bloom h1,.t-bloom h2,.t-bloom h3{font-family:'Trebuchet MS','Segoe UI',sans-serif;letter-spacing:-.01em}
.t-bloom nav{top:16px;left:50%;transform:translateX(-50%);right:auto;width:min(1080px,92%);height:60px;border-radius:999px;background:rgba(255,255,255,.72);backdrop-filter:blur(16px) saturate(1.4);box-shadow:0 14px 40px rgba(120,80,40,.14);border:1px solid rgba(255,255,255,.6);padding:0 12px 0 24px}
.t-bloom nav.solid{background:rgba(255,255,255,.92)}
.t-bloom .logo{color:var(--p)}.t-bloom .logo span{color:var(--a)}
.t-bloom .nlinks a{color:var(--tx)}
.t-bloom .tgl span{background:var(--p)}
.t-bloom .mm{top:84px;left:50%;transform:translate(-50%,-160%);width:min(1080px,92%);border-radius:22px;background:rgba(255,255,255,.98);border:1px solid var(--bd)}
.t-bloom .mm.open{transform:translate(-50%,0)}
.t-bloom .mm a{color:var(--tx)}
.b-hero{min-height:100svh;display:flex;align-items:center;padding:130px 6% 90px;position:relative;overflow:hidden;background:radial-gradient(60% 70% at 80% 10%,color-mix(in srgb,var(--a) 22%,var(--cr)),var(--cr)),radial-gradient(50% 60% at 5% 90%,color-mix(in srgb,var(--a2) 30%,var(--cr)),transparent)}
.b-grid{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:1.05fr .95fr;gap:50px;align-items:center;width:100%}
.b-copy .badge{background:#fff;border:1px solid var(--bd);color:var(--p);box-shadow:0 8px 22px rgba(120,80,40,.08);opacity:0;animation:up .7s var(--ease) .1s forwards}
.b-copy .badge .dot{background:var(--a)}
.b-hero h1{font-size:clamp(2.4rem,1.3rem + 5vw,4.3rem);font-weight:800;color:var(--p);line-height:1.05;margin-bottom:20px}
.b-hero .lead{font-size:clamp(1.02rem,.96rem + .4vw,1.2rem);color:var(--g);max-width:32em;margin-bottom:28px}
.b-hero .btns{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:24px}
.b-hero .bs{background:#fff;color:var(--p);border:1px solid var(--bd);box-shadow:0 8px 22px rgba(120,80,40,.08)}
.b-hero .bs:hover{transform:translateY(-2px)}
.b-hero .chips{display:flex;gap:10px 18px;flex-wrap:wrap}.b-hero .chip{color:var(--g);font-size:.88rem;font-weight:600}
.b-cluster{position:relative;height:400px}
.b-card{position:absolute;background:#fff;border:1px solid var(--bd);border-radius:22px;padding:18px 20px;box-shadow:0 26px 60px rgba(120,80,40,.16);display:flex;flex-direction:column;gap:6px;width:210px}
.b-card span{font-size:38px}.b-card b{color:var(--p);font-size:1.02rem}.b-card small{color:var(--g);font-size:.8rem;line-height:1.4}
.b-c1{top:8%;left:4%;animation:bob 5.5s ease-in-out infinite}
.b-c2{top:36%;right:0;animation:bob 5.5s ease-in-out infinite 1.1s;z-index:2}
.b-c3{bottom:2%;left:26%;animation:bob 5.5s ease-in-out infinite 2.2s}
.b-statwrap{padding:0 6% 6px;margin-top:-30px}
.b-pills{max-width:1000px;margin:0 auto;display:flex;gap:16px;flex-wrap:wrap;justify-content:center}
.b-pill{background:#fff;border:1px solid var(--bd);border-radius:999px;padding:14px 26px;box-shadow:0 12px 30px rgba(120,80,40,.1);display:flex;align-items:baseline;gap:8px}
.b-pill .num{font-size:1.3rem;font-weight:800;color:var(--a)}.b-pill .lab{color:var(--g);font-size:.86rem}
.b-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}
.b-tile{background:#fff;border:1px solid var(--bd);border-radius:24px;padding:28px;transition:transform .4s var(--ease),box-shadow .35s}
.b-tile:hover{transform:translateY(-8px);box-shadow:0 26px 56px rgba(120,80,40,.16)}
.b-tico{width:64px;height:64px;border-radius:20px;display:grid;place-items:center;font-size:30px;margin-bottom:16px;background:color-mix(in srgb,var(--a) 16%,#fff)}
.b-tile h3{font-size:1.16rem;font-weight:800;color:var(--p);margin-bottom:6px}
.b-tile p{color:var(--g);font-size:.94rem}
.b-tile .price{margin-top:12px;display:inline-block;background:color-mix(in srgb,var(--a) 14%,#fff);color:var(--p);font-weight:800;font-size:.82rem;padding:6px 15px;border-radius:999px}
.b-about{background:#fff}
.b-awrap{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:.9fr 1.1fr;gap:52px;align-items:center}
.b-blob{aspect-ratio:1;border-radius:42% 58% 55% 45%/48% 42% 58% 52%;background:linear-gradient(150deg,color-mix(in srgb,var(--a) 30%,var(--cr)),color-mix(in srgb,var(--a2) 40%,var(--cr)));display:grid;place-items:center;font-size:110px;box-shadow:0 30px 70px rgba(120,80,40,.16);animation:morph 9s ease-in-out infinite}
@keyframes morph{0%,100%{border-radius:42% 58% 55% 45%/48% 42% 58% 52%}50%{border-radius:56% 44% 43% 57%/56% 54% 46% 44%}}
.b-whys{list-style:none;display:flex;flex-direction:column;gap:16px;margin-top:14px}
.b-whys li{display:flex;gap:13px}
.b-whys .chk{flex-shrink:0;width:32px;height:32px;border-radius:12px;background:color-mix(in srgb,var(--a) 18%,#fff);color:var(--p);display:grid;place-items:center;font-weight:900}
.b-whys h4{color:var(--p);font-size:1.02rem;font-weight:800;margin-bottom:1px}.b-whys p{color:var(--g);font-size:.92rem}
.b-revs{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
.b-rev{background:#fff;border:1px solid var(--bd);border-radius:24px;padding:28px;position:relative}
.b-rev::before{content:'“';position:absolute;top:6px;right:22px;font-size:70px;color:color-mix(in srgb,var(--a) 30%,#fff);font-family:Georgia,serif;line-height:1}
.b-rev .stars{color:var(--a);letter-spacing:2px;margin-bottom:12px}
.b-rev p{color:#5b4a3a;font-style:italic;margin-bottom:16px}
.b-rev .auth{display:flex;align-items:center;gap:12px}
.b-rev .ava{width:42px;height:42px;border-radius:50%;background:linear-gradient(140deg,var(--a),var(--a2));color:#fff;display:grid;place-items:center;font-weight:800;font-size:.82rem}
.b-rev .an{font-weight:750;color:var(--p);font-size:.9rem}.b-rev .al{color:var(--g);font-size:.76rem}
.b-band{text-align:center;background:linear-gradient(140deg,color-mix(in srgb,var(--a) 22%,var(--cr)),color-mix(in srgb,var(--a2) 30%,var(--cr)));color:var(--p)}
.b-band h2{color:var(--p)}.b-band .eyebrow{color:var(--p);justify-content:center}.b-band .eyebrow::before{background:var(--p)}
.b-band p{color:var(--tx);max-width:34em;margin:0 auto 26px}
.b-band .bw{background:var(--p);color:#fff}
.contact{background:#fff}
.contact .cwrap{display:grid;grid-template-columns:1fr 1.05fr;gap:56px}
.cinfo{display:flex;flex-direction:column;gap:14px;margin-top:8px}
.crow{display:flex;gap:15px;align-items:center;background:var(--cr);border:1px solid var(--bd);border-radius:18px;padding:15px 18px}
.ci{flex-shrink:0;width:44px;height:44px;border-radius:14px;display:grid;place-items:center;font-size:20px;background:#fff;border:1px solid var(--bd)}
.cl{font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:var(--g);font-weight:700}.cv{font-size:1.02rem;font-weight:800;color:var(--p)}
.t-bloom form{display:flex;flex-direction:column;gap:14px;background:var(--cr);border:1px solid var(--bd);border-radius:26px;padding:32px}
.t-bloom input,.t-bloom textarea{padding:14px 16px;border:1.5px solid var(--bd);border-radius:14px;background:#fff;font-size:.96rem;font-family:inherit}
.t-bloom input:focus,.t-bloom textarea:focus{outline:none;border-color:var(--a);box-shadow:0 0 0 4px color-mix(in srgb,var(--a) 16%,transparent)}
.t-bloom .fsub{border-radius:14px}
@media(max-width:880px){.b-grid,.b-awrap,.contact .cwrap{grid-template-columns:1fr;gap:40px}.b-cluster{height:330px}.b-blob{max-width:340px;margin:0 auto}}
@media(max-width:600px){.t-bloom nav{width:94%;padding:0 10px 0 18px}.t-bloom .ncta{display:none}}
"""


# ---------------------------------------------------------------- fragments
def _chips(c):
    labels = ["Trusted in " + esc(c["town"]), "Friendly local team", "Fair, honest prices"]
    return "".join('<span class="chip">✓ ' + l + "</span>" for l in labels)


def _mq(c):
    items = "".join("<span>" + esc(s["title"]) + '</span><i>✦</i>' for s in c["services"])
    return items + items


def _whys(c, cls="whys", chk="chk"):
    return "".join('<li class="why"><span class="' + chk + '">✓</span><div><h4>' + esc(h) +
                   "</h4><p>" + esc(p) + "</p></div></li>" for h, p in c["why"])


def _cards(c):
    return "".join('<div class="card" data-tilt><div class="ico">' + s["icon"] + "</div><h3>" +
                   esc(s["title"]) + "</h3><p>" + esc(s["desc"]) + "</p>" +
                   ('<div class="price">' + esc(s["price"]) + "</div>" if s["price"] else "") +
                   "</div>" for s in c["services"])


def _revcards(c):
    return "".join('<div class="rev"><div class="stars">★★★★★</div><p>"' + esc(r["txt"]) +
                   '"</p><div class="auth"><div class="ava">' + esc(r["initials"]) +
                   '</div><div><div class="an">' + esc(r["nm"]) + '</div><div class="al">' +
                   esc(r["place"]) + "</div></div></div></div>" for r in c["reviews"])


def _cta_label(c):
    return ("📞 " + esc(c["phone"])) if c["phone"] else esc(c["cta"])


def _nav(c):
    return ('<div class="prog" id="prog" aria-hidden="true"></div>'
            '<nav id="nav"><div class="logo">' + c["logo"] + "</div>"
            '<ul class="nlinks"><li><a href="#services">' + esc(c["stag"]) + "</a></li>"
            '<li><a href="#about">About</a></li><li><a href="#reviews">Reviews</a></li>'
            '<li><a href="#contact">Contact</a></li></ul>'
            '<div class="nav-right"><a href="' + c["href"] + '" class="ncta">' + _cta_label(c) + "</a>"
            '<button class="tgl" id="tgl" aria-label="Open menu" aria-expanded="false">'
            "<span></span><span></span><span></span></button></div></nav>"
            '<div class="mm" id="mm"><a href="#services">' + esc(c["stag"]) + "</a>"
            '<a href="#about">About</a><a href="#reviews">Reviews</a><a href="#contact">Contact</a>'
            '<a href="' + c["href"] + '" class="mcta">' + esc(c["cta"]) + "</a></div>")


def _contact(c):
    ph = esc(c["phone"]) if c["phone"] else "Add your number"
    return ('<section id="contact" class="contact"><div class="wrap cwrap">'
            '<div class="reveal"><div class="eyebrow">Get in touch</div><h2>' + esc(c["cta"]) + "</h2>"
            '<p class="sub">We\'d love to hear from you. Call or drop a message and we\'ll get straight back.</p>'
            '<div class="cinfo">'
            '<div class="crow"><span class="ci">📞</span><div><div class="cl">Phone</div><div class="cv">' + ph + "</div></div></div>"
            '<div class="crow"><span class="ci">📍</span><div><div class="cl">Area</div><div class="cv">' + esc(c["town"]) + " &amp; nearby</div></div></div>"
            '<div class="crow"><span class="ci">🕒</span><div><div class="cl">Hours</div><div class="cv">Open 6 days a week</div></div></div>'
            "</div></div>"
            '<form class="reveal" onsubmit="return false"><input type="text" placeholder="Your name" aria-label="Your name">'
            '<input type="tel" placeholder="Phone number" aria-label="Phone number">'
            '<input type="email" placeholder="Email address" aria-label="Email address">'
            '<textarea rows="4" placeholder="How can we help?" aria-label="Message"></textarea>'
            '<button class="fsub bp" type="submit">Send message →</button></form></div></section>')


def _footer(c):
    ph = (" · " + esc(c["phone"])) if c["phone"] else ""
    return ("<footer><div class=\"fn\">" + c["logo"] + "</div>"
            "<div>" + esc(c["badge"]) + " · " + esc(c["town"]) + ph + "</div>"
            '<p class="concept">This is a free design concept created by <b>HW Web Design</b> to show '
            + esc(c["name"]) + " what a modern website could look like. Sample text, prices and reviews "
            "are for illustration only. Like it? Let's make it real — hwwebdesign.co.uk</p></footer>"
            '<a class="flag" href="' + BASE_URL + '" target="_blank" rel="noopener">✦ Concept by <b>HW Web Design</b></a>')


def _page(c, bodyclass, css, body):
    a = c["a"]
    meta = ('<meta name="description" content="' + esc(c["name"]) + " — " + esc(c["badge"]) +
            " in " + esc(c["town"]) + '. ' + esc(c["sub"]) + '">')
    return ('<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            + meta + '<meta name="robots" content="noindex">'
            "<title>" + esc(c["name"]) + " | " + esc(c["badge"]) + " in " + esc(c["town"]) + "</title>"
            "<style>" + _vars(a) + CORE_CSS + BASE_BITS + css + "</style></head>"
            '<body class="' + bodyclass + '"><div class="grain" aria-hidden="true"></div>'
            + _nav(c) + body + _footer(c) + CORE_JS + "</body></html>")


# ---------------------------------------------------------------- builders
def build_stage(c):
    q = c["reviews"][0]
    body = (
        '<header class="hero s-hero" id="top"><span class="orb o1"></span><span class="orb o2"></span>'
        '<span class="grid-ov"></span><div class="s-hero-in">'
        '<span class="badge"><span class="dot"></span>' + esc(c["badge"]) + " · " + esc(c["town"]) + "</span>"
        "<h1>" + c["head"] + '</h1><p class="lead">' + esc(c["sub"]) + "</p>"
        '<div class="btns"><a href="' + c["href"] + '" class="bp">' + esc(c["cta"]) +
        ' →</a><a href="#services" class="bs">See services</a></div>'
        '<div class="chips">' + _chips(c) + '</div></div><div class="s-fade"></div></header>'
        '<div class="mqw" aria-hidden="true"><div class="mq">' + _mq(c) + "</div></div>"
        '<div class="statwrap"><div class="statbar stagger">' + c["stats"] + "</div></div>"
        '<section id="services"><div class="wrap"><div class="reveal"><div class="eyebrow">' +
        esc(c["stag"]) + "</div><h2>" + esc(c["shead"]) + '</h2><p class="sub">' + esc(c["ssub"]) +
        '</p></div><div class="grid stagger">' + _cards(c) + "</div></div></section>"
        '<section id="about" class="cream"><div class="wrap awrap"><div class="reveal">'
        '<div class="eyebrow">Why ' + esc(c["name"]) + "</div><h2>Why Locals Choose Us</h2>"
        '<p class="sub">We\'re proud to serve ' + esc(c["town"]) + " and the area — and we work hard to keep it that way.</p>"
        '<ul class="whys">' + _whys(c) + "</ul></div>"
        '<div class="svisual" data-emoji="' + c["visual"] + '"><div class="svq"><div class="st">★★★★★</div><p>"' +
        esc(q["txt"]) + '"</p><small>' + esc(q["nm"]) + " · " + esc(c["town"]) + "</small></div></div></div></section>"
        '<section id="reviews"><div class="wrap"><div class="reveal"><div class="eyebrow">Reviews</div>'
        "<h2>What People Say</h2><p class=\"sub\">Real words from happy customers across " + esc(c["town"]) +
        ' and beyond.</p></div><div class="revs stagger">' + _revcards(c) + "</div></div></section>"
        '<section class="band"><div class="wrap reveal"><div class="eyebrow">Ready when you are</div>'
        "<h2>" + esc(c["cta"]) + " Today</h2><p>Friendly, local and easy to reach — " + esc(c["name"]) +
        " is here for " + esc(c["town"]) + '.</p><a href="' + c["href"] + '" class="bw">' + _cta_label(c) +
        "</a></div></section>" + _contact(c))
    return _page(c, "t-stage", CSS_STAGE, body)


def build_atelier(c):
    q = c["reviews"][0]
    rows = ""
    for i, s in enumerate(c["services"], 1):
        price = '<span class="a-price">' + esc(s["price"]) + "</span>" if s["price"] else '<span class="a-price">Enquire</span>'
        rows += ('<div class="a-row reveal"><span class="a-num">%02d</span><div class="a-rc"><h3>' % i +
                 esc(s["title"]) + "</h3><p>" + esc(s["desc"]) + "</p></div>" + price + "</div>")
    qs = ""
    for i, r in enumerate(c["reviews"]):
        qs += ('<div class="q' + (" on" if i == 0 else "") + '"><div class="st">★★★★★</div><p>"' +
               esc(r["txt"]) + '"</p><small>' + esc(r["nm"]) + " · " + esc(r["place"]) + "</small></div>")
    astats = '<div class="a-stats count-wrap">'
    for num, lab in c["a"]["stats"]:
        cc = _count_num(num)
        inner = ('<span data-count="' + cc[0] + '">' + cc[0] + "</span>" + cc[1]) if cc else esc(num)
        astats += '<div class="a-st"><div class="num">' + inner + '</div><div class="lab">' + esc(lab) + "</div></div>"
    astats += "</div>"
    tel_html = ('<a href="' + c["href"] + '" class="a-tel">or call ' + esc(c["phone"]) + "</a>") if c["phone"] else ""
    body = (
        '<header class="hero a-hero" id="top"><div class="a-grid"><div class="a-copy clip">'
        '<span class="a-eye">' + esc(c["badge"]) + " — " + esc(c["town"]) + "</span><h1>" + c["head"] +
        '</h1><p class="lead">' + esc(c["sub"]) + '</p><div class="a-act"><a href="' + c["href"] +
        '" class="bp">' + esc(c["cta"]) + "</a>" + tel_html + "</div></div>"
        '<div class="a-panel reveal"><div class="a-frame"><span class="a-wm">' + c["visual"] + "</span></div>"
        '<div class="a-qc"><div class="st">★★★★★</div><p>"' + esc(q["txt"]) + '"</p><small>' + esc(q["nm"]) +
        "</small></div></div></div></header>"
        '<section id="services" class="a-serv"><div class="wrap"><div class="reveal"><div class="eyebrow">' +
        esc(c["stag"]) + "</div><h2>" + esc(c["shead"]) + '</h2><p class="sub">' + esc(c["ssub"]) +
        '</p></div><div class="a-rows">' + rows + "</div></div></section>"
        '<section id="about" class="a-about"><div class="wrap reveal"><div class="eyebrow">Why ' +
        esc(c["name"]) + "</div><h2>A local name " + esc(c["town"]) + " can rely on</h2>" + astats + "</div></section>"
        '<section id="reviews" class="a-rev"><div class="wrap reveal"><div class="eyebrow" style="justify-content:center">Reviews</div>'
        '<div class="qrot">' + qs + "</div></div></section>"
        '<section class="band a-band"><div class="wrap reveal"><div class="eyebrow">Ready when you are</div><h2>' +
        esc(c["cta"]) + "</h2><p>Friendly, local and easy to reach — " + esc(c["name"]) + " is here for " +
        esc(c["town"]) + '.</p><a href="' + c["href"] + '" class="bw">' + _cta_label(c) + "</a></div></section>"
        + _contact(c))
    return _page(c, "t-atelier", CSS_ATELIER, body)


def build_momentum(c):
    strip = "".join("<span>" + esc(s["title"]) + "</span><i>/</i>" for s in c["services"])
    strip += strip
    rows = ""
    for i, s in enumerate(c["services"], 1):
        extra = (" · " + esc(s["price"])) if s["price"] else ""
        rows += ('<div class="m-row reveal"><span class="m-num">%02d</span><div class="m-rc"><h3>' % i +
                 esc(s["title"]) + "</h3><p>" + esc(s["desc"]) + extra + '</p></div><span class="m-arrow">→</span></div>')
    big = '<div class="m-big count-wrap">'
    for num, lab in c["a"]["stats"]:
        cc = _count_num(num)
        inner = ('<span data-count="' + cc[0] + '">' + cc[0] + "</span>" + cc[1]) if cc else esc(num)
        big += '<div class="m-bc"><div class="num">' + inner + '</div><div class="lab">' + esc(lab) + "</div></div>"
    big += "</div>"
    whys = "".join('<li><span class="chk">✓</span><div><h4>' + esc(h) + "</h4><p>" + esc(p) + "</p></div></li>"
                   for h, p in c["why"])
    tel_html = ('<a href="' + c["href"] + '" class="m-tel" data-mag>📞 ' + esc(c["phone"]) + "</a>") if c["phone"] else ""
    body = (
        '<header class="hero m-hero" id="top"><div class="m-in"><span class="m-eye">' + esc(c["badge"]) +
        " / " + esc(c["town"]) + "</span><h1>" + c["head"] + '</h1><p class="lead">' + esc(c["sub"]) +
        '</p><div class="btns"><a href="' + c["href"] + '" class="bp">' + esc(c["cta"]) + " →</a>" + tel_html +
        '</div></div><div class="m-strip" aria-hidden="true"><div class="mq">' + strip + "</div></div></header>"
        '<section class="m-stats"><div class="wrap statbar stagger count-wrap">' + c["stats"] + "</div></section>"
        '<section id="services" class="m-serv"><div class="wrap"><div class="reveal"><div class="eyebrow">' +
        esc(c["stag"]) + "</div><h2>" + esc(c["shead"]) + '</h2><p class="sub">' + esc(c["ssub"]) +
        '</p></div><div class="m-list">' + rows + "</div></div></section>"
        '<section id="about" class="m-about"><div class="m-awrap"><div class="reveal"><div class="eyebrow">Why ' +
        esc(c["name"]) + '</div><h2>Built on doing it right</h2><ul class="m-whys">' + whys + "</ul></div>"
        '<div class="reveal">' + big + "</div></div></section>"
        '<section id="reviews" class="m-rev"><div class="wrap"><div class="reveal"><div class="eyebrow">Reviews</div>'
        '<h2>The verdict</h2></div><div class="m-scroll">' + _revcards(c) + "</div></div></section>"
        '<section class="band m-band"><div class="wrap reveal"><div class="eyebrow">Ready when you are</div><h2>' +
        esc(c["cta"]) + "</h2><p>" + esc(c["name"]) + " — here for " + esc(c["town"]) +
        ' and ready when you are.</p><a href="' + c["href"] + '" class="bw">' + _cta_label(c) + "</a></div></section>"
        + _contact(c))
    return _page(c, "t-momentum", CSS_MOMENTUM, body)


def build_bloom(c):
    s = c["services"]
    def bcard(cls, sv):
        return ('<div class="b-card ' + cls + '"><span>' + sv["icon"] + "</span><b>" + esc(sv["title"]) +
                "</b><small>" + esc(sv["desc"]) + "</small></div>")
    cluster = bcard("b-c1", s[0]) + bcard("b-c2", s[1]) + bcard("b-c3", s[2] if len(s) > 2 else s[0])
    tiles = "".join('<div class="b-tile"><div class="b-tico">' + sv["icon"] + "</div><h3>" + esc(sv["title"]) +
                    "</h3><p>" + esc(sv["desc"]) + "</p>" +
                    ('<div class="price">' + esc(sv["price"]) + "</div>" if sv["price"] else "") + "</div>"
                    for sv in c["services"])
    pills = ""
    for num, lab in c["a"]["stats"]:
        cc = _count_num(num)
        inner = ('<span data-count="' + cc[0] + '">' + cc[0] + "</span>" + cc[1]) if cc else esc(num)
        pills += '<div class="b-pill"><span class="num">' + inner + '</span><span class="lab">' + esc(lab) + "</span></div>"
    whys = "".join('<li><span class="chk">✓</span><div><h4>' + esc(h) + "</h4><p>" + esc(p) + "</p></div></li>"
                   for h, p in c["why"])
    revs = "".join('<div class="b-rev"><div class="stars">★★★★★</div><p>"' + esc(r["txt"]) +
                   '"</p><div class="auth"><div class="ava">' + esc(r["initials"]) + '</div><div><div class="an">' +
                   esc(r["nm"]) + '</div><div class="al">' + esc(r["place"]) + "</div></div></div></div>"
                   for r in c["reviews"])
    body = (
        '<header class="hero b-hero" id="top"><div class="b-grid"><div class="b-copy reveal">'
        '<span class="badge"><span class="dot"></span>' + esc(c["badge"]) + " · " + esc(c["town"]) + "</span><h1>" +
        c["head"] + '</h1><p class="lead">' + esc(c["sub"]) + '</p><div class="btns"><a href="' + c["href"] +
        '" class="bp">' + esc(c["cta"]) + ' →</a><a href="#services" class="bs">See more</a></div>'
        '<div class="chips">' + _chips(c) + '</div></div><div class="b-cluster" aria-hidden="true">' + cluster +
        "</div></div></header>"
        '<div class="b-statwrap"><div class="b-pills stagger">' + pills + "</div></div>"
        '<section id="services"><div class="wrap"><div class="reveal"><div class="eyebrow">' + esc(c["stag"]) +
        "</div><h2>" + esc(c["shead"]) + '</h2><p class="sub">' + esc(c["ssub"]) + '</p></div><div class="b-tiles stagger">' +
        tiles + "</div></div></section>"
        '<section id="about" class="b-about"><div class="b-awrap"><div class="b-blob reveal">' + c["visual"] +
        '</div><div class="reveal"><div class="eyebrow">Why ' + esc(c["name"]) +
        '</div><h2>Made with care, loved by locals</h2><ul class="b-whys">' + whys + "</ul></div></div></section>"
        '<section id="reviews"><div class="wrap"><div class="reveal"><div class="eyebrow">Reviews</div><h2>Kind words</h2></div>'
        '<div class="b-revs stagger">' + revs + "</div></div></section>"
        '<section class="band b-band"><div class="wrap reveal"><div class="eyebrow">Come say hello</div><h2>' +
        esc(c["cta"]) + "</h2><p>" + esc(c["name"]) + " is here for " + esc(c["town"]) +
        '. We\'d love to see you.</p><a href="' + c["href"] + '" class="bw">' + _cta_label(c) + "</a></div></section>"
        + _contact(c))
    return _page(c, "t-bloom", CSS_BLOOM, body)


BUILDERS = {"stage": build_stage, "atelier": build_atelier,
            "momentum": build_momentum, "bloom": build_bloom}


def render(biz):
    name, niche, town = biz["name"], biz["niche"], biz["town"]
    niche = NICHE_OVERRIDE.get(lead_slug(name, town), niche)
    n = NICHE.get(niche, NICHE["restaurant"])
    a = ARCH[n["arch"]]
    phone = (biz.get("phone") or "").strip()
    href = "tel:" + tel(phone) if phone else "#contact"
    fmt = lambda s: s.format(town=town)
    services = [dict(icon=s["icon"], title=fmt(s["title"]), desc=fmt(s["desc"]), price=s["price"])
                for s in n["services"]]
    c = dict(name=name, town=town, phone=phone, href=href, logo=_logo(name),
             badge=fmt(n["badge"]), sub=fmt(n["sub"]), head=_headline(n["head"], town),
             cta=n["cta"], stag=n["stag"], shead=fmt(n["shead"]), ssub=fmt(n["ssub"]),
             emoji=n["emoji"], visual=n["visual"], stats=_stats_html(a),
             services=services, reviews=_reviews_list(n, town), why=a["why"], a=a, n=n)
    return BUILDERS[pick_arch(name, town, niche)](c)


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
    def pal(b):
        return ARCH[NICHE.get(b["niche"], NICHE["restaurant"])["arch"]]
    cards = "".join(
        '<a class="g" href="./' + lead_slug(b["name"], b["town"]) + '/" target="_blank">'
        '<div class="gt" style="background:linear-gradient(140deg,' + pal(b)["primary"] + "," + pal(b)["dark"] +
        ')"><span>' + NICHE.get(b["niche"], {}).get("emoji", "🌐") + "</span>"
        '<em>' + pick_arch(b["name"], b["town"], b["niche"]) + "</em></div>"
        '<div class="gb"><div class="gn">' + esc(b["name"]) + '</div>'
        '<div class="gm">' + esc(b["niche"]) + " · " + esc(b["town"]) + "</div></div></a>"
        for b in items)
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            '<meta name="robots" content="noindex"><title>HW Web Design — Live Mockups</title><style>'
            "*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',system-ui,sans-serif;background:#0b1220;color:#eef2fc}"
            "header{background:radial-gradient(60% 90% at 80% -20%,rgba(124,58,237,.3),transparent 60%),radial-gradient(50% 80% at 10% 0%,rgba(37,99,235,.35),transparent 55%),#0b1220;padding:72px 6% 56px}"
            "header h1{font-size:clamp(28px,4vw,44px);font-weight:900;letter-spacing:-1px}"
            "header h1 span{background:linear-gradient(92deg,#60a5fa,#a78bfa);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}"
            "header p{color:rgba(238,242,252,.7);margin-top:10px;font-size:17px;max-width:640px}"
            ".wrap{max-width:1140px;margin:0 auto;padding:46px 6% 90px}"
            ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:18px}"
            ".g{background:#101a35;border:1px solid rgba(125,160,255,.14);border-radius:16px;overflow:hidden;color:inherit;transition:transform .3s cubic-bezier(.16,1,.3,1),box-shadow .3s,border-color .3s}"
            ".g:hover{transform:translateY(-6px);box-shadow:0 22px 50px rgba(2,6,20,.55);border-color:rgba(125,160,255,.35)}"
            ".gt{position:relative;height:120px;display:flex;align-items:center;justify-content:center}"
            ".gt span{font-size:46px;filter:drop-shadow(0 6px 16px rgba(0,0,0,.4))}"
            ".gt em{position:absolute;top:10px;right:12px;font-style:normal;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.6);background:rgba(0,0,0,.3);padding:3px 8px;border-radius:999px}"
            ".gb{padding:16px 18px}.gn{font-weight:800;font-size:15.5px}.gm{color:rgba(238,242,252,.55);font-size:12.5px;text-transform:capitalize;margin-top:3px}"
            "</style></head><body><header><h1>Live Website <span>Mockups</span></h1>"
            "<p>Free design concepts built by HW Web Design for local businesses — now in four distinct styles. Click any card to view the full mockup.</p></header>"
            '<div class="wrap"><div class="grid">' + cards + "</div></div></body></html>")


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "leads/leads_high_wycombe_area.csv"
    items = select(csv_path)
    os.makedirs("mockups", exist_ok=True)
    for b in items:
        slug = lead_slug(b["name"], b["town"])
        if slug in BESPOKE_SLUGS:
            continue
        d = os.path.join("mockups", slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w") as f:
            f.write(render(b))
    with open("mockups/index.html", "w") as f:
        f.write(gallery(items))
    counts = {}
    for b in items:
        if lead_slug(b["name"], b["town"]) in BESPOKE_SLUGS:
            continue
        k = pick_arch(b["name"], b["town"], b["niche"])
        counts[k] = counts.get(k, 0) + 1
    print("Generated %d mockups -> mockups/  (gallery: mockups/index.html)" % len(items))
    print("Architecture spread: " + ", ".join("%s=%d" % (k, v) for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
