# Tenly — UK Launch Playbook (deep dive)

A concrete, run-it-this-week plan to get the first 3 paying landlords for Tenly,
localised for the UK and your home turf (Buckinghamshire / home counties).

> **One number to hit:** 3 paying landlords in 14 days. Everything below serves that.

---

## 1. The beachhead: local UK "accidental" landlords (1–5 units)

Don't start with everyone. Start with the tightest segment that feels this pain
hardest and is easiest for *you* to reach:

**Independent UK landlords with 1–5 units who self-manage (no letting agent).**

Why this exact group:
- **They feel it most.** They have no staff and no agent, so *they* are the 2am
  phone. Big portfolios already pay agents; this group is stuck.
- **They're priced out of agents.** Full management agents charge ~10–15% of rent
  (often £100–250+/unit/mo). Tenly at £9/unit is a no-brainer by comparison.
- **You can reach them locally.** You're in Buckinghamshire — there are landlord
  meetups, local Facebook groups, and REIA-style networks within driving distance.
  In-person trust converts far better than cold internet.

**Expansion later:** landlords who just had a bad agent experience, then small
portfolio (6–15 unit) self-managers.

---

## 2. Where to find them (UK-specific)

| Channel | Notes |
|---|---|
| **r/uklandlords**, r/HousingUK, r/LandlordUK | Active, opinionated; lead with free help, not a pitch (most ban ads) |
| **Property118 forum** | Serious UK landlord community |
| **OpenRent landlord community / blog comments** | Self-managing landlords by definition |
| **Facebook: "Landlords of [Bucks/your town]"**, "UK Landlords", NRLA member groups | Local groups convert; read group rules first |
| **NRLA** (National Residential Landlords Association) local branch meetups | In-person, high trust — your best channel |
| **Local REIA / property meetups** (search Eventbrite + Meetup for "[your town] property investors") | Face-to-face = fastest yes |

**Your unfair advantage:** start *local and in person*. Two coffees with local
landlords beats 200 cold DMs.

---

## 3. Recruiting posts (tailored per channel)

### A) r/uklandlords (rules-aware — frame as research + free help)
> **I'll be your after-hours tenant line for 2 weeks, free — looking for a few self-managing landlords**
>
> I'm a [Bucks-based] landlord building a tool to handle the bit we all hate:
> tenant messages and maintenance at all hours. Before I automate anything I want
> to run it manually for a few of you, free.
>
> For two weeks I'll personally handle your tenant texts — triage the routine
> stuff, line up a contractor when needed (you approve anything that costs money),
> and only ring you for genuine emergencies. You get quieter evenings; I learn
> what actually matters.
>
> Self-managing, 1–5 units, tired of the buzzing phone? Comment or DM. Not selling
> anything — first 5 only.

### B) Local Facebook landlord group (warmer, neighbourly)
> Fellow [town] landlords — quick one. I'm trialling a service that handles tenant
> messages and maintenance triage so you're not the 24/7 phone line. I'll run it
> free for two weeks for a couple of local landlords. You approve anything that
> costs money; I handle the rest. Anyone fed up of weekend "the boiler's playing
> up" texts? Drop a comment 👇

### C) NRLA meetup / in-person one-liner
> "I'm building something that handles tenant messages and maintenance triage for
> self-managing landlords — basically an after-hours tenant line. I'm running it
> free for a couple of people for two weeks to learn. Could I set it up for you?"

---

## 4. The Wizard-of-Oz setup (be the tenant line — UK tools)

You're going to *be* Tenly by hand for the first landlords. Setup, ~30 min:

1. **Get a dedicated UK number** tenants can text:
   - Easiest: a cheap **PAYG SIM** (Giffgaff/Smarty/Lebara) in a spare phone, or
   - **Twilio UK number** (programmable; lets you forward/log), or
   - A second line app (e.g. a UK eSIM / second-number app).
2. **Onboard each landlord** (15-min call): get their properties, tenant names,
   boiler/appliance details, a couple of trusted local contractors (or you source
   them), and their rules ("call me if it's over £X / a genuine emergency").
3. **Give tenants the number** — landlord tells tenants "text this for anything
   to do with the flat." No app, nothing to install.
4. **You run the playbook** (below) whenever a tenant texts. Log everything in a
   simple spreadsheet per landlord: time, tenant, issue, action, outcome.

---

## 5. Tenant-reply templates (British English, in the landlord's voice)

**First contact / acknowledgement**
> Hi [Tenant], thanks for letting me know — I'll get this sorted. Quick question
> so I can help fast: [clarifying q]. I'll update you shortly.

**Routine troubleshoot (e.g. no hot water)**
> Before I send anyone out — could you check the boiler pressure gauge? If it's
> below 1 bar, there's a small lever/tap underneath to top it up; here's how:
> [link/photo]. If that doesn't do it, I'll arrange an engineer today.

**Booking a contractor (after landlord approval)**
> All sorted — I've arranged [trade] to come [day, time window]. They'll text
> before arriving. Anything else in the meantime, just message me here.

**Genuine emergency (leak/gas/no heat in winter)**
> Thanks for flagging — treating this as urgent. [Immediate safety step, e.g.
> "please turn off the stopcock under the sink"]. I'm getting someone to you now
> and will keep you posted every step.

> (In parallel: call + text the landlord immediately.)

---

## 6. Week-by-week

**Week 1 — recruit & set up**
- Post A + B, DM 10 landlords, mention it at one local meetup.
- Onboard the first 3–5 who say yes. Numbers live, tenants notified.

**Week 2 — run it & earn the proof**
- Handle every tenant message fast and well. Capture the wins (screenshots of
  "wow, that was quick — thank you").
- Mid-week, send the paid ask to anyone who's felt the relief.

**Day 14 — score & decide** (see scorecard in GO-TO-MARKET.md).

---

## 7. Pricing & the paid ask (GBP)

- **£9 / unit / month.** First unit free for 14 days.
- Anchor against the alternative: *a full management agent is ~£100–250/unit/mo.
  Tenly handles the most painful part for £9.*

**Paid ask:**
> Glad the quiet evenings landed! I'm making Tenly permanent — £9 per unit a
> month, running 24/7 so you're never the after-hours line again. Want me to keep
> it going for your places? [Stripe link]

---

## 8. The two things you must do to collect money

1. **Stripe Payment Link** — create a **£9/unit/month** subscription link (same
   steps as before, currency GBP) and paste it in; I'll wire it into the page.
2. **GitHub Pages** — flip it on so the page is live at `…github.io/jarvis-app/tenly/`.

---

## 9. Riskiest assumptions (what we're really testing)

1. **Trust:** will a landlord let an outsider talk to their tenants in their name?
   → Tested the moment they hand over the number.
2. **Willingness to pay:** £9/unit isn't much — will they pay it vs. just coping?
   → Tested by the Stripe card.
3. **Quality:** can routine messages be handled without bothering the landlord?
   → Tested by your hit rate over the two weeks.

If trust + pay survive, build the thin automation: one number, one triage flow,
landlord-approval step. Nothing more until you have paying landlords asking for it.
